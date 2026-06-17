# Log Analysis Scripts

Utility scripts for analyzing and monitoring application logs.

## Scripts

### 1. log_analyzer.py

Analyzes application logs and generates statistical reports.

**Usage:**
```bash
# Analyze last 24 hours (default)
python scripts/log_analyzer.py

# Analyze last 12 hours
python scripts/log_analyzer.py 12

# Analyze last 7 days
python scripts/log_analyzer.py 168
```

**Analyzes:**
- API request statistics
- Error rates and types
- Upload activity
- Query performance
- User activity

**Output:**
- Console report with statistics
- JSON report saved to `logs/report_TIMESTAMP.json`

### 2. monitor_logs.py

Real-time log monitoring with alerts.

**Usage:**
```bash
python scripts/monitor_logs.py
```

**Monitors:**
- Error rates (alerts if >10 errors in 5 minutes)
- Slow requests (alerts if >5 slow requests in 5 minutes)
- Failed uploads
- KB sync failures

**Alerts:**
- Printed to console
- Logged to `logs/alerts.log`

## Examples

### Daily Report

Run this via cron for daily reports:
```bash
# Add to crontab
0 0 * * * cd /path/to/backend && python scripts/log_analyzer.py 24 > /dev/null
```

### Continuous Monitoring

Run in a separate terminal or as a service:
```bash
python scripts/monitor_logs.py
```

### Quick Statistics

```bash
# Count total requests today
grep "API" logs/application.log | grep "$(date +%Y-%m-%d)" | wc -l

# Count errors today
grep "ERROR" logs/errors.log | grep "$(date +%Y-%m-%d)" | wc -l

# Average response time
grep "Duration:" logs/application.log | grep -oP "Duration: \K[0-9.]+" | \
  awk '{sum+=$1; count++} END {print sum/count " ms"}'
```
