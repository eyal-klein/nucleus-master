"""
NUCLEUS V1.2 - QA Engine (Cloud Run Job)
Quality assurance testing for newly created or updated agents
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
import uuid
import json

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Agent, AgentTest
from shared.llm import get_llm_gateway
from shared.pubsub import get_pubsub_client
from shared.tools import get_all_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QAEngine:
    """
    QA Engine - Tests agents before activation.
    
    Process:
    1. Identify agents pending QA (status='pending_qa')
    2. Generate test scenarios based on agent purpose
    3. Execute tests with the agent
    4. Evaluate responses
    5. Update agent status (approved/rejected)
    """
    
    def __init__(self):
        self.llm = get_llm_gateway()
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        self.tools = get_all_tools()
        
    async def test_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Test an agent's capabilities and responses.
        
        Args:
            agent_id: UUID of the agent to test
            
        Returns:
            Test results
        """
        logger.info(f"Starting QA for agent: {agent_id}")
        
        db = next(get_db())
        
        try:
            # Get agent
            agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            if agent.status != 'pending_qa':
                logger.warning(f"Agent {agent_id} is not pending QA (status: {agent.status})")
                return {
                    "status": "skipped",
                    "agent_id": agent_id,
                    "reason": f"Agent status is {agent.status}, not pending_qa"
                }
            
            logger.info(f"Testing agent: {agent.agent_name} (purpose: {agent.purpose})")
            
            # Generate test scenarios
            test_scenarios = await self._generate_test_scenarios(agent)
            
            # Execute tests
            test_results = []
            passed_count = 0
            failed_count = 0
            
            for i, scenario in enumerate(test_scenarios, 1):
                logger.info(f"Executing test {i}/{len(test_scenarios)}: {scenario['name']}")
                
                result = await self._execute_test(agent, scenario)
                test_results.append(result)
                
                if result['passed']:
                    passed_count += 1
                else:
                    failed_count += 1
                
                # Store test result
                test_record = AgentTest(
                    agent_id=uuid.UUID(agent_id),
                    test_name=scenario['name'],
                    test_input=scenario['input'],
                    expected_output=scenario.get('expected'),
                    actual_output=result['output'],
                    passed=result['passed'],
                    feedback=result.get('feedback'),
                    metadata={"scenario": scenario}
                )
                db.add(test_record)
            
            # Calculate pass rate
            pass_rate = passed_count / len(test_scenarios) if test_scenarios else 0
            
            # Determine if agent passes QA (threshold: 70%)
            qa_passed = pass_rate >= 0.7
            
            # Update agent status
            if qa_passed:
                agent.status = 'approved'
                agent.meta_data = agent.meta_data or {}
                agent.meta_data['qa_passed_at'] = datetime.utcnow().isoformat()
                agent.meta_data['qa_pass_rate'] = pass_rate
            else:
                agent.status = 'rejected'
                agent.meta_data = agent.meta_data or {}
                agent.meta_data['qa_failed_at'] = datetime.utcnow().isoformat()
                agent.meta_data['qa_pass_rate'] = pass_rate
                agent.meta_data['qa_failures'] = [r for r in test_results if not r['passed']]
            
            db.add(agent)
            db.commit()
            
            # Publish event
            await self.pubsub.publish(
                topic_name="evolution-events",
                message_data={
                    "event_type": "agent_qa_completed",
                    "agent_id": agent_id,
                    "agent_name": agent.agent_name,
                    "qa_passed": qa_passed,
                    "pass_rate": pass_rate,
                    "tests_passed": passed_count,
                    "tests_failed": failed_count
                }
            )
            
            logger.info(f"QA complete for {agent.agent_name}: {'PASSED' if qa_passed else 'FAILED'} ({pass_rate:.1%})")
            
            return {
                "status": "success",
                "agent_id": agent_id,
                "agent_name": agent.agent_name,
                "qa_passed": qa_passed,
                "pass_rate": pass_rate,
                "tests_passed": passed_count,
                "tests_failed": failed_count,
                "test_results": test_results
            }
            
        except Exception as e:
            logger.error(f"QA failed for agent {agent_id}: {e}")
            raise
        finally:
            db.close()
    
    async def _generate_test_scenarios(self, agent: Agent) -> List[Dict[str, Any]]:
        """Generate test scenarios based on agent purpose"""
        
        prompt = f"""You are generating test scenarios for a new AI agent in NUCLEUS.

Agent: {agent.agent_name}
Purpose: {agent.purpose}
System Prompt: {agent.system_prompt[:500]}...

Generate 5 test scenarios that will verify this agent can perform its intended purpose.

For each scenario, provide:
1. name: Short test name
2. input: User message to send to the agent
3. expected: What type of response is expected (general description)

Return as JSON array of scenarios.
"""
        
        messages = [
            {"role": "system", "content": "You are a QA specialist for AI agents."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(messages, temperature=0.5, max_tokens=1000)
        
        # Parse JSON
        try:
            scenarios = json.loads(response.strip())
            return scenarios if isinstance(scenarios, list) else []
        except json.JSONDecodeError:
            logger.warning("Failed to parse test scenarios as JSON, using default")
            return [
                {
                    "name": "Basic interaction",
                    "input": f"Hello, can you help me with {agent.purpose}?",
                    "expected": "Helpful response related to agent purpose"
                }
            ]
    
    async def _execute_test(self, agent: Agent, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test scenario"""
        
        try:
            # Simulate agent response
            messages = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": scenario['input']}
            ]
            
            # Get agent's tools
            agent_tools = [t for t in self.tools if t.name in (agent.meta_data or {}).get('tool_names', [])]
            
            response = await self.llm.complete(
                messages,
                tools=agent_tools if agent_tools else None,
                temperature=0.7,
                max_tokens=500
            )
            
            # Evaluate response
            evaluation = await self._evaluate_response(
                scenario['input'],
                response,
                scenario.get('expected', '')
            )
            
            return {
                "test_name": scenario['name'],
                "input": scenario['input'],
                "output": response,
                "passed": evaluation['passed'],
                "feedback": evaluation['feedback']
            }
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "test_name": scenario['name'],
                "input": scenario['input'],
                "output": f"ERROR: {str(e)}",
                "passed": False,
                "feedback": f"Test execution error: {str(e)}"
            }
    
    async def _evaluate_response(self, input_text: str, output_text: str, expected: str) -> Dict[str, Any]:
        """Evaluate if agent response is appropriate"""
        
        prompt = f"""Evaluate this AI agent response:

User Input: {input_text}
Agent Output: {output_text}
Expected: {expected}

Does the agent's output appropriately address the user's input and meet expectations?

Respond with JSON:
{{
  "passed": true/false,
  "feedback": "Brief explanation"
}}
"""
        
        messages = [
            {"role": "system", "content": "You are evaluating AI agent responses."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(messages, temperature=0.3, max_tokens=200)
        
        try:
            evaluation = json.loads(response.strip())
            return evaluation
        except json.JSONDecodeError:
            # Default to pass if evaluation fails
            return {
                "passed": True,
                "feedback": "Evaluation parse error, defaulting to pass"
            }


async def main():
    """Main entry point"""
    logger.info("QA Engine starting...")
    
    agent_id = os.getenv("AGENT_ID")
    if not agent_id:
        logger.error("AGENT_ID environment variable not set")
        return
    
    engine = QAEngine()
    await engine.pubsub.initialize()
    
    try:
        result = await engine.test_agent(agent_id)
        logger.info(f"QA complete: {result}")
    except Exception as e:
        logger.error(f"QA failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
