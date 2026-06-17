from datetime import datetime
from typing import Dict, Any, List
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class MonitoringService:
    """Service for CloudWatch monitoring and alarms"""

    def __init__(self):
        self.cloudwatch_client = aws_clients.get_cloudwatch_client()
        self.sns_client = aws_clients.get_sns_client()
        self.log_group = settings.CLOUDWATCH_LOG_GROUP
        self.alarm_topic = settings.ALARM_SNS_TOPIC_ARN

    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'Count',
        dimensions: List[Dict[str, str]] = None
    ) -> bool:
        """Log custom metric to CloudWatch"""
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }

        if dimensions:
            metric_data['Dimensions'] = dimensions

        try:
            self.cloudwatch_client.put_metric_data(
                Namespace='IngestionPipeline',
                MetricData=[metric_data]
            )
            logger.debug(f"Logged metric {metric_name}: {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to log metric: {str(e)}")
            return False

    def log_ingestion_success(self, source: str, file_count: int = 1):
        """Log successful ingestion"""
        self.log_metric(
            'IngestionSuccess',
            file_count,
            dimensions=[{'Name': 'Source', 'Value': source}]
        )

    def log_ingestion_failure(self, source: str, error_type: str):
        """Log ingestion failure"""
        self.log_metric(
            'IngestionFailure',
            1,
            dimensions=[
                {'Name': 'Source', 'Value': source},
                {'Name': 'ErrorType', 'Value': error_type}
            ]
        )

    def log_processing_duration(self, stage: str, duration_seconds: float):
        """Log processing duration for a stage"""
        self.log_metric(
            'ProcessingDuration',
            duration_seconds,
            unit='Seconds',
            dimensions=[{'Name': 'Stage', 'Value': stage}]
        )

    def log_dlq_count(self, count: int):
        """Log DLQ message count"""
        self.log_metric('DLQMessageCount', count)

    def send_alarm(
        self,
        subject: str,
        message: str,
        severity: str = 'ERROR'
    ) -> str:
        """Send alarm notification via SNS"""
        full_message = f"[{severity}] {message}\n\nTimestamp: {datetime.utcnow().isoformat()}"

        try:
            response = self.sns_client.publish(
                TopicArn=self.alarm_topic,
                Subject=subject,
                Message=full_message
            )

            message_id = response['MessageId']
            logger.warning(f"Sent alarm notification: {subject}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to send alarm: {str(e)}")
            raise

    def check_dlq_threshold(self, threshold: int = 10):
        """Check if DLQ exceeds threshold and send alarm"""
        from .sqs_service import sqs_service

        try:
            dlq_count = sqs_service.get_dlq_count()
            self.log_dlq_count(dlq_count)

            if dlq_count >= threshold:
                self.send_alarm(
                    subject=f"DLQ Threshold Exceeded: {dlq_count} messages",
                    message=f"Dead-letter queue has {dlq_count} messages, exceeding threshold of {threshold}. Investigate failed ingestions.",
                    severity='CRITICAL'
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to check DLQ threshold: {str(e)}")
            raise

    def get_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        period: int = 300
    ) -> List[Dict[str, Any]]:
        """Get metric statistics from CloudWatch"""
        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='IngestionPipeline',
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Sum', 'Average', 'Maximum']
            )
            return response.get('Datapoints', [])
        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}")
            raise

monitoring_service = MonitoringService()
