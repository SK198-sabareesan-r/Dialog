#!/usr/bin/env python3
"""
Helper script to get AWS SSO credentials and update .env file

Usage:
    python get_sso_credentials.py --profile your-sso-profile

Or manually:
    1. Run: aws sso login --profile your-profile
    2. Run: aws configure export-credentials --profile your-profile --format env
    3. Copy the output to your .env file
"""

import subprocess
import sys
import os
import json
from pathlib import Path

def get_sso_credentials(profile_name=None):
    """Get AWS SSO credentials from AWS CLI"""

    print("=" * 80)
    print("AWS SSO Credentials Helper")
    print("=" * 80)

    # Determine profile
    if not profile_name:
        profile_name = os.getenv('AWS_PROFILE', 'default')
        print(f"\nNo profile specified. Using: {profile_name}")
        print("To use a different profile, run:")
        print(f"  python {sys.argv[0]} --profile your-profile-name\n")

    # Step 1: Check if already logged in
    print(f"\n[1/3] Checking SSO login status for profile '{profile_name}'...")

    try:
        result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity', '--profile', profile_name],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            identity = json.loads(result.stdout)
            print(f"✅ Already logged in as: {identity.get('Arn', 'Unknown')}")
        else:
            print("❌ Not logged in. Attempting SSO login...")

            # Attempt SSO login
            login_result = subprocess.run(
                ['aws', 'sso', 'login', '--profile', profile_name],
                timeout=300  # 5 minutes for user to login
            )

            if login_result.returncode != 0:
                print("\n❌ SSO login failed!")
                print("Please run manually: aws sso login --profile", profile_name)
                sys.exit(1)

            print("✅ SSO login successful!")

    except subprocess.TimeoutExpired:
        print("⏱️  Login timed out. Please try again.")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  Warning: Could not verify login status: {e}")
        print("Continuing anyway...\n")

    # Step 2: Get credentials
    print(f"\n[2/3] Fetching temporary credentials...")

    try:
        result = subprocess.run(
            ['aws', 'configure', 'export-credentials', '--profile', profile_name, '--format', 'env'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"❌ Failed to get credentials: {result.stderr}")
            sys.exit(1)

        # Parse credentials
        credentials = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                credentials[key] = value

        if not credentials:
            print("❌ No credentials found!")
            sys.exit(1)

        print("✅ Credentials retrieved successfully!")

    except subprocess.TimeoutExpired:
        print("⏱️  Credential fetch timed out.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error getting credentials: {e}")
        sys.exit(1)

    # Step 3: Display and optionally update .env
    print(f"\n[3/3] Your temporary AWS credentials:")
    print("=" * 80)
    print(f"AWS_ACCESS_KEY_ID={credentials.get('AWS_ACCESS_KEY_ID', 'NOT_FOUND')}")
    print(f"AWS_SECRET_ACCESS_KEY={credentials.get('AWS_SECRET_ACCESS_KEY', 'NOT_FOUND')}")
    print(f"AWS_SESSION_TOKEN={credentials.get('AWS_SESSION_TOKEN', 'NOT_FOUND')}")
    print("=" * 80)

    # Ask to update .env
    env_path = Path(__file__).parent / 'config' / '.env'

    if env_path.exists():
        response = input(f"\n📝 Update {env_path}? (y/n): ").strip().lower()

        if response == 'y':
            update_env_file(env_path, credentials)
        else:
            print("\n📋 Copy the above credentials to your .env file manually.")
    else:
        print(f"\n⚠️  .env file not found at: {env_path}")
        print("📋 Copy the above credentials to your .env file manually.")

    # Show expiration warning
    print("\n⚠️  IMPORTANT: These are temporary credentials!")
    print("They typically expire in 1-12 hours (depending on your SSO config).")
    print("You'll need to re-run this script when they expire.\n")

def update_env_file(env_path, credentials):
    """Update .env file with new credentials"""

    try:
        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update credentials
        updated_lines = []
        keys_updated = set()

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('AWS_ACCESS_KEY_ID='):
                updated_lines.append(f"AWS_ACCESS_KEY_ID={credentials.get('AWS_ACCESS_KEY_ID', 'NOT_FOUND')}\n")
                keys_updated.add('AWS_ACCESS_KEY_ID')
            elif stripped.startswith('AWS_SECRET_ACCESS_KEY='):
                updated_lines.append(f"AWS_SECRET_ACCESS_KEY={credentials.get('AWS_SECRET_ACCESS_KEY', 'NOT_FOUND')}\n")
                keys_updated.add('AWS_SECRET_ACCESS_KEY')
            elif stripped.startswith('AWS_SESSION_TOKEN='):
                updated_lines.append(f"AWS_SESSION_TOKEN={credentials.get('AWS_SESSION_TOKEN', 'NOT_FOUND')}\n")
                keys_updated.add('AWS_SESSION_TOKEN')
            else:
                updated_lines.append(line)

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)

        print(f"✅ Updated {env_path}")
        print(f"   - AWS_ACCESS_KEY_ID: {'✓' if 'AWS_ACCESS_KEY_ID' in keys_updated else '✗'}")
        print(f"   - AWS_SECRET_ACCESS_KEY: {'✓' if 'AWS_SECRET_ACCESS_KEY' in keys_updated else '✗'}")
        print(f"   - AWS_SESSION_TOKEN: {'✓' if 'AWS_SESSION_TOKEN' in keys_updated else '✗'}")

    except Exception as e:
        print(f"❌ Error updating .env: {e}")
        print("📋 Please update manually.")

if __name__ == '__main__':
    profile = None

    # Parse arguments
    if len(sys.argv) > 2 and sys.argv[1] == '--profile':
        profile = sys.argv[2]
    elif len(sys.argv) > 1 and sys.argv[1] not in ['--help', '-h']:
        print(f"Unknown argument: {sys.argv[1]}")
        print("\nUsage:")
        print(f"  python {sys.argv[0]} --profile your-sso-profile")
        sys.exit(1)
    elif len(sys.argv) > 1:
        print("AWS SSO Credentials Helper")
        print("\nUsage:")
        print(f"  python {sys.argv[0]} --profile your-sso-profile")
        print("\nExample:")
        print(f"  python {sys.argv[0]} --profile dev")
        print(f"  python {sys.argv[0]} --profile production")
        sys.exit(0)

    get_sso_credentials(profile)
