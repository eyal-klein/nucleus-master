"""
NUCLEUS V1.2 - Integrations API Router
Endpoints for managing third-party service integrations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from backend.shared.models import EntityIntegration, get_db
from backend.shared.utils.credentials_manager import CredentialsManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


# Pydantic models for request/response
class IntegrationCreate(BaseModel):
    """Request model for creating an integration."""
    entity_id: str  # UUID as string
    service_name: str
    service_type: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    credential_type: str
    credentials: Dict[str, Any]  # The actual credentials (will be stored in Secret Manager)
    scopes: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    sync_settings: Optional[Dict[str, Any]] = None
    token_expires_in: Optional[int] = None  # Seconds until token expires


class IntegrationUpdate(BaseModel):
    """Request model for updating an integration."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    sync_settings: Optional[Dict[str, Any]] = None
    token_expires_in: Optional[int] = None


class IntegrationResponse(BaseModel):
    """Response model for integration (without sensitive data)."""
    id: str
    entity_id: str  # UUID as string
    service_name: str
    service_type: str
    display_name: Optional[str]
    description: Optional[str]
    credential_type: str
    status: str
    last_sync_at: Optional[str]
    last_sync_status: Optional[str]
    sync_error_message: Optional[str]
    next_sync_at: Optional[str]
    token_expires_at: Optional[str]
    scopes: Optional[List[str]]
    config: Optional[Dict[str, Any]]
    sync_settings: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]

    class Config:
        from_attributes = True


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration: IntegrationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new third-party service integration.
    
    Stores credentials securely in GCP Secret Manager and metadata in database.
    """
    try:
        # Initialize credentials manager
        creds_manager = CredentialsManager()
        
        # Store credentials in Secret Manager
        secret_path = creds_manager.store_credentials(
            entity_id=integration.entity_id,
            service_name=integration.service_name,
            credentials=integration.credentials
        )
        
        # Calculate token expiration if provided
        token_expires_at = None
        if integration.token_expires_in:
            token_expires_at = datetime.utcnow() + timedelta(seconds=integration.token_expires_in)
        
        # Create database record
        db_integration = EntityIntegration(
            entity_id=integration.entity_id,
            service_name=integration.service_name,
            service_type=integration.service_type,
            display_name=integration.display_name or integration.service_name.title(),
            description=integration.description,
            secret_path=secret_path,
            credential_type=integration.credential_type,
            status="active",
            token_expires_at=token_expires_at,
            scopes=integration.scopes,
            config=integration.config or {},
            sync_settings=integration.sync_settings or {},
            created_by="api"
        )
        
        db.add(db_integration)
        db.commit()
        db.refresh(db_integration)
        
        logger.info(f"Created integration {db_integration.id} for entity {integration.entity_id}")
        
        return db_integration.to_dict()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create integration: {str(e)}"
        )


@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    entity_id: Optional[str] = None,
    service_name: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all integrations with optional filters.
    """
    try:
        query = db.query(EntityIntegration)
        
        if entity_id:
            query = query.filter(EntityIntegration.entity_id == entity_id)
        
        if service_name:
            query = query.filter(EntityIntegration.service_name == service_name)
        
        if status_filter:
            query = query.filter(EntityIntegration.status == status_filter)
        
        integrations = query.all()
        
        return [integration.to_dict() for integration in integrations]
        
    except Exception as e:
        logger.error(f"Failed to list integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list integrations: {str(e)}"
        )


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific integration by ID.
    """
    try:
        integration = db.query(EntityIntegration).filter(
            EntityIntegration.id == integration_id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_id} not found"
            )
        
        return integration.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration: {str(e)}"
        )


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: str,
    update: IntegrationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing integration.
    """
    try:
        integration = db.query(EntityIntegration).filter(
            EntityIntegration.id == integration_id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_id} not found"
            )
        
        # Update credentials if provided
        if update.credentials:
            creds_manager = CredentialsManager()
            creds_manager.update_credentials(
                entity_id=integration.entity_id,
                service_name=integration.service_name,
                credentials=update.credentials
            )
        
        # Update token expiration if provided
        if update.token_expires_in:
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=update.token_expires_in)
        
        # Update other fields
        if update.display_name is not None:
            integration.display_name = update.display_name
        if update.description is not None:
            integration.description = update.description
        if update.status is not None:
            integration.status = update.status
        if update.config is not None:
            integration.config = update.config
        if update.sync_settings is not None:
            integration.sync_settings = update.sync_settings
        
        db.commit()
        db.refresh(integration)
        
        logger.info(f"Updated integration {integration_id}")
        
        return integration.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update integration: {str(e)}"
        )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an integration and its credentials.
    """
    try:
        integration = db.query(EntityIntegration).filter(
            EntityIntegration.id == integration_id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_id} not found"
            )
        
        # Delete credentials from Secret Manager
        creds_manager = CredentialsManager()
        creds_manager.delete_credentials(
            entity_id=integration.entity_id,
            service_name=integration.service_name
        )
        
        # Delete database record
        db.delete(integration)
        db.commit()
        
        logger.info(f"Deleted integration {integration_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete integration: {str(e)}"
        )


@router.post("/{integration_id}/test", response_model=Dict[str, Any])
async def test_integration(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """
    Test if an integration's credentials are valid.
    """
    try:
        integration = db.query(EntityIntegration).filter(
            EntityIntegration.id == integration_id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_id} not found"
            )
        
        # Test credentials
        creds_manager = CredentialsManager()
        is_valid = creds_manager.test_credentials(
            entity_id=integration.entity_id,
            service_name=integration.service_name
        )
        
        return {
            "integration_id": str(integration_id),
            "service_name": integration.service_name,
            "is_valid": is_valid,
            "tested_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test integration: {str(e)}"
        )


@router.post("/{integration_id}/sync", response_model=Dict[str, Any])
async def trigger_sync(
    integration_id: str,
    db: Session = Depends(get_db)
):
    """
    Trigger a manual sync for an integration.
    
    This will be expanded later to actually perform the sync.
    For now, it just updates the sync timestamp.
    """
    try:
        integration = db.query(EntityIntegration).filter(
            EntityIntegration.id == integration_id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_id} not found"
            )
        
        if integration.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot sync inactive integration"
            )
        
        # Update sync timestamp
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_status = "success"
        integration.sync_error_message = None
        
        # Schedule next sync (example: 1 hour from now)
        integration.next_sync_at = datetime.utcnow() + timedelta(hours=1)
        
        db.commit()
        
        logger.info(f"Triggered sync for integration {integration_id}")
        
        return {
            "integration_id": str(integration_id),
            "service_name": integration.service_name,
            "sync_triggered_at": integration.last_sync_at.isoformat(),
            "next_sync_at": integration.next_sync_at.isoformat() if integration.next_sync_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to trigger sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {str(e)}"
        )



@router.get("/debug/schema-info", response_model=Dict[str, Any])
async def get_schema_info(db: Session = Depends(get_db)):
    """
    Debug endpoint to check database schema state.
    
    Returns information about:
    - Entity tables existence
    - Migration history
    - Schema search path
    - Entity count
    """
    try:
        # Check if entity tables exist
        result = db.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE '%entity%'
            ORDER BY table_schema, table_name;
        """))
        tables = [{"schema": row[0], "table": row[1]} for row in result]
        
        # Check migrations
        migrations_result = db.execute(text("""
            SELECT migration_name, applied_at 
            FROM public.migrations 
            ORDER BY applied_at;
        """))
        migration_list = [{"name": row[0], "applied_at": str(row[1])} for row in migrations_result]
        
        # Check search path
        search_path_result = db.execute(text("SHOW search_path;"))
        search_path = search_path_result.scalar()
        
        # Try to count entities in dna.entity
        entity_count = None
        entity_error = None
        try:
            count_result = db.execute(text("SELECT COUNT(*) FROM dna.entity;"))
            entity_count = count_result.scalar()
        except Exception as e:
            entity_error = str(e)
        
        # Try to get sample entities
        sample_entities = []
        try:
            sample_result = db.execute(text("SELECT id, name, created_at FROM dna.entity LIMIT 5;"))
            sample_entities = [
                {"id": str(row[0]), "name": row[1], "created_at": str(row[2])} 
                for row in sample_result
            ]
        except Exception as e:
            sample_entities = [{"error": str(e)}]
        
        # Check entity_integrations table
        integrations_count = None
        integrations_error = None
        try:
            int_count_result = db.execute(text("SELECT COUNT(*) FROM dna.entity_integrations;"))
            integrations_count = int_count_result.scalar()
        except Exception as e:
            integrations_error = str(e)
        
        return {
            "status": "success",
            "database": {
                "search_path": search_path,
                "tables_with_entity": tables,
                "migrations_applied": migration_list
            },
            "dna_entity": {
                "count": entity_count,
                "error": entity_error,
                "sample_entities": sample_entities
            },
            "entity_integrations": {
                "count": integrations_count,
                "error": integrations_error
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Debug endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug endpoint failed: {str(e)}"
        )
