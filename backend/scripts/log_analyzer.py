"""
Log Analysis Script
Analyze application logs for insights and statistics
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any

LOG_DIR = Path(__file__).parent.parent / 'logs'


def parse_log_line(line: str) -> Dict[str, Any]:
    """Parse a log line into structured data"""
    try:
        # Pattern: 2025-01-15 10:30:45 | INFO | module:function:line | message
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (\w+)\s+\| ([\w.]+):([\w]+):(\d+) \| (.+)'
        match = re.match(pattern, line)

        if match:
            timestamp, level, module, function, line_no, message = match.groups()
            return {
                'timestamp': datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S'),
                'level': level,
                'module': module,
                'function': function,
                'line': int(line_no),
                'message': message
            }
    except Exception:
        pass
    return None


def analyze_errors(log_file: Path, hours: int = 24) -> Dict[str, Any]:
    """Analyze error logs"""
    print(f"\n{'='*80}")
    print(f"ERROR ANALYSIS - Last {hours} hours")
    print(f"{'='*80}")

    cutoff_time = datetime.now() - timedelta(hours=hours)
    errors_by_type = Counter()
    errors_by_module = Counter()
    error_details = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = parse_log_line(line)
                if parsed and parsed['level'] in ['ERROR', 'CRITICAL']:
                    if parsed['timestamp'] >= cutoff_time:
                        errors_by_module[parsed['module']] += 1

                        # Extract error type
                        if 'Exception' in parsed['message']:
                            error_type = re.search(r'(\w+Exception)', parsed['message'])
                            if error_type:
                                errors_by_type[error_type.group(1)] += 1

                        error_details.append({
                            'timestamp': parsed['timestamp'].isoformat(),
                            'module': parsed['module'],
                            'message': parsed['message'][:100]
                        })

        print(f"\nTotal Errors: {len(error_details)}")
        print(f"\nErrors by Module:")
        for module, count in errors_by_module.most_common(10):
            print(f"  {module}: {count}")

        print(f"\nErrors by Type:")
        for error_type, count in errors_by_type.most_common(10):
            print(f"  {error_type}: {count}")

        if error_details:
            print(f"\nRecent Errors (last 5):")
            for error in error_details[-5:]:
                print(f"  [{error['timestamp']}] {error['module']}: {error['message']}")

        return {
            'total_errors': len(error_details),
            'errors_by_module': dict(errors_by_module),
            'errors_by_type': dict(errors_by_type)
        }

    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return {}


def analyze_api_requests(log_file: Path, hours: int = 24) -> Dict[str, Any]:
    """Analyze API request statistics"""
    print(f"\n{'='*80}")
    print(f"API REQUEST ANALYSIS - Last {hours} hours")
    print(f"{'='*80}")

    cutoff_time = datetime.now() - timedelta(hours=hours)
    requests_by_endpoint = Counter()
    requests_by_method = Counter()
    status_codes = Counter()
    durations = defaultdict(list)
    slow_requests = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'API' in line and 'Status:' in line:
                    parsed = parse_log_line(line)
                    if parsed and parsed['timestamp'] >= cutoff_time:
                        # Extract request details
                        match = re.search(r'API (\w+) ([\w/]+) - Status: (\d+) - Duration: ([\d.]+)ms', parsed['message'])
                        if match:
                            method, path, status, duration = match.groups()
                            duration_ms = float(duration)

                            endpoint = f"{method} {path}"
                            requests_by_endpoint[endpoint] += 1
                            requests_by_method[method] += 1
                            status_codes[status] += 1
                            durations[endpoint].append(duration_ms)

                            if duration_ms > 1000:  # Slow request
                                slow_requests.append({
                                    'timestamp': parsed['timestamp'].isoformat(),
                                    'endpoint': endpoint,
                                    'duration_ms': duration_ms
                                })

        print(f"\nTotal Requests: {sum(requests_by_endpoint.values())}")

        print(f"\nRequests by Method:")
        for method, count in requests_by_method.most_common():
            print(f"  {method}: {count}")

        print(f"\nTop 10 Endpoints:")
        for endpoint, count in requests_by_endpoint.most_common(10):
            avg_duration = sum(durations[endpoint]) / len(durations[endpoint])
            print(f"  {endpoint}: {count} requests (avg {avg_duration:.2f}ms)")

        print(f"\nStatus Codes:")
        for code, count in sorted(status_codes.items()):
            print(f"  {code}: {count}")

        if slow_requests:
            print(f"\nSlow Requests (>1s): {len(slow_requests)}")
            for req in slow_requests[-5:]:
                print(f"  [{req['timestamp']}] {req['endpoint']}: {req['duration_ms']:.2f}ms")

        return {
            'total_requests': sum(requests_by_endpoint.values()),
            'requests_by_method': dict(requests_by_method),
            'status_codes': dict(status_codes),
            'slow_requests_count': len(slow_requests)
        }

    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return {}


def analyze_uploads(log_file: Path, hours: int = 24) -> Dict[str, Any]:
    """Analyze file upload statistics"""
    print(f"\n{'='*80}")
    print(f"UPLOAD ANALYSIS - Last {hours} hours")
    print(f"{'='*80}")

    cutoff_time = datetime.now() - timedelta(hours=hours)
    uploads_by_user = Counter()
    uploads_by_source = Counter()
    total_size = 0
    successful_uploads = 0
    failed_uploads = 0

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'Upload -' in line:
                    parsed = parse_log_line(line)
                    if parsed and parsed['timestamp'] >= cutoff_time:
                        # Extract upload details
                        match = re.search(
                            r'Upload - ([\w.]+) \((\d+) bytes\) by ([\w]+) from ([\w_]+)',
                            parsed['message']
                        )
                        if match:
                            filename, size, user_id, source = match.groups()
                            uploads_by_user[user_id] += 1
                            uploads_by_source[source] += 1
                            total_size += int(size)

                            if 'S3:' in parsed['message']:
                                successful_uploads += 1
                            elif 'Failed:' in parsed['message']:
                                failed_uploads += 1

        total_uploads = successful_uploads + failed_uploads
        success_rate = (successful_uploads / total_uploads * 100) if total_uploads > 0 else 0

        print(f"\nTotal Uploads: {total_uploads}")
        print(f"Successful: {successful_uploads}")
        print(f"Failed: {failed_uploads}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Total Size: {total_size / 1024 / 1024:.2f} MB")

        print(f"\nUploads by User:")
        for user, count in uploads_by_user.most_common(10):
            print(f"  {user}: {count}")

        print(f"\nUploads by Source:")
        for source, count in uploads_by_source.most_common():
            print(f"  {source}: {count}")

        return {
            'total_uploads': total_uploads,
            'successful': successful_uploads,
            'failed': failed_uploads,
            'success_rate': success_rate,
            'total_size_mb': total_size / 1024 / 1024,
            'uploads_by_user': dict(uploads_by_user),
            'uploads_by_source': dict(uploads_by_source)
        }

    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return {}


def analyze_queries(log_file: Path, hours: int = 24) -> Dict[str, Any]:
    """Analyze query statistics"""
    print(f"\n{'='*80}")
    print(f"QUERY ANALYSIS - Last {hours} hours")
    print(f"{'='*80}")

    cutoff_time = datetime.now() - timedelta(hours=hours)
    queries_by_user = Counter()
    total_queries = 0
    total_results = 0
    durations = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'Query -' in line:
                    parsed = parse_log_line(line)
                    if parsed and parsed['timestamp'] >= cutoff_time:
                        # Extract query details
                        match = re.search(
                            r'Query - \'(.+)\' by ([\w]+) - (\d+) results in ([\d.]+)ms',
                            parsed['message']
                        )
                        if match:
                            query, user_id, results, duration = match.groups()
                            total_queries += 1
                            queries_by_user[user_id] += 1
                            total_results += int(results)
                            durations.append(float(duration))

        avg_duration = sum(durations) / len(durations) if durations else 0
        avg_results = total_results / total_queries if total_queries > 0 else 0

        print(f"\nTotal Queries: {total_queries}")
        print(f"Total Results: {total_results}")
        print(f"Avg Results per Query: {avg_results:.2f}")
        print(f"Avg Query Duration: {avg_duration:.2f}ms")

        print(f"\nQueries by User:")
        for user, count in queries_by_user.most_common(10):
            print(f"  {user}: {count}")

        return {
            'total_queries': total_queries,
            'total_results': total_results,
            'avg_results': avg_results,
            'avg_duration_ms': avg_duration,
            'queries_by_user': dict(queries_by_user)
        }

    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return {}


def generate_report(hours: int = 24):
    """Generate comprehensive log analysis report"""
    print(f"\n{'#'*80}")
    print(f"# BDA PIPELINE LOG ANALYSIS REPORT")
    print(f"# Generated: {datetime.now().isoformat()}")
    print(f"# Period: Last {hours} hours")
    print(f"{'#'*80}")

    app_log = LOG_DIR / 'application.log'
    error_log = LOG_DIR / 'errors.log'
    activity_log = LOG_DIR / 'activity.log'

    report = {}

    # API requests
    if app_log.exists():
        report['api_requests'] = analyze_api_requests(app_log, hours)

    # Errors
    if error_log.exists():
        report['errors'] = analyze_errors(error_log, hours)

    # Uploads
    if activity_log.exists():
        report['uploads'] = analyze_uploads(activity_log, hours)
        report['queries'] = analyze_queries(activity_log, hours)

    # Save report to JSON
    report_file = LOG_DIR / f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Report saved to: {report_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    import sys

    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    generate_report(hours)
