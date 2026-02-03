# Copilot Instructions for Wilde Backyard Backend

## Repository Overview

This is a Django 5.0.2 REST API backend for the Wilde Backyard wildlife conservation platform. The project uses PostgreSQL for the database, Pydantic for data validation, Django REST Framework for API endpoints, and Azure for cloud services (storage, key vault). The codebase is approximately medium-sized with 4 main Django apps.

**Stack:** Python 3.10+, Django 5.0.2, PostgreSQL, Pydantic 2.9.2, Django REST Framework, Azure Cloud
**Package Manager:** uv (fast Python package manager)
**Deployment:** Azure App Service with CI/CD via GitHub Actions

## Project Layout

### Key Directories and Files

- **siteapps/** - Main application directory containing Django apps
  - **users/** - User authentication and profile management
  - **socialmedia/** - Social media posts and moderation features
  - **species/** - Wildlife species data management
  - **mapbox/** - Location/mapping functionality
  - **templates/** - Django templates
- **config/** - Django configuration directory
  - **settings/base.py** - Base settings shared across environments
  - **settings/local.py** - Local development settings
  - **settings/staging.py** - Staging environment settings
  - **settings/prod.py** - Production settings
  - **urls.py** - URL routing configuration
  - **wsgi/** - WSGI configuration
- **gcp_deployment/** - Google Cloud Platform deployment scripts and documentation
- **staticfiles/** - Collected static files (generated, do not edit directly)
- **.github/workflows/** - CI/CD workflows
  - **main_wildebackyard.yml** - Azure deployment workflow (runs on push to main)

### Key Configuration Files

- **pyproject.toml** - Project metadata and dependencies (Python 3.10+)
- **requirements.txt** - Production dependencies
- **requirements-dev.txt** - Development dependencies (pytest, black, flake8, isort, pre-commit)
- **pytest.ini** - Pytest configuration (uses `--no-migrations --reuse-db` for speed)
- **.coveragerc** - Test coverage configuration
- **.env.example** - Environment variables template
- **manage.py** - Django management script

### Important Documentation Files

- **README.md** - Main project documentation
- **QUICK_REFERENCE.md** - Common commands and patterns reference
- **TEST_COVERAGE_REPORT.md** - Test coverage status

## Build and Validation Instructions

### Prerequisites

1. Python 3.10 or higher must be installed
2. PostgreSQL must be installed and running
3. ODBC Driver 17 must be installed (for SQL Server support)
4. uv package manager should be installed

### Environment Setup (CRITICAL STEPS)

**ALWAYS follow these steps for a clean setup:**

1. Install uv if not installed:
   ```bash
   # Linux/macOS
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. Create virtual environment:
   ```bash
   uv venv
   ```

3. Activate virtual environment:
   ```bash
   # Linux/macOS
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate.bat
   ```

4. Install dependencies:
   ```bash
   uv pip install -e .
   ```

5. Install development dependencies (for testing/linting):
   ```bash
   uv pip install -r requirements-dev.txt
   ```

6. Set up PostgreSQL database:
   ```bash
   sudo -u postgres psql << 'EOF'
   CREATE USER your_user WITH PASSWORD 'your_password';
   CREATE DATABASE wildebackyard OWNER your_user;
   GRANT ALL PRIVILEGES ON DATABASE wildebackyard TO your_user;
   GRANT ALL ON SCHEMA public TO your_user;
   \q
   EOF
   ```

7. Create .env file from template:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

8. **CRITICAL:** Fix django-rest-passwordreset package migration:
   - This package has a known issue with token model NOT NULL constraint
   - Navigate to `.venv/lib/python*/site-packages/django_rest_passwordreset/migrations/`
   - Delete numbered migration files (0001_*, 0002_*, etc.)
   - Replace with corrected migration file (contact team or check Slack for file)
   - This step is REQUIRED before running migrations

9. Run migrations:
   ```bash
   python manage.py migrate --settings=config.settings.local
   ```

### Running the Development Server

```bash
python manage.py runserver --settings=config.settings.local
# Server starts at http://127.0.0.1:8000/
```

**Note:** You can connect to different environments by changing the settings:
- `--settings=config.settings.local` - Local development
- `--settings=config.settings.staging` - Staging database (recommended for testing)
- `--settings=config.settings.prod` - Production (CAUTION: live data)

### Testing

**ALWAYS run tests before committing code changes.**

```bash
# Run all tests
python manage.py test --settings=config.settings.local

# Run tests for specific app
python manage.py test siteapps.users --settings=config.settings.local

# Run with pytest (configured in pytest.ini)
pytest

# Run with coverage
coverage run --source='.' manage.py test --settings=config.settings.local
coverage report
```

**Test Configuration:**
- Tests use `--no-migrations` flag for speed (defined in pytest.ini)
- Tests use `--reuse-db` to avoid recreating database each time
- Test files: `test_*.py`, `*_test.py`, or `tests.py` in siteapps directory

### Linting and Code Quality

The project uses multiple linting tools (defined in requirements-dev.txt):

```bash
# Format code with black
black siteapps config

