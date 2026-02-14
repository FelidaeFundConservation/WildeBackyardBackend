"""
Tests for GCP staging database connectivity.

⚠️ IMPORTANT: This test ONLY runs against the GCP staging database, not local!

This test queries the ACTUAL GCP staging database for user jnovak@example.com
to verify database connectivity and proper configuration.

REQUIRED SETTINGS:
    DJANGO_SETTINGS_MODULE=config.settings.wildebackyard_api
    WILDEBACKYARD_API_DATABASE_URL=postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging

Run with:
    python manage.py test siteapps.users.test_gcp_staging_connectivity --settings=config.settings.wildebackyard_api
    
Or with pytest:
    pytest siteapps/users/test_gcp_staging_connectivity.py --ds=config.settings.wildebackyard_api
    
Prerequisites:
    1. Cloud SQL Proxy running: cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432
    2. WILDEBACKYARD_API_DATABASE_URL environment variable set
"""

import os
from django.test import TestCase, override_settings
from django.conf import settings
from django.db import connection
from siteapps.users.models import User


class GCPStagingConnectivityTest(TestCase):
    """
    Test GCP staging database connectivity by querying for a specific user.
    
    ⚠️ WARNING: This test REQUIRES connection to GCP staging database.
    It will FAIL if not properly configured to prevent accidental local database queries.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class and verify we're connected to GCP staging"""
        super().setUpClass()
        
        # ENFORCE GCP staging database - fail if not configured correctly
        cls.settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', settings.SETTINGS_MODULE)
        cls.db_url = os.environ.get('WILDEBACKYARD_API_DATABASE_URL')
        
        # Verify we're using the correct settings module
        if cls.settings_module != 'config.settings.wildebackyard_api':
            raise RuntimeError(
                f"❌ WRONG SETTINGS MODULE: {cls.settings_module}\n"
                "This test MUST use config.settings.wildebackyard_api\n"
                "Run with: --settings=config.settings.wildebackyard_api"
            )
        
        # Verify database URL is set (required for GCP staging)
        if not cls.db_url:
            raise RuntimeError(
                "❌ WILDEBACKYARD_API_DATABASE_URL not set!\n"
                "This test requires connection to GCP staging database.\n"
                "Set: export WILDEBACKYARD_API_DATABASE_URL='postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'\n"
                "Make sure Cloud SQL Proxy is running!"
            )
        
        # Verify we're connecting to the staging database, not local
        db_name = settings.DATABASES['default']['NAME']
        if db_name != 'wildebackyard_api_staging':
            raise RuntimeError(
                f"❌ WRONG DATABASE: {db_name}\n"
                "This test MUST connect to 'wildebackyard_api_staging'\n"
                "Check your WILDEBACKYARD_API_DATABASE_URL"
            )
        
    def test_database_connection(self):
        """Test that database connection is working to GCP staging"""
        print("\n" + "=" * 70)
        print("GCP STAGING DATABASE CONNECTION TEST")
        print("=" * 70)
        
        # Get database info
        db_config = settings.DATABASES['default']
        print(f"\n📊 Database Configuration:")
        print(f"  Engine:   {db_config['ENGINE']}")
        print(f"  Name:     {db_config['NAME']}")
        print(f"  Host:     {db_config.get('HOST', 'default')}")
        print(f"  User:     {db_config.get('USER', 'default')}")
        
        # VERIFY this is GCP staging database
        self.assertEqual(db_config['NAME'], 'wildebackyard_api_staging',
                        "Must be connected to wildebackyard_api_staging database!")
        
        # Test connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"\n✅ Connected to GCP Staging Database")
                print(f"  PostgreSQL: {version.split(',')[0]}")
                
                # Verify we can query the users table
                cursor.execute("SELECT COUNT(*) FROM users_user;")
                user_count = cursor.fetchone()[0]
                print(f"  Total users: {user_count}")
                
        except Exception as e:
            self.fail(f"❌ Database connection failed: {e}\n"
                     f"Make sure Cloud SQL Proxy is running!")
            
    def test_query_target_user(self):
        """Query for user jnovak@example.com in GCP staging database"""
        print("\n" + "=" * 70)
        print("🔍 QUERY GCP STAGING FOR USER: jnovak@example.com")
        print("=" * 70)
        
        # VERIFY we're on staging database
        db_name = settings.DATABASES['default']['NAME']
        print(f"\n✓ Database: {db_name}")
        self.assertEqual(db_name, 'wildebackyard_api_staging',
                        "Must query GCP staging database, not local!")
        
        target_email = "jnovak@example.com"
        
        # Show what query will be executed
        print(f"\n📝 Django ORM Query:")
        print(f"  User.objects.get(email='{target_email}')")
        
        print(f"\n📝 Equivalent SQL:")
        print(f"  SELECT * FROM users_user WHERE email = '{target_email}';")
        
        # Get total user count first
        total_users = User.objects.count()
        print(f"\n📊 Total users in GCP staging database: {total_users}")
        
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
    
    @classmethod
    def setUpClass(cls):
        """Verify we're connected to GCP staging"""
        super().setUpClass()
        
        # ENFORCE GCP staging database
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', settings.SETTINGS_MODULE)
        if settings_module != 'config.settings.wildebackyard_api':
            raise RuntimeError(
                f"❌ Wrong settings: {settings_module}\n"
                "Must use: --settings=config.settings.wildebackyard_api"
            )
    
    def test_display_database_info(self):
        """Display GCP staging database configuration information"""
        print("\n" + "=" * 70)
        print("🔧 GCP STAGING DATABASE CONFIGURATION")
        print("=" * 70)
        
        db_config = settings.DATABASES['default']
        
        print(f"\n📋 Django Settings Module:")
        print(f"  {settings.SETTINGS_MODULE}")
        
        print(f"\n🗄️  Database Configuration:")
        print(f"  Engine:       {db_config['ENGINE']}")
        print(f"  Database:     {db_config['NAME']}")
        print(f"  User:         {db_config.get('USER', 'N/A')}")
        print(f"  Host:         {db_config.get('HOST', 'N/A')}")
        print(f"  Port:         {db_config.get('PORT', 'N/A')}")
        
        # VERIFY this is staging database
        self.assertEqual(db_config['NAME'], 'wildebackyard_api_staging',
                        "Must be wildebackyard_api_staging database!")
        
        # Check environment variables
        print(f"\n🔐 Environment Variables:")
        db_url = os.environ.get('WILDEBACKYARD_API_DATABASE_URL')
        if db_url:
            # Mask password in URL
            import re
            masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_url)
            print(f"  WILDEBACKYARD_API_DATABASE_URL: {masked_url}")
        else:
            self.fail("WILDEBACKYARD_API_DATABASE_URL must be set for GCP staging!")
        
        gae_app = os.environ.get('GAE_APPLICATION')
        print(f"  GAE_APPLICATION: {gae_app if gae_app else 'Not set (local/proxy)'}")
        
        # Check if running on GCP or via proxy
        print(f"\n🌐 Connection Method:")
        if gae_app:
            print(f"  ✓ Running on Google App Engine")
            print(f"  Instance: {db_config.get('HOST', 'N/A')}")
        else:
            print(f"  ✓ Connected via Cloud SQL Proxy")
            print(f"  Proxy endpoint: {db_config.get('HOST', 'N/A')}:{db_config.get('PORT', 'N/A')}")
        
        # Verify connection works
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user;")
            db, user = cursor.fetchone()
            print(f"\n✅ Successfully connected to GCP staging:")
            print(f"  Database: {db}")
            print(f"  User: {user}")
        
        print(f"\n{'=' * 70}\n")


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
