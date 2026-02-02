# Quick Reference

## Daily Development Commands

### Activate Virtual Environment
```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate.bat
```

### Run Development Server
```bash
python manage.py runserver --settings=config.settings.local
# Server will start at http://127.0.0.1:8000/
```

### Database Commands
```bash
# Run migrations
python manage.py migrate --settings=config.settings.local

# Create new migration after model changes
python manage.py makemigrations --settings=config.settings.local

# Open database shell
python manage.py dbshell --settings=config.settings.local

# Create superuser
python manage.py createsuperuser --settings=config.settings.local
```

### Django Shell
```bash
# Interactive Python shell with Django context
python manage.py shell --settings=config.settings.local
```

### Package Management with uv
```bash
# Install new package
uv pip install package-name

# Install all dependencies
uv pip install -e .

# Update all packages
uv pip install --upgrade -e .

# List installed packages
uv pip list

# Freeze current packages (for requirements.txt)
uv pip freeze
```

### Testing
```bash
# Run all tests
python manage.py test --settings=config.settings.local

# Run specific app tests
python manage.py test siteapps.users --settings=config.settings.local

# Run with coverage
coverage run --source='.' manage.py test --settings=config.settings.local
coverage report
```

### Static Files
```bash
# Collect static files
python manage.py collectstatic --settings=config.settings.local --noinput
```

### Database Backup & Restore
```bash
# Backup database
pg_dump -U jnovak -h localhost wildebackyard > backup.sql

# Restore database
psql -U jnovak -h localhost wildebackyard < backup.sql
```

### PostgreSQL Commands
```bash
# Connect to database
psql -U jnovak -d wildebackyard -h localhost

# Inside psql:
\dt          # List all tables
\d tablename # Describe table structure
\q           # Quit
\conninfo    # Show connection info
```

## Common Pydantic Patterns

### Validating Request Data
```python
from pydantic import ValidationError
from .schemas import UserCreate

try:
    user_data = UserCreate(**request.data)
except ValidationError as e:
    return Response({'errors': e.errors()}, status=400)
```

### Converting Django Model to Pydantic
```python
from .schemas import UserResponse

user = User.objects.get(id=user_id)
response_data = UserResponse.model_validate(user)
return Response(response_data.model_dump())
```

### Partial Updates
```python
from .schemas import UserUpdate

update_data = UserUpdate(**request.data)
update_dict = update_data.model_dump(exclude_unset=True)
for field, value in update_dict.items():
    setattr(user, field, value)
user.save()
```

## Useful Django ORM Queries

### Basic Queries
```python
# Get all objects
User.objects.all()

# Filter objects
User.objects.filter(is_active=True)

# Get single object
User.objects.get(id=user_id)

# Count objects
User.objects.count()

# Order objects
User.objects.order_by('-created')

# Limit results
User.objects.all()[:10]
```

### Advanced Queries
```python
from django.db.models import Q, Count

# OR queries
User.objects.filter(Q(name='John') | Q(email='john@example.com'))

# Annotations
User.objects.annotate(post_count=Count('mediapost'))

# Select related (for foreign keys)
MediaPost.objects.select_related('user').all()

# Prefetch related (for many-to-many)
User.objects.prefetch_related('mediapost_set').all()
```

## Environment Variables

### Edit .env file
```bash
nano .env  # or use your preferred editor
```

### Key variables:
```bash
DB_NAME=wildebackyard
DB_USER=jnovak
DB_PASSWORD=Nashorn9450!
DB_HOST=localhost
DB_PORT=5432
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
```

## Git Workflow

### Common commands
```bash
# Check status
git status

# Create new branch
git checkout -b feature/your-feature

# Stage changes
git add .

# Commit changes
git commit -m "Description of changes"

# Push to remote
git push origin feature/your-feature

# Pull latest changes
git pull origin main
```

## Troubleshooting

### Database connection issues
```bash
# Test PostgreSQL connection
PGPASSWORD='Nashorn9450!' psql -U jnovak -d wildebackyard -h localhost -c "\conninfo"

# Check PostgreSQL service
sudo systemctl status postgresql
sudo systemctl start postgresql  # if not running
```

### Virtual environment issues
```bash
# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Migration issues
```bash
# Show migration status
python manage.py showmigrations --settings=config.settings.local

# Fake a migration (if needed)
python manage.py migrate --fake app_name migration_name --settings=config.settings.local

# Reset migrations (CAUTION: deletes data)
python manage.py migrate app_name zero --settings=config.settings.local
```

### Clear Python cache
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Performance Tips

1. **Use select_related() and prefetch_related()** for N+1 query problems
2. **Add database indexes** to frequently queried fields
3. **Use bulk operations** for multiple inserts/updates
4. **Cache frequently accessed data** with Django's caching framework
5. **Use database connection pooling** for production

## Security Reminders

- ⚠️ Never commit `.env` file
- ⚠️ Always use strong SECRET_KEY in production
- ⚠️ Set DEBUG=False in production
- ⚠️ Use HTTPS in production
- ⚠️ Keep dependencies updated: `uv pip install --upgrade -e .`
