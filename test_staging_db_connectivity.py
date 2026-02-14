#!/usr/bin/env python
"""
Test script to verify GCP staging database connectivity by querying for a specific user.

This script queries the User table in the GCP staging database for the user with
email 'jnovak@example.com' to verify database connectivity.

Usage:
    python test_staging_db_connectivity.py

Prerequisites:
    - WILDEBACKYARD_API_DATABASE_URL environment variable must be set
    - Cloud SQL Proxy running (if connecting locally) OR running on GCP App Engine
    - Django dependencies installed
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "siteapps"))


def main():
    """Query the staging database for user jnovak@example.com"""
    
    print("=" * 70)
    print("GCP Staging Database Connectivity Test")
    print("=" * 70)
    print()
    
    # Check if we have the required environment variable
    db_url = os.environ.get("WILDEBACKYARD_API_DATABASE_URL")
    if not db_url:
        print("⚠️  WARNING: WILDEBACKYARD_API_DATABASE_URL not set")
        print()
        print("To run this test, you need to:")
        print("1. Start Cloud SQL Proxy:")
        print("   cloud-sql-proxy --port 5432 wildepod-339517:us-west2:wildepoddb")
        print()
        print("2. Set the environment variable:")
        print("   export WILDEBACKYARD_API_DATABASE_URL='postgres://USER:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'")
        print()
        print("3. Run this script again:")
        print("   python test_staging_db_connectivity.py")
        print()
        return 1
    
    # Set Django settings module for staging
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.wildebackyard_api")
    
    try:
        import django
        django.setup()
        
        from django.conf import settings
        from siteapps.users.models import User
        
        print("✓ Django initialized successfully")
        print(f"✓ Settings module: {settings.SETTINGS_MODULE}")
        print(f"✓ Database engine: {settings.DATABASES['default']['ENGINE']}")
        print(f"✓ Database name: {settings.DATABASES['default']['NAME']}")
        print(f"✓ Database host: {settings.DATABASES['default'].get('HOST', 'default')}")
        print()
        
        # Test database connectivity
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✓ Database connection successful")
            print(f"  PostgreSQL version: {version[:50]}...")
        print()
        
        # Query for the specific user
        target_email = "jnovak@example.com"
        print(f"Querying for user: {target_email}")
        print("-" * 70)
        
        try:
            user = User.objects.get(email=target_email)
            print(f"✅ USER FOUND!")
            print()
            print(f"User Details:")
            print(f"  ID:       {user.id}")
            print(f"  Email:    {user.email}")
            print(f"  Name:     {user.name}")
            print(f"  Active:   {user.is_active}")
            print(f"  Staff:    {user.is_staff}")
            print(f"  Superuser: {user.is_superuser}")
            print(f"  Warnings: {user.warnings}")
            print(f"  Created:  {user.created}")
            print(f"  Modified: {user.modified}")
            print()
            print("✅ Database connectivity test PASSED")
            return 0
            
        except User.DoesNotExist:
            print(f"❌ User with email '{target_email}' NOT FOUND in database")
            print()
            print("Checking total user count...")
            user_count = User.objects.count()
            print(f"Total users in database: {user_count}")
            
            if user_count > 0:
                print()
                print("Sample users (first 5):")
                for user in User.objects.all()[:5]:
                    print(f"  - {user.email} (ID: {user.id})")
            
            print()
            print("⚠️  The user 'jnovak@example.com' does not exist in the staging database.")
            print("   Database connectivity is working, but this specific user was not found.")
            return 2
            
    except ImportError as e:
        print(f"❌ Error importing Django: {e}")
        print()
        print("Make sure Django and all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print()
        print("Common issues:")
        print("  - Cloud SQL Proxy not running")
        print("  - Incorrect DATABASE_URL")
        print("  - Network connectivity issues")
        print("  - Database credentials incorrect")
        return 1


if __name__ == "__main__":
    sys.exit(main())
