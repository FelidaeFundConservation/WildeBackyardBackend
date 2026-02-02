# Pydantic Integration Guide

This project now includes Pydantic for data validation and serialization alongside Django ORM.

## Setup Complete

The following changes have been made:

1. **Added Pydantic packages** to `pyproject.toml`:
   - `pydantic==2.9.2`
   - `pydantic-settings==2.6.1`

2. **Configured PostgreSQL database**:
   - Database: `wildebackyard`
   - User: `jnovak`
   - Host: `localhost`
   - Port: `5432`

3. **Created environment configuration**:
   - `.env` file for local development (not committed to git)
   - `.env.example` as a template for other developers

## Using Pydantic with Django

### Example: Creating Pydantic Schemas

Create Pydantic schemas in your app directories for validation and serialization:

```python
# siteapps/users/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserResponse(UserBase):
    id: int
    date_joined: datetime
    is_active: bool

    class Config:
        from_attributes = True  # Allows Pydantic to work with Django ORM models
```

### Example: Using Pydantic in Views

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from pydantic import ValidationError
from .schemas import UserCreate, UserResponse
from .models import User

@api_view(['POST'])
def create_user(request):
    try:
        # Validate incoming data with Pydantic
        user_data = UserCreate(**request.data)

        # Create Django model instance
        user = User.objects.create_user(
            email=user_data.email,
            name=user_data.name,
            password=user_data.password
        )

        # Serialize response with Pydantic
        response_data = UserResponse.from_orm(user)
        return Response(response_data.model_dump())

    except ValidationError as e:
        return Response({'errors': e.errors()}, status=400)
```

### Example: Pydantic Settings

For configuration management, you can use `pydantic-settings`:

```python
# config/pydantic_config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    db_name: str = "wildebackyard"
    db_user: str = "jnovak"
    db_password: str
    db_host: str = "localhost"
    db_port: int = 5432

    # Django
    django_secret_key: str
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )

settings = Settings()
```

## Benefits of Using Pydantic

1. **Type Safety**: Automatic type checking and validation
2. **Data Serialization**: Easy conversion between Django models and JSON
3. **Documentation**: Auto-generated schemas for API documentation
4. **Performance**: Fast validation using Rust-based core
5. **IDE Support**: Better autocomplete and type hints

## Database Connection

To test the database connection:

```bash
source .venv/bin/activate
python manage.py dbshell --settings=config.settings.local
```

To run the development server:

```bash
source .venv/bin/activate
python manage.py runserver --settings=config.settings.local
```

## Next Steps

1. Create Pydantic schemas for your existing Django models
2. Update API views to use Pydantic for validation
3. Consider using `django-ninja` for automatic API documentation with Pydantic
4. Add Pydantic validation to serializers for stronger type safety

## Common Patterns

### Converting Django Model to Pydantic

```python
# From Django model instance
user = User.objects.get(id=1)
user_schema = UserResponse.from_orm(user)

# To dictionary
user_dict = user_schema.model_dump()

# To JSON string
user_json = user_schema.model_dump_json()
```

### Validating Request Data

```python
from pydantic import ValidationError

try:
    validated_data = UserCreate(**request_data)
except ValidationError as e:
    # e.errors() returns detailed validation errors
    print(e.errors())
```
