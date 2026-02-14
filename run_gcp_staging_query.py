#!/usr/bin/env python
"""
GCP Staging Database Query Script
Demonstrates and executes query for user jnovak@example.com

This script will:
1. Show the exact Django ORM query
2. Show the equivalent SQL query  
3. Attempt to connect and execute if credentials are available
4. Provide instructions for running with proper GCP access
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "siteapps"))

def show_query_details():
    """Display the query details"""
    print("=" * 80)
    print("GCP STAGING DATABASE QUERY FOR USER: jnovak@example.com")
    print("=" * 80)
    print()
    
    print("DATABASE CONFIGURATION:")
    print("-" * 80)
    print("  Instance:  wildepod-339517:us-west2:wildepoddb")
    print("  Database:  wildebackyard_api_staging")
    print("  User:      wildepod_wildebackyard_api_user")
    print("  Table:     users_user")
    print("  Settings:  config.settings.wildebackyard_api")
    print()
    
    print("DJANGO ORM QUERY:")
    print("-" * 80)
    print("  from siteapps.users.models import User")
    print("  user = User.objects.get(email='jnovak@example.com')")
    print()
    
    print("EQUIVALENT SQL QUERY:")
    print("-" * 80)
    sql = """  SELECT 
    id, email, name, is_active, is_staff, 
    is_superuser, warnings, bio, created, modified
  FROM users_user 
  WHERE email = 'jnovak@example.com';"""
    print(sql)
    print()

def execute_query():
    """Attempt to execute the query if database is accessible"""
    
    print("ATTEMPTING DATABASE CONNECTION...")
    print("-" * 80)
    
    # Check for database URL
    db_url = os.environ.get("WILDEBACKYARD_API_DATABASE_URL")
    
    if not db_url:
        print("⚠️  WILDEBACKYARD_API_DATABASE_URL not set")
        print()
        print("To connect to GCP staging database, you need to:")
        print()
        print("OPTION 1: Using Cloud SQL Proxy (Recommended)")
        print("  1. Authenticate with GCP:")
        print("     gcloud auth login")
        print("     gcloud config set project wildepod-339517")
        print()
        print("  2. Start Cloud SQL Proxy in Terminal 1:")
        print("     cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432")
        print()
        print("  3. Get database password from Secret Manager:")
        print("     gcloud secrets versions access latest \\")
        print("       --secret=wildebackyard_api_db_password")
        print()
        print("  4. Set environment variable in Terminal 2:")
        print("     export WILDEBACKYARD_API_DATABASE_URL='\\")
        print("       postgres://wildepod_wildebackyard_api_user:PASSWORD@\\")
        print("       127.0.0.1:5432/wildebackyard_api_staging'")
        print()
        print("  5. Run this script:")
        print("     python run_gcp_staging_query.py")
        print()
        print("OPTION 2: Direct gcloud SQL connection")
        print("  gcloud sql connect wildepoddb \\")
        print("    --user=wildepod_wildebackyard_api_user \\")
        print("    --database=wildebackyard_api_staging")
        print()
        print("  Then run SQL query:")
        print("  SELECT * FROM users_user WHERE email = 'jnovak@example.com';")
        print()
        return 1
    
    # Try to connect and query
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.wildebackyard_api")
    
    try:
        import django
        django.setup()
        
        from django.conf import settings
        from siteapps.users.models import User
        from django.db import connection
        
        print("✓ Django initialized")
        print(f"  Settings: {settings.SETTINGS_MODULE}")
        print(f"  Database: {settings.DATABASES['default']['NAME']}")
        print()
        
        # Test connection
        print("Testing database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✓ Connected to PostgreSQL")
            print(f"  Version: {version.split(',')[0]}")
        print()
        
        # Execute the query
        print("Executing query for: jnovak@example.com")
        print("-" * 80)
        
        try:
            user = User.objects.get(email='jnovak@example.com')
            
            # SUCCESS!
            print()
            print("=" * 80)
            print("✅ SUCCESS! USER FOUND IN GCP STAGING DATABASE")
            print("=" * 80)
            print()
            print(f"USER DETAILS:")
            print(f"  ID:           {user.id}")
            print(f"  Email:        {user.email}")
            print(f"  Name:         {user.name}")
            print(f"  Active:       {user.is_active}")
            print(f"  Staff:        {user.is_staff}")
            print(f"  Superuser:    {user.is_superuser}")
            print(f"  Warnings:     {user.warnings}")
            print(f"  Bio:          {user.bio[:100] + '...' if len(user.bio) > 100 else user.bio}")
            print(f"  Created:      {user.created}")
            print(f"  Modified:     {user.modified}")
            print()
            print("=" * 80)
            print("✅ GCP STAGING DATABASE CONNECTIVITY VERIFIED")
            print("=" * 80)
            return 0
            
        except User.DoesNotExist:
            print()
            print("⚠️  User 'jnovak@example.com' NOT FOUND in database")
            print()
            
            # Show what IS in the database
            user_count = User.objects.count()
            print(f"Total users in database: {user_count}")
            
            if user_count > 0:
                print()
                print("First 5 users in database:")
                for i, user in enumerate(User.objects.all()[:5], 1):
                    print(f"  {i}. {user.email:<35} | {user.name}")
                
                # Check for similar emails
                print()
                print("Searching for similar emails containing 'jnovak'...")
                similar = User.objects.filter(email__icontains='jnovak')
                if similar.exists():
                    print("Found:")
                    for user in similar:
                        print(f"  - {user.email:<35} | {user.name}")
                else:
                    print("  No users found with 'jnovak' in email")
                
                # Check for users with example.com domain
                print()
                print("Searching for users with @example.com domain...")
                example_users = User.objects.filter(email__icontains='example.com')
                if example_users.exists():
                    print("Found:")
                    for user in example_users:
                        print(f"  - {user.email:<35} | {user.name}")
                else:
                    print("  No users found with @example.com domain")
            
            print()
            print("=" * 80)
            print("✅ Database connected successfully but user not found")
            print("=" * 80)
            return 2
            
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Main execution"""
    show_query_details()
    return execute_query()

if __name__ == "__main__":
    sys.exit(main())
