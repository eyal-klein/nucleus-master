"""
NUCLEUS V1.2 - Google Cloud Pub/Sub Client Wrapper

Provides async messaging infrastructure using Google Cloud Pub/Sub.
Based on NUCLEUS-ATLAS implementation.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable
from google.cloud import pubsub_v1
from google.api_core import retry
import logging

logger = logging.getLogger(__name__)


class PubSubClient:
    """Async wrapper for Google Cloud Pub/Sub"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self._subscriptions: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize the Pub/Sub client"""
        logger.info(f"Initializing Pub/Sub client for project: {self.project_id}")
        
    async def publish(
        self,
        topic_name: str,
        message_data: Dict[str, Any],
        attributes: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Publish a message to a topic.
        
        Args:
            topic_name: Name of the topic (without project prefix)
            message_data: Message payload as dict
            attributes: Optional message attributes
            
        Returns:
            Message ID
        """
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        
        # Convert message data to JSON bytes
        message_bytes = json.dumps(message_data).encode("utf-8")
        
        # Publish message
        future = self.publisher.publish(
            topic_path,
            data=message_bytes,
            **(attributes or {})
        )
        
        message_id = await asyncio.get_event_loop().run_in_executor(
            None, future.result
        )
        
        logger.info(f"Published message {message_id} to {topic_name}")
        return message_id
    
    async def subscribe(
        self,
        subscription_name: str,
        callback: Callable[[Dict[str, Any]], None],
        max_messages: int = 10
    ):
        """
        Subscribe to a subscription and process messages.
        
        Args:
            subscription_name: Name of the subscription (without project prefix)
            callback: Async function to process each message
            max_messages: Max messages to pull at once
        """
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_name
        )
        
        def message_callback(message: pubsub_v1.subscriber.message.Message):
            """Callback for each received message"""
            try:
                # Parse message data
                message_data = json.loads(message.data.decode("utf-8"))
                
                # Process message
                asyncio.create_task(callback(message_data))
                
                # Acknowledge message
                message.ack()
                
                logger.info(f"Processed message from {subscription_name}")
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                message.nack()  # Requeue message
        
        # Start streaming pull
        streaming_pull_future = self.subscriber.subscribe(
            subscription_path,
            callback=message_callback,
            flow_control=pubsub_v1.types.FlowControl(max_messages=max_messages)
        )
        
        self._subscriptions[subscription_name] = streaming_pull_future
        
        logger.info(f"Subscribed to {subscription_name}")
        
        # Keep subscription alive
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, streaming_pull_future.result
            )
        except Exception as e:
            logger.error(f"Subscription error: {e}")
            streaming_pull_future.cancel()
    
    async def pull_once(
        self,
        subscription_name: str,
        max_messages: int = 1
    ) -> list[Dict[str, Any]]:
        """
        Pull messages once (for Cloud Run Jobs).
        
        Args:
            subscription_name: Name of the subscription
            max_messages: Max messages to pull
            
        Returns:
            List of message data dicts
        """
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_name
        )
        
        # Pull messages
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": max_messages
                },
                retry=retry.Retry(deadline=30)
            )
        )
        
        messages = []
        ack_ids = []
        
        for received_message in response.received_messages:
            # Parse message
            message_data = json.loads(received_message.message.data.decode("utf-8"))
            messages.append(message_data)
            ack_ids.append(received_message.ack_id)
        
        # Acknowledge all messages
        if ack_ids:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.subscriber.acknowledge(
                    request={
                        "subscription": subscription_path,
                        "ack_ids": ack_ids
                    }
                )
            )
        
        logger.info(f"Pulled {len(messages)} messages from {subscription_name}")
        return messages
    
    async def close(self):
        """Close all subscriptions and clients"""
        for sub_name, future in self._subscriptions.items():
            future.cancel()
            logger.info(f"Cancelled subscription: {sub_name}")
        
        self.publisher.close()
        self.subscriber.close()
        logger.info("Pub/Sub client closed")


# Singleton instance
_pubsub_client: Optional[PubSubClient] = None


def get_pubsub_client(project_id: Optional[str] = None) -> PubSubClient:
    """Get or create the singleton Pub/Sub client"""
    global _pubsub_client
    
    if _pubsub_client is None:
        if project_id is None:
            raise ValueError("project_id must be provided on first call")
        _pubsub_client = PubSubClient(project_id)
    
    return _pubsub_client
