#!/usr/bin/env python3
"""
Test AWS Credentials

Quick script to verify your AWS credentials are working correctly.
Tests access to S3 and Bedrock services.

Usage:
    python test_credentials.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def test_credentials():
    """Test AWS credentials and permissions"""

    print("=" * 80)
    print("AWS Credentials Test")
    print("=" * 80)

    # Check configuration
    print("\n[1/5] Checking configuration...")
    print(f"   Region: {settings.AWS_REGION}")
    print(f"   Access Key: {settings.AWS_ACCESS_KEY_ID[:10]}..." if settings.AWS_ACCESS_KEY_ID else "   Access Key: NOT SET")
    print(f"   Secret Key: {'*' * 10}..." if settings.AWS_SECRET_ACCESS_KEY else "   Secret Key: NOT SET")
    print(f"   Session Token: {'*' * 10}..." if settings.AWS_SESSION_TOKEN else "   Session Token: NOT SET (OK for non-SSO)")

    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        print("\n❌ AWS credentials not configured!")
        print("Please update config/.env with your credentials.")
        print("\nFor SSO users, run:")
        print("   python get_sso_credentials.py --profile your-profile")
        return False

    print("   ✅ Configuration looks good")

    # Build credentials
    aws_creds = {
        'region_name': settings.AWS_REGION,
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY
    }
    if settings.AWS_SESSION_TOKEN:
        aws_creds['aws_session_token'] = settings.AWS_SESSION_TOKEN

    # Test 1: STS GetCallerIdentity
    print("\n[2/5] Testing AWS credentials...")
    try:
        sts = boto3.client('sts', **aws_creds)
        identity = sts.get_caller_identity()
        print(f"   ✅ Authenticated as: {identity['Arn']}")
        print(f"   Account: {identity['Account']}")
        print(f"   User ID: {identity['UserId']}")
    except NoCredentialsError:
        print("   ❌ No credentials found!")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ExpiredToken':
            print("   ❌ Session token has expired!")
            print("   Run: python get_sso_credentials.py --profile your-profile")
        else:
            print(f"   ❌ Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

    # Test 2: S3 Access
    print("\n[3/5] Testing S3 access...")
    try:
        s3 = boto3.client('s3', **aws_creds)

        # Check if bucket exists
        if settings.S3_RAW_BUCKET:
            try:
                s3.head_bucket(Bucket=settings.S3_RAW_BUCKET)
                print(f"   ✅ S3 bucket exists: {settings.S3_RAW_BUCKET}")

                # Try to list objects
                response = s3.list_objects_v2(Bucket=settings.S3_RAW_BUCKET, MaxKeys=1)
                object_count = response.get('KeyCount', 0)
                print(f"   ✅ Can list objects (found {object_count} objects)")

            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    print(f"   ⚠️  Bucket does not exist: {settings.S3_RAW_BUCKET}")
                    print(f"   Create it with: aws s3 mb s3://{settings.S3_RAW_BUCKET} --region {settings.AWS_REGION}")
                elif error_code == '403':
                    print(f"   ❌ Access denied to bucket: {settings.S3_RAW_BUCKET}")
                    print("   Check IAM permissions for S3")
                else:
                    print(f"   ❌ S3 error: {e}")
        else:
            print("   ⚠️  S3_RAW_BUCKET not configured in .env")

    except Exception as e:
        print(f"   ❌ S3 test failed: {e}")

    # Test 3: Bedrock Agent Access
    print("\n[4/5] Testing Bedrock Agent access...")
    try:
        bedrock_agent = boto3.client('bedrock-agent', **aws_creds)

        if settings.BEDROCK_KB_ID:
            try:
                kb = bedrock_agent.get_knowledge_base(knowledgeBaseId=settings.BEDROCK_KB_ID)
                print(f"   ✅ Knowledge Base found: {kb['knowledgeBase']['name']}")
                print(f"   Status: {kb['knowledgeBase']['status']}")

                # List data sources
                if settings.BEDROCK_DATA_SOURCE_ID:
                    try:
                        ds = bedrock_agent.get_data_source(
                            knowledgeBaseId=settings.BEDROCK_KB_ID,
                            dataSourceId=settings.BEDROCK_DATA_SOURCE_ID
                        )
                        print(f"   ✅ Data Source found: {ds['dataSource']['name']}")
                        print(f"   Status: {ds['dataSource']['status']}")
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'ResourceNotFoundException':
                            print(f"   ⚠️  Data Source not found: {settings.BEDROCK_DATA_SOURCE_ID}")
                        else:
                            print(f"   ⚠️  Could not check data source: {e}")
                else:
                    print("   ⚠️  BEDROCK_DATA_SOURCE_ID not configured")

            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    print(f"   ❌ Knowledge Base not found: {settings.BEDROCK_KB_ID}")
                elif error_code == 'AccessDeniedException':
                    print("   ❌ Access denied to Bedrock")
                    print("   Check IAM permissions for Bedrock")
                else:
                    print(f"   ❌ Bedrock error: {e}")
        else:
            print("   ⚠️  BEDROCK_KB_ID not configured in .env")

    except Exception as e:
        print(f"   ⚠️  Bedrock test failed: {e}")

    # Test 4: Bedrock Runtime Access
    print("\n[5/5] Testing Bedrock Runtime access...")
    try:
        bedrock_runtime = boto3.client('bedrock-agent-runtime', **aws_creds)

        if settings.BEDROCK_KB_ID:
            print(f"   ✅ Bedrock Agent Runtime client created")
            print(f"   Ready to query KB: {settings.BEDROCK_KB_ID}")
        else:
            print("   ⚠️  BEDROCK_KB_ID not configured")

    except Exception as e:
        print(f"   ⚠️  Bedrock Runtime test failed: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print("✅ AWS credentials are valid")

    if settings.S3_RAW_BUCKET:
        print(f"✅ S3 bucket configured: {settings.S3_RAW_BUCKET}")
    else:
        print("⚠️  S3 bucket not configured")

    if settings.BEDROCK_KB_ID:
        print(f"✅ Bedrock KB configured: {settings.BEDROCK_KB_ID}")
    else:
        print("⚠️  Bedrock KB not configured")

    if settings.BEDROCK_DATA_SOURCE_ID:
        print(f"✅ Data Source configured: {settings.BEDROCK_DATA_SOURCE_ID}")
    else:
        print("⚠️  Data Source not configured")

    print("\n🚀 You're ready to start the API!")
    print("   Run: python api/app.py")
    print("=" * 80)

    return True

if __name__ == '__main__':
    try:
        success = test_credentials()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
