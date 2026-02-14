#!/usr/bin/env python
"""
Direct Django database query script for GCP staging database.
Queries for user jnovak@example.com to verify database connectivity.

This script can be run directly with Python (no uv needed):
    python query_staging_user.py

Or with Django's management command structure if needed.
"""

import os
import sys
import django
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "siteapps"))

def query_user_directly():
    """Query the database directly for user jnovak@example.com"""
    
    print("=" * 70)
    print("Direct Database Query for User: jnovak@example.com")
    print("=" * 70)
    print()
    
    # Configure Django settings
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.wildebackyard_api")
    
    # Check if database URL is set
    db_url = os.environ.get("WILDEBACKYARD_API_DATABASE_URL")
    if not db_url:
        print("⚠️  WILDEBACKYARD_API_DATABASE_URL not set")
        print()
        print("Attempting to use default local database settings...")
        print()
        # Try local settings instead
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.local"
    
    # Initialize Django
    try:
        django.setup()
    except Exception as e:
        print(f"❌ Error initializing Django: {e}")
        return 1
    
    # Import User model after Django setup
    try:
        from django.conf import settings
        from siteapps.users.models import User
        from django.db import connection
        
        print(f"✓ Django initialized")
        print(f"  Settings: {settings.SETTINGS_MODULE}")
        print(f"  Database: {settings.DATABASES['default']['NAME']}")
        print(f"  Engine: {settings.DATABASES['default']['ENGINE']}")
        print()
        
        # Test database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"✓ Database connected successfully")
                print(f"  PostgreSQL: {version.split(',')[0]}")
                print()
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print()
            return 1
        
        # Query for the specific user
        target_email = "jnovak@example.com"
        print(f"Querying for user: {target_email}")
        print("-" * 70)
        
        try:
            # Execute the query
            user = User.objects.get(email=target_email)
            
            # User found - display details
            print(f"✅ SUCCESS - User found in database!")
            print()
            print(f"User Details:")
            print(f"  ID:         {user.id}")
            print(f"  Email:      {user.email}")
            print(f"  Name:       {user.name}")
            print(f"  Active:     {user.is_active}")
            print(f"  Staff:      {user.is_staff}")
            print(f"  Superuser:  {user.is_superuser}")
            print(f"  Warnings:   {user.warnings}")
            print(f"  Bio:        {user.bio[:50] + '...' if len(user.bio) > 50 else user.bio}")
            print(f"  Created:    {user.created}")
            print(f"  Modified:   {user.modified}")
            print()
            print("=" * 70)
            print("✅ Database query completed successfully")
            print("=" * 70)
            return 0
            
        except User.DoesNotExist:
            # User not found
            print(f"⚠️  User '{target_email}' not found in database")
            print()
            
            # Get total user count
            try:
                user_count = User.objects.count()
                print(f"Total users in database: {user_count}")
                
                if user_count > 0:
                    print()
                    print("Sample users (first 5):")
                    for user in User.objects.all()[:5]:
                        print(f"  - {user.email:<30} | {user.name}")
                    
                    # Check if any users match partial email
                    print()
                    print("Checking for similar emails...")
                    similar_users = User.objects.filter(email__icontains="jnovak")
                    if similar_users.exists():
                        print("Found users with 'jnovak' in email:")
                        for user in similar_users:
                            print(f"  - {user.email:<30} | {user.name}")
                    else:
                        print("  No users found with 'jnovak' in email")
                        
            except Exception as e:
                print(f"Error querying user count: {e}")
            
            print()
            print("=" * 70)
            print("⚠️  Database accessible but user not found")
            print("=" * 70)
            return 2
            
    except ImportError as e:
        print(f"❌ Error importing Django modules: {e}")
        print()
        print("Make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point"""
    return query_user_directly()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