# Sort imports with isort
isort siteapps config

# Run flake8 linting
flake8 siteapps config

# Clean unused imports with pycln
pycln siteapps config

# Django template linting
djlint siteapps/templates
```

**ALWAYS run linters before committing.** If pre-commit hooks are configured, they will run automatically.

### Database Operations

```bash
# Create new migrations after model changes
python manage.py makemigrations --settings=config.settings.local

# Apply migrations
python manage.py migrate --settings=config.settings.local

# Show migration status
python manage.py showmigrations --settings=config.settings.local

# Create superuser
python manage.py createsuperuser --settings=config.settings.local

# Open Django shell
python manage.py shell --settings=config.settings.local

# Open database shell
python manage.py dbshell --settings=config.settings.local
```

### Static Files

```bash
python manage.py collectstatic --settings=config.settings.local --noinput
```

## Common Development Patterns

### Working with Pydantic

This project uses Pydantic 2.9.2 for data validation. See PYDANTIC_GUIDE.md for detailed patterns.

**Validating request data:**
```python
from pydantic import ValidationError
from .schemas import UserCreate

try:
    user_data = UserCreate(**request.data)
except ValidationError as e:
    return Response({'errors': e.errors()}, status=400)
```

**Converting Django models to Pydantic:**
```python
from .schemas import UserResponse

user = User.objects.get(id=user_id)
response_data = UserResponse.model_validate(user)
return Response(response_data.model_dump())
```

### Django ORM Best Practices

- Use `select_related()` for foreign keys to avoid N+1 queries
- Use `prefetch_related()` for many-to-many relationships
- Add database indexes to frequently queried fields
- Use bulk operations for multiple inserts/updates

## Git Workflow

```bash
# Always work on feature branches
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Make changes, then push
git add .
git commit -m "Description of changes"
git push origin feature/your-feature-name

# Open Pull Request, add reviewer, link issue
```

## CI/CD Pipeline

The repository has Azure CI/CD configured via `.github/workflows/main_wildebackyard.yml`:
- Triggers on push to main branch
- Uses Python 3.12 for build (note: project requires 3.10+)
- Installs dependencies from requirements.txt
- Creates zip artifact and deploys to Azure App Service

**Important:** Tests are not currently automated in CI (see comment in workflow file). Run tests locally before pushing.

## Deployment

Pushes or merges to `staging` or `prod` branches automatically deploy to the respective Azure App Service environment via CI/CD.

**CAUTION:** Production branch contains live user data. Be very careful when working with prod environment.

## Common Issues and Workarounds

### django-rest-passwordreset Migration Issue

**Problem:** NOT NULL constraint error on token model
**Solution:** Delete numbered migration files and replace with corrected version (see Environment Setup step 8)
**Status:** Known issue, workaround is required for all setups

### Database Connection Issues

```bash
# Test PostgreSQL connection
PGPASSWORD='your_password' psql -U your_user -d wildebackyard -h localhost -c "\conninfo"

# Check PostgreSQL service
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Clear Python Cache

```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Security Reminders

- Never commit .env file (included in .gitignore)
- Use strong SECRET_KEY in production
- Set DEBUG=False in production
- Use HTTPS in production
- Keep dependencies updated regularly

## Additional Resources

- Django 5.0 documentation: https://docs.djangoproject.com/en/5.0/
- Pydantic documentation: https://docs.pydantic.dev/
- Django REST Framework: https://www.django-rest-framework.org/
- uv documentation: https://github.com/astral-sh/uv

## Instructions for Copilot Coding Agent

**Trust these instructions.** Only search for additional information if these instructions are incomplete or found to be incorrect.

**When making code changes:**
1. Activate virtual environment first
2. Install dependencies if needed
3. Check which Django app the change belongs to (users, socialmedia, species, mapbox)
4. Follow existing code patterns in that app
5. Use Pydantic for data validation where appropriate
6. Write or update tests for your changes
7. Run tests before committing: `pytest` or `python manage.py test --settings=config.settings.local`
8. Run linters if development dependencies are installed
9. Use the appropriate settings module (usually local for development)

**When working with models:**
1. Make changes to Django model classes
2. Create migrations: `python manage.py makemigrations --settings=config.settings.local`
3. Review generated migration files
4. Apply migrations: `python manage.py migrate --settings=config.settings.local`
5. Update corresponding Pydantic schemas if they exist
6. Update or add tests for model changes

**When debugging:**
- Use Django shell: `python manage.py shell --settings=config.settings.local`
- Check server logs from `python manage.py runserver`
- Use database shell for SQL queries: `python manage.py dbshell --settings=config.settings.local`
- Review test output for detailed error messages
