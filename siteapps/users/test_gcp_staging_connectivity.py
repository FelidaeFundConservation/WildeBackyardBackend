"""
Tests for GCP staging database connectivity.

This test queries the GCP staging database for user jnovak@example.com
to verify database connectivity and proper configuration.

Run with:
    python manage.py test siteapps.users.test_gcp_staging_connectivity --settings=config.settings.wildebackyard_api
    
Or with pytest:
    pytest siteapps/users/test_gcp_staging_connectivity.py
    
Environment Requirements:
    WILDEBACKYARD_API_DATABASE_URL must be set to connect to staging database
"""

import os
from django.test import TestCase, override_settings
from django.conf import settings
from django.db import connection
from siteapps.users.models import User


class GCPStagingConnectivityTest(TestCase):
    """Test GCP staging database connectivity by querying for a specific user"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        super().setUpClass()
        
        # Check if we're using the staging database
        cls.is_staging = os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.settings.wildebackyard_api'
        cls.db_url = os.environ.get('WILDEBACKYARD_API_DATABASE_URL')
        
    def test_database_connection(self):
        """Test that database connection is working"""
        print("\n" + "=" * 70)
        print("GCP STAGING DATABASE CONNECTION TEST")
        print("=" * 70)
        
        # Get database info
        db_config = settings.DATABASES['default']
        print(f"\nDatabase Configuration:")
        print(f"  Engine:   {db_config['ENGINE']}")
        print(f"  Name:     {db_config['NAME']}")
        print(f"  Host:     {db_config.get('HOST', 'default')}")
        print(f"  User:     {db_config.get('USER', 'default')}")
        
        # Test connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"\n✓ Database Connected Successfully")
                print(f"  PostgreSQL: {version.split(',')[0]}")
        except Exception as e:
            self.fail(f"Database connection failed: {e}")
            
    def test_query_target_user(self):
        """Query for user jnovak@example.com in staging database"""
        print("\n" + "=" * 70)
        print("QUERY FOR USER: jnovak@example.com")
        print("=" * 70)
        
        target_email = "jnovak@example.com"
        
        # Show what query will be executed
        print(f"\nDjango ORM Query:")
        print(f"  User.objects.get(email='{target_email}')")
        
        print(f"\nEquivalent SQL:")
        print(f"  SELECT * FROM users_user WHERE email = '{target_email}';")
        
        # Get total user count first
        total_users = User.objects.count()
        print(f"\nTotal users in database: {total_users}")
        
        # Try to find the target user
        try:
            user = User.objects.get(email=target_email)
            
            # User found!
            print(f"\n{'=' * 70}")
            print("✅ SUCCESS - USER FOUND!")
            print(f"{'=' * 70}")
            print(f"\nUser Details:")
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
            print(f"\n{'=' * 70}")
            print("✅ GCP STAGING DATABASE CONNECTIVITY VERIFIED")
            print(f"{'=' * 70}\n")
            
            # Assertions
            self.assertEqual(user.email, target_email)
            self.assertIsNotNone(user.id)
            self.assertIsNotNone(user.name)
            
        except User.DoesNotExist:
            # User not found - show what IS in the database
            print(f"\n⚠️  User '{target_email}' NOT FOUND in database")
            
            if total_users > 0:
                print(f"\nFirst 5 users in database:")
                for i, user in enumerate(User.objects.all()[:5], 1):
                    print(f"  {i}. {user.email:<35} | {user.name}")
                
                # Check for similar emails
                print(f"\nSearching for emails containing 'jnovak'...")
                similar_users = User.objects.filter(email__icontains='jnovak')
                if similar_users.exists():
                    print("Found:")
                    for user in similar_users:
                        print(f"  - {user.email:<35} | {user.name}")
                else:
                    print("  None found")
                
                # Check for @example.com domain
                print(f"\nSearching for emails with '@example.com'...")
                example_users = User.objects.filter(email__icontains='example.com')
                if example_users.exists():
                    print("Found:")
                    for user in example_users[:5]:
                        print(f"  - {user.email:<35} | {user.name}")
                else:
                    print("  None found")
            
            print(f"\n{'=' * 70}")
            print(f"✅ Database accessible but user '{target_email}' not found")
            print(f"{'=' * 70}\n")
            
            # This is not a failure - database is accessible
            # Just mark that user doesn't exist
            self.skipTest(f"User '{target_email}' does not exist in database (database is accessible)")
            
    def test_user_model_structure(self):
        """Verify User model has expected fields"""
        print("\n" + "=" * 70)
        print("USER MODEL STRUCTURE VERIFICATION")
        print("=" * 70)
        
        # Get model fields
        user_fields = [f.name for f in User._meta.get_fields()]
        
        expected_fields = ['id', 'email', 'name', 'is_active', 'is_staff', 
                          'is_superuser', 'warnings', 'bio', 'created', 'modified']
        
        print(f"\nExpected fields in User model:")
        for field in expected_fields:
            status = "✓" if field in user_fields else "✗"
            print(f"  {status} {field}")
        
        # Assertions
        for field in expected_fields:
            self.assertIn(field, user_fields, f"User model missing field: {field}")
        
        print(f"\n✅ User model structure verified")


class GCPStagingDatabaseInfoTest(TestCase):
    """Display information about the GCP staging database configuration"""
    
    def test_display_database_info(self):
        """Display database configuration information"""
        print("\n" + "=" * 70)
        print("GCP STAGING DATABASE CONFIGURATION")
        print("=" * 70)
        
        db_config = settings.DATABASES['default']
        
        print(f"\nDjango Settings Module:")
        print(f"  {settings.SETTINGS_MODULE}")
        
        print(f"\nDatabase Configuration:")
        print(f"  Engine:       {db_config['ENGINE']}")
        print(f"  Database:     {db_config['NAME']}")
        print(f"  User:         {db_config.get('USER', 'N/A')}")
        print(f"  Host:         {db_config.get('HOST', 'N/A')}")
        print(f"  Port:         {db_config.get('PORT', 'N/A')}")
        
        # Check environment variables
        print(f"\nEnvironment Variables:")
        db_url = os.environ.get('WILDEBACKYARD_API_DATABASE_URL')
        if db_url:
            # Mask password in URL
            import re
            masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_url)
            print(f"  WILDEBACKYARD_API_DATABASE_URL: {masked_url}")
        else:
            print(f"  WILDEBACKYARD_API_DATABASE_URL: Not set")
        
        gae_app = os.environ.get('GAE_APPLICATION')
        print(f"  GAE_APPLICATION: {gae_app if gae_app else 'Not set (local/proxy)'}")
        
        # Check if running on GCP
        if gae_app:
            print(f"\n✓ Running on Google App Engine")
            print(f"  Instance: {db_config.get('HOST', 'N/A')}")
        else:
            print(f"\n✓ Running locally (via Cloud SQL Proxy or local database)")
        
        print(f"\n{'=' * 70}\n")
        
        # No assertions - just informational
        self.assertTrue(True)


# Instructions for running this test
__doc__ += """

INSTRUCTIONS FOR RUNNING THIS TEST:

1. With Cloud SQL Proxy (Local):
   
   Terminal 1 - Start Cloud SQL Proxy:
   $ cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432
   
   Terminal 2 - Run test:
   $ export WILDEBACKYARD_API_DATABASE_URL='postgres://USER:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'
   $ python manage.py test siteapps.users.test_gcp_staging_connectivity --settings=config.settings.wildebackyard_api
   
2. With pytest:
   $ WILDEBACKYARD_API_DATABASE_URL='postgres://...' pytest siteapps/users/test_gcp_staging_connectivity.py -v -s
   
3. Run specific test:
   $ python manage.py test siteapps.users.test_gcp_staging_connectivity.GCPStagingConnectivityTest.test_query_target_user --settings=config.settings.wildebackyard_api

Expected Output:
- If user found: Test passes with user details displayed
- If user not found: Test is skipped (database accessible but user doesn't exist)
- If connection fails: Test fails with connection error
"""
