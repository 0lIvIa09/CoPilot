from loguru import logger

from app.connectors.shuffle.schema.integrations import IntegrationRequest
from app.connectors.shuffle.utils.universal import send_post_request


async def execute_integration(request: IntegrationRequest) -> dict:
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info(f"Executing integration: {request}")
    response = await send_post_request("/api/v1/apps/categories/run", request.dict())
    return response
