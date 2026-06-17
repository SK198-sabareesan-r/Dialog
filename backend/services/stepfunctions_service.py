import json
from typing import Dict, Any
from datetime import datetime
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class StepFunctionsService:
    """Service for AWS Step Functions orchestration"""

    def __init__(self):
        self.client = aws_clients.get_stepfunctions_client()
        self.state_machine_arn = settings.STEP_FUNCTION_ARN

    def start_execution(
        self,
        input_data: Dict[str, Any],
        execution_name: str = None
    ) -> Dict[str, Any]:
        """
        Start Step Functions execution for ingestion pipeline

        Args:
            input_data: Input data including S3 keys, metadata, etc.
            execution_name: Optional custom execution name

        Returns:
            Execution details
        """
        if not execution_name:
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            execution_name = f"ingestion-{timestamp}"

        try:
            response = self.client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )

            execution_arn = response['executionArn']
            logger.info(f"Started Step Functions execution: {execution_arn}")

            return {
                'execution_arn': execution_arn,
                'execution_name': execution_name,
                'start_date': response['startDate'].isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to start Step Functions execution: {str(e)}")
            raise

    def get_execution_status(self, execution_arn: str) -> Dict[str, Any]:
        """Get status of Step Functions execution"""
        try:
            response = self.client.describe_execution(
                executionArn=execution_arn
            )

            result = {
                'execution_arn': execution_arn,
                'status': response['status'],
                'start_date': response['startDate'].isoformat(),
                'input': json.loads(response['input'])
            }

            if 'stopDate' in response:
                result['stop_date'] = response['stopDate'].isoformat()

            if 'output' in response:
                result['output'] = json.loads(response['output'])

            if 'error' in response:
                result['error'] = response['error']
                result['cause'] = response.get('cause')

            return result

        except Exception as e:
            logger.error(f"Failed to get execution status: {str(e)}")
            raise

    def list_executions(
        self,
        status_filter: str = None,
        max_results: int = 100
    ) -> list:
        """List Step Functions executions"""
        params = {
            'stateMachineArn': self.state_machine_arn,
            'maxResults': max_results
        }

        if status_filter:
            params['statusFilter'] = status_filter

        try:
            response = self.client.list_executions(**params)
            return response.get('executions', [])
        except Exception as e:
            logger.error(f"Failed to list executions: {str(e)}")
            raise

    def stop_execution(
        self,
        execution_arn: str,
        error: str = "Manual stop",
        cause: str = "Stopped by user"
    ) -> bool:
        """Stop a running execution"""
        try:
            self.client.stop_execution(
                executionArn=execution_arn,
                error=error,
                cause=cause
            )
            logger.info(f"Stopped execution: {execution_arn}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop execution: {str(e)}")
            raise

stepfunctions_service = StepFunctionsService()
