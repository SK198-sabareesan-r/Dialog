"""
Real-time Log Monitor
Watch logs in real-time and send alerts for critical events
"""

import time
import re
from pathlib import Path
from datetime import datetime
from collections import deque
from typing import Deque

LOG_DIR = Path(__file__).parent.parent / 'logs'

# Alert thresholds
ERROR_THRESHOLD = 10  # Alert if >10 errors in 5 minutes
SLOW_REQUEST_THRESHOLD = 5  # Alert if >5 slow requests in 5 minutes
WINDOW_SIZE = 300  # 5 minutes in seconds


class LogMonitor:
    """Monitor logs and trigger alerts"""

    def __init__(self):
        self.error_window: Deque = deque()
        self.slow_request_window: Deque = deque()
        self.last_position = 0

    def clean_windows(self):
        """Remove old entries from sliding windows"""
        current_time = time.time()
        cutoff = current_time - WINDOW_SIZE

        # Clean error window
        while self.error_window and self.error_window[0] < cutoff:
            self.error_window.popleft()

        # Clean slow request window
        while self.slow_request_window and self.slow_request_window[0] < cutoff:
            self.slow_request_window.popleft()

    def check_alerts(self):
        """Check if any alerts should be triggered"""
        self.clean_windows()

        # Check error rate
        if len(self.error_window) >= ERROR_THRESHOLD:
            self.send_alert(
                'ERROR_RATE',
                f"High error rate: {len(self.error_window)} errors in last 5 minutes"
            )

        # Check slow requests
        if len(self.slow_request_window) >= SLOW_REQUEST_THRESHOLD:
            self.send_alert(
                'SLOW_REQUESTS',
                f"High slow request rate: {len(self.slow_request_window)} slow requests in last 5 minutes"
            )

    def send_alert(self, alert_type: str, message: str):
        """Send alert (can be extended to send emails, Slack, etc.)"""
        timestamp = datetime.now().isoformat()
        print(f"\n{'!'*80}")
        print(f"ALERT [{alert_type}] at {timestamp}")
        print(f"{message}")
        print(f"{'!'*80}\n")

        # Write to alerts log
        alerts_log = LOG_DIR / 'alerts.log'
        with open(alerts_log, 'a') as f:
            f.write(f"{timestamp} | {alert_type} | {message}\n")

    def process_line(self, line: str):
        """Process a single log line"""
        current_time = time.time()

        # Check for errors
        if 'ERROR' in line or 'CRITICAL' in line:
            self.error_window.append(current_time)
            print(f"[ERROR] {line.strip()}")

        # Check for slow requests
        if 'Slow request' in line:
            self.slow_request_window.append(current_time)
            duration_match = re.search(r'took ([\d.]+)ms', line)
            if duration_match:
                duration = duration_match.group(1)
                print(f"[SLOW] Request took {duration}ms")

        # Check for failed uploads
        if 'Upload' in line and 'Failed' in line:
            print(f"[UPLOAD FAILED] {line.strip()}")

        # Check for KB sync failures
        if 'KB' in line and ('failed' in line.lower() or 'error' in line.lower()):
            print(f"[KB ERROR] {line.strip()}")

        self.check_alerts()

    def tail_file(self, file_path: Path):
        """Tail a log file and process new lines"""
        print(f"Monitoring: {file_path}")
        print(f"Press Ctrl+C to stop\n")

        try:
            with open(file_path, 'r') as f:
                # Go to end of file
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if line:
                        self.process_line(line)
                    else:
                        time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nMonitoring stopped")
        except FileNotFoundError:
            print(f"Log file not found: {file_path}")


def main():
    """Main monitoring function"""
    print(f"{'='*80}")
    print("BDA Pipeline Log Monitor")
    print(f"{'='*80}")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Alert Thresholds:")
    print(f"  - Errors: >{ERROR_THRESHOLD} in 5 minutes")
    print(f"  - Slow Requests: >{SLOW_REQUEST_THRESHOLD} in 5 minutes")
    print(f"{'='*80}\n")

    monitor = LogMonitor()

    # Monitor application log
    app_log = LOG_DIR / 'application.log'
    if app_log.exists():
        monitor.tail_file(app_log)
    else:
        print(f"Application log not found: {app_log}")
        print("Waiting for log file to be created...")

        # Wait for log file to be created
        while not app_log.exists():
            time.sleep(1)

        monitor.tail_file(app_log)


if __name__ == "__main__":
    main()
