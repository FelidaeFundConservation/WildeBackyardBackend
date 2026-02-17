# Wilde Backyard Backend

This project uses [uv](https://github.com/astral-sh/uv) for fast and reliable Python package management and PostgreSQL for the database.

## 📚 Documentation

- **[Quick Reference](QUICK_REFERENCE.md)** - Common commands and patterns
- **[Pydantic Guide](PYDANTIC_GUIDE.md)** - Data validation and serialization
- **[Migration Summary](MIGRATION_SUMMARY.md)** - Recent project changes
- **[Version API Documentation](VERSION_API_DOCUMENTATION.md)** - Version information endpoint and release workflow
- **[Moderation Guide](MODERATION_GUIDE.md)** - Content moderation interface and workflows

## Features

- **Django 5.0.2** web framework
- **PostgreSQL** database with Django ORM
- **Pydantic** for data validation and serialization
- **Django REST Framework** for API endpoints
- **Google Cloud Platform** (GCP) for storage, deployment, and logging
- **django-allauth** for authentication
- **uv** for fast package management

## Prerequisites

1. Install [Python 3.10+](https://www.python.org/downloads/)
2. Install [Git](https://git-scm.com/downloads)
3. Install [PostgreSQL](https://www.postgresql.org/download/)
4. Install [ODBC Driver](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16#version-17)

## Quick Setup

### Linux/macOS
```bash
git clone https://github.com/FelidaeFundConservation/WildeBackyardBackend.git
cd WildeBackyardBackend
./setup.sh
```

### Windows
```bash
git clone https://github.com/FelidaeFundConservation/WildeBackyardBackend.git
cd WildeBackyardBackend
setup-win.bat
```

## Manual Setup

1. Clone the repository:
```bash
git clone https://github.com/FelidaeFundConservation/WildeBackyardBackend.git
cd WildeBackyardBackend
```

2. Install uv (if not already installed):
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Create and activate a virtual environment:
```bash
uv venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate.bat
```

4. Install dependencies:
```bash
uv pip install -e .
```

5. Set up PostgreSQL database:
```bash
# Create database and user (if not already exists)
sudo -u postgres psql << 'EOF'
CREATE USER your_user WITH PASSWORD 'your_password';
CREATE DATABASE wildebackyard OWNER your_user;
GRANT ALL PRIVILEGES ON DATABASE wildebackyard TO your_user;
GRANT ALL ON SCHEMA public TO your_user;
\q
EOF
```

6. Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
# Edit .env with your database credentials and other settings
```

7. Run migrations:
```bash
python manage.py migrate --settings=config.settings.local
```

8. Fix package migration files by following the steps below (if needed).

---
## django-rest-passwordreset Package Fix

**Note:** The automated setup scripts handle this automatically.

This project uses the django-rest-passwordreset package.
https://pypi.org/project/django-rest-passwordreset/

However, there is an issue with the token model that causes a NOT NULL constraint error.

### As a current workaround, the the "id" field needs to be removed from the model and migrations for this package.

**Note:** The automated setup scripts handle this automatically. For manual setup:

1. Navigate to the installed package:
   - Linux/macOS: `.venv/lib/python*/site-packages/django_rest_passwordreset`
   - Windows: `.venv\Lib\site-packages\django_rest_passwordreset`
2. Enter the migrations folder.
3. Delete all migration files within the passwordreset package (the numbered ones with 0001_SOMETHING, 0002_SOMETHING, etc).
4. Find the alternative migration file in the Slack channel, or ask for it.
5. Add this alt. migration file in the folder.

<i>The directory should look like this (this is the alternative 0001_initial.py file, not the original)</i>
![image](https://github.com/user-attachments/assets/d958a5aa-2346-4b8d-ae2f-ac8d9ec80e98)


6. Migrate to your local DB.

```
python manage.py migrate --settings=config.settings.local
```

The migrations should now be consistent with the database, and should work locally for development.

---

## ALLOWED_HOSTS Configuration

Django's `ALLOWED_HOSTS` setting controls which host/domain names the application will accept requests from. This project is configured with different behaviors for different environments:

### Non-Production Environments (Local, Staging, GCP Staging)
- **Default behavior**: All hosts are allowed (`ALLOWED_HOSTS = ["*"]`)
- This allows temporary deployments, versioned URLs, and testing without host validation errors
- Safe for non-production as these environments are not publicly exposed or have other security layers
- Configured in:
  - `config/settings/local.py`
  - `config/settings/staging.py`
  - `config/settings/wildebackyard_api.py`

### Production Environment
- **Strict host checking**: Only specific, configured hostnames are allowed
- Environment variable `WEBSITE_HOSTNAME` must be set to the production domain
- This maintains security by preventing host header attacks
- Configured in: `config/settings/prod.py`

**⚠️ Security Note**: Never use `ALLOWED_HOSTS = ["*"]` in production environments as it disables an important security feature that prevents host header attacks.

## Common uv Commands

```bash
# Activate the virtual environment
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate.bat

# Install a new package
uv pip install <package-name>

# Update all packages
uv pip install --upgrade -e .

# Sync dependencies (install/update based on pyproject.toml)
uv pip install -e .
```

---
## Test Run Server

Try running the server to see if it works.
```
python manage.py runserver --settings=config.settings.local
```

To connect to staging or even prod databases, replace "local" with "staging" or "prod."<br>
It's recommended to use the staging environment for development to test with data in the actual Cloud DB.

<i>(!) Please be very careful when working with data while connected to prod, as this is live data seen by users.</i>

## Django Admin Interface

The backend includes a comprehensive Django Admin interface for managing content and moderation.

### Accessing the Admin Interface

1. Create a superuser account (if not already created):
```bash
python manage.py createsuperuser --settings=config.settings.local
```

2. Start the development server:
```bash
python manage.py runserver --settings=config.settings.local
```

3. Navigate to: `http://127.0.0.1:8000/admin/`

4. Log in with your superuser credentials

### Admin Features

- **User Management**: View and manage user accounts, warnings, and permissions
- **Content Moderation**: Review and handle inappropriate content reports
- **Social Media**: Manage posts, comments, and media
- **Species Data**: Manage wildlife species information

### Content Moderation

For detailed instructions on using the moderation interface, see the **[Moderation Guide](MODERATION_GUIDE.md)**.

Key moderation features:
- View all reported content with previews
- Filter by status, date, and user
- Search by user email or warning notes
- Bulk actions: clear reports, issue warnings, ban users
- View user moderation history and warning counts
- Track all moderation decisions for audit purposes

To access the moderation queue:
- Go to: `http://127.0.0.1:8000/admin/socialmedia/inappropriatecontentreport/`
- Or navigate through Admin → Social media → Inappropriate content reports

---
## Developing A Feature
1. Self-assign or request to be assigned an issue.
2. Make sure your local repo is up to date.

```
git checkout main
git pull origin main
```

3. Create a new feature branch with a name which accurately captures the intent. (ex. add_comments_section)

```
git checkout -b <BRANCH_NAME>
```

4. Implement your feature, fix, etc.
5. When done working on the feature, push your local branch to the repo.

```
git push origin <BRANCH_NAME>
```

6. Open a Pull Request, add a reviewer, and link the issue to the PR.
7. After the code is reviewed, merge the branch into main.

<i>Your feature is now integrated!</i>

---
## Deployment Info

### GCP Deployment
This repository uses Google Cloud Platform (GCP) for deployment. The application is deployed to Google App Engine using the `app.yaml` and `staging.yaml` configuration files.

**Note:** See `GCP_DEPLOYMENT_REFERENCE.md` for detailed GCP deployment configuration and manual deployment procedures.
