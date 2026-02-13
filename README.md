# Wilde Backyard Backend

This project uses [uv](https://github.com/astral-sh/uv) for fast and reliable Python package management and PostgreSQL for the database.

## 📚 Documentation

- **[Quick Reference](QUICK_REFERENCE.md)** - Common commands and patterns
- **[Pydantic Guide](PYDANTIC_GUIDE.md)** - Data validation and serialization
- **[Migration Summary](MIGRATION_SUMMARY.md)** - Recent project changes
- **[Version API Documentation](VERSION_API_DOCUMENTATION.md)** - Version information endpoint and release workflow

## Features

- **Django 5.0.2** web framework
- **PostgreSQL** database with Django ORM
- **Pydantic** for data validation and serialization
- **Django REST Framework** for API endpoints
- **Azure** integration for storage and key vault
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

### Azure Deployment
This repository is connected to Azure CI/CD via the `main_wildebackyard.yml` workflow. Pushes or merges into the `main` branch will automatically deploy the code to Azure App Service.

### GCP Deployment
The repository includes a GCP staging deployment workflow (`deploy-staging-example.yml`) that can be enabled for Google Cloud Platform deployments. When enabled, this workflow triggers on pushes to the `main` branch and deploys to Google App Engine.

**Note:** See `GCP_DEPLOYMENT_REFERENCE.md` for detailed GCP deployment configuration and manual deployment procedures.
