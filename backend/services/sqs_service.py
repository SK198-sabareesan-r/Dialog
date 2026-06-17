import json
from typing import Dict, Any, List
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class SQSService:
    """Service for SQS operations - retry and dead-letter queue"""

    def __init__(self):
        self.client = aws_clients.get_sqs_client()
        self.dlq_url = settings.SQS_DLQ_URL
        self.retry_queue_url = settings.SQS_RETRY_QUEUE_URL
        self.max_retries = settings.MAX_RETRY_ATTEMPTS

    def send_to_retry_queue(
        self,
        message_body: Dict[str, Any],
        delay_seconds: int = 0
    ) -> str:
        """Send failed job to retry queue"""
        try:
            response = self.client.send_message(
                QueueUrl=self.retry_queue_url,
                MessageBody=json.dumps(message_body),
                DelaySeconds=delay_seconds
            )

            message_id = response['MessageId']
            logger.info(f"Sent message to retry queue: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to send to retry queue: {str(e)}")
            raise

    def send_to_dlq(
        self,
        message_body: Dict[str, Any],
        error_details: Dict[str, Any]
    ) -> str:
        """Send exhausted retry to dead-letter queue"""
        dlq_message = {
            'original_message': message_body,
            'error': error_details,
            'retry_count': message_body.get('retry_count', 0),
            'timestamp': error_details.get('timestamp')
        }

        try:
            response = self.client.send_message(
                QueueUrl=self.dlq_url,
                MessageBody=json.dumps(dlq_message)
            )

            message_id = response['MessageId']
            logger.warning(f"Sent message to DLQ after {dlq_message['retry_count']} retries: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to send to DLQ: {str(e)}")
            raise

    def receive_messages(
        self,
        queue_url: str,
        max_messages: int = 10,
        wait_time: int = 0
    ) -> List[Dict[str, Any]]:
        """Receive messages from queue"""
        try:
            response = self.client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=['All']
            )

            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from queue")
            return messages

        except Exception as e:
            logger.error(f"Failed to receive messages: {str(e)}")
            raise

    def delete_message(self, queue_url: str, receipt_handle: str) -> bool:
        """Delete message from queue after successful processing"""
        try:
            self.client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info("Deleted message from queue")
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {str(e)}")
            raise

    def get_dlq_count(self) -> int:
        """Get number of messages in DLQ"""
        try:
            response = self.client.get_queue_attributes(
                QueueUrl=self.dlq_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            count = int(response['Attributes']['ApproximateNumberOfMessages'])
            logger.info(f"DLQ message count: {count}")
            return count
        except Exception as e:
            logger.error(f"Failed to get DLQ count: {str(e)}")
            raise

sqs_service = SQSService()
