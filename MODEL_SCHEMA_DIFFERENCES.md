# Model Schema Differences Report
**WildeBackyardBackend vs WildeBackyardWeb**

Generated: January 28, 2026

---

## Executive Summary

This document outlines all schema differences between the Backend and Web Django model implementations across both projects. The analysis covers models in the `species`, `socialmedia`, `users`, `mapbox`, and `home` apps.

### Key Findings:
- **Species models**: Identical across both projects ✅
- **SocialMedia models**: Identical across both projects ✅
- **Users models**: Significant differences found ⚠️
- **Mapbox models**: Both empty (no models defined) ✅
- **Home models**: Only exists in Web project ℹ️

---

## Detailed Analysis by App

### 1. Species App Models

#### Backend: `/siteapps/species/models.py`
#### Web: `/siteapps/species/models.py`

**Status**: ✅ **IDENTICAL**

Both projects contain the same `SpeciesName` model with identical fields:

**Model**: `SpeciesName`
- Inherits from: `TimeStampedModel`
- Fields:
  - `name`: CharField (max_length=250, unique=True)
  - `scientific_name`: CharField (max_length=250, null=True, blank=True)
  - `active`: BooleanField (default=True)
- Meta:
  - ordering: `("name", "-created")`
  - verbose_name_plural: "Species List"

---

### 2. SocialMedia App Models

#### Backend: `/siteapps/socialmedia/models.py`
#### Web: `/siteapps/socialmedia/models.py`

**Status**: ✅ **IDENTICAL**

Both projects contain identical implementations of all three models:

#### **Model 1**: `Media`
- Inherits from: `TimeStampedModel`
- Fields:
  - `id`: UUIDField (primary_key=True, default=uuid.uuid4)
  - `is_video`: BooleanField (default=False)
  - `file_cloud_path`: CharField (max_length=250)
  - `content_hash`: CharField (max_length=64)
  - `uploaded_by`: ForeignKey (User, on_delete=SET_NULL, null=True)

#### **Model 2**: `TextComment`
- Inherits from: `TimeStampedModel`
- Fields:
  - `id`: UUIDField (primary_key=True, default=uuid.uuid4)
  - `created_by`: ForeignKey (User, on_delete=SET_NULL, null=True)
  - `text_content`: TextField (max_length=4000, null=True)
  - `upvoted_by`: ManyToManyField (User, blank=True)

#### **Model 3**: `MediaPost`
- Inherits from: `TextComment`
- Fields (in addition to inherited fields):
  - `replies`: ManyToManyField (TextComment, blank=True)
  - `title`: TextField (max_length=80)
  - `media`: ForeignKey (Media, on_delete=SET_NULL, null=True)
  - `accuracy_ring_radius_meters`: IntegerField (null=True)
  - `encounter_datetime`: DateTimeField
  - `geoprivacy`: CharField (max_length=16, with choices)
  - `species`: ForeignKey (SpeciesName, on_delete=SET_NULL, null=True, blank=True)
  - **Public location fields:**
    - `public_location_latitude`: FloatField (null=True)
    - `public_location_longitude`: FloatField (null=True)
    - `obfuscation_range_kilometers`: FloatField (null=True)
    - `obfuscation_box_corner_[1-4]_latitude/longitude`: FloatField (null=True) × 8 fields
  - **Geocoded location info:**
    - `geocoded_location_locality`: CharField (max_length=64, null=True)
    - `geocoded_location_state`: CharField (max_length=64, null=True)
    - `geocoded_location_country`: CharField (max_length=64, null=True)
    - `geocoded_location_zip_code`: CharField (max_length=64, null=True)
  - **Camera metadata:**
    - `camera_model`: CharField (max_length=64, null=True)
    - `camera_deployment_date`: CharField (max_length=32, null=True)
    - `camera_timestamp_offset_error_details`: CharField (max_length=512, null=True)
    - `habitat_type`: CharField (max_length=64, null=True)
  - **Private location fields:**
    - `true_location_latitude`: FloatField (null=True)
    - `true_location_longitude`: FloatField (null=True)
    - `private_location_latitude`: FloatField (null=True)
    - `private_location_longitude`: FloatField (null=True)

#### **Model 4**: `InappropriateContentReport`
- Inherits from: `TimeStampedModel`
- Fields:
  - `id`: UUIDField (primary_key=True, default=uuid.uuid4)
  - `reported_by`: ForeignKey (User, on_delete=SET_NULL, null=True)
  - `reported_user`: ForeignKey (User, on_delete=SET_NULL, null=True)
  - `reported_comment`: ForeignKey (TextComment, on_delete=SET_NULL, null=True, blank=True)
  - `reported_post`: ForeignKey (MediaPost, on_delete=SET_NULL, null=True, blank=True)
  - `resolved`: BooleanField (default=False)
  - `warning_notes`: CharField (max_length=800, default="")

---

### 3. Users App Models

#### Backend: `/siteapps/users/models.py`
#### Web: `/siteapps/users/models.py`

**Status**: ⚠️ **SIGNIFICANT DIFFERENCES**

This is the primary area where schema differences exist between the two projects.

#### **Model 1**: `User`

**Common Fields** (Present in Both):
- Inherits from: `AbstractUser`, `TimeStampedModel`
- `id`: UUIDField (primary_key=True, default=uuid.uuid4)
- `username`: None (removed from AbstractUser)
- `email`: EmailField (unique=True) - used as USERNAME_FIELD
- `name`: CharField (max_length=255) with random name generator
- `first_name`: None (removed)
- `last_name`: None (removed)
- USERNAME_FIELD: "email"
- REQUIRED_FIELDS: ["name"]

**Backend-Only Fields**:
1. **`warnings`**: IntegerField (default=0)
   - Purpose: Track number of warnings user has received
   - Used for moderation/content policy enforcement

2. **`history`**: HistoricalRecords()
   - Purpose: Track model instance changes over time
   - Requires: `simple_history` package
   - Creates shadow table for audit trail

3. **Random name function**: `generate_random_name()`
   - Returns: `"Backyarder" + 6_random_digits`

**Web-Only Fields**:
1. **`bio`**: CharField (max_length=10000, default="")
   - Purpose: User profile biography/description
   - Not present in Backend

2. **`objects`**: UserManager (custom manager)
   - Custom manager implementation with `create_user` and `create_superuser` methods
   - More explicit user creation logic

3. **Random name function**: `generate_random_name()`
   - Returns: `"User" + 6_random_digits`

4. **Method**: `has_eligible_work(min)`
   - Checks if user has writings with word_count >= 500
   - Related to a `writing` relation not defined in this model
   - **Note**: This appears to be legacy code from another project

**Web-Only Meta Configuration**:
- Explicit `ordering`: Not defined in Backend
- Custom Meta class configuration

#### **Model 2**: `BannedEmail`

**Backend Only**: ✅
- Inherits from: `TimeStampedModel`
- Fields:
  - `id`: UUIDField (primary_key=True, default=uuid.uuid4)
  - `email`: EmailField (unique=True)
  - `ban_reason`: CharField (max_length=800, default="")
- Purpose: Track banned emails to prevent account recreation

**Web**: ❌ Not present

---

### 4. Mapbox App Models

#### Backend: `/siteapps/mapbox/models.py`
#### Web: `/siteapps/mapbox/models.py`

**Status**: ✅ **IDENTICAL** (Both Empty)

Both files contain only the default Django comment with no models defined.

---

### 5. Home App Models

#### Backend: ❌ App does not exist
#### Web: `/siteapps/home/models.py`

**Status**: ℹ️ **Web Only**

File exists but contains no model definitions (only default Django comment).

---

## Schema Differences Summary Table

| App | Model | Backend | Web | Differences |
|-----|-------|---------|-----|-------------|
| **species** | SpeciesName | ✅ | ✅ | None - Identical |
| **socialmedia** | Media | ✅ | ✅ | None - Identical |
| **socialmedia** | TextComment | ✅ | ✅ | None - Identical |
| **socialmedia** | MediaPost | ✅ | ✅ | None - Identical |
| **socialmedia** | InappropriateContentReport | ✅ | ✅ | None - Identical |
| **users** | User | ✅ | ✅ | **YES - See details above** |
| **users** | BannedEmail | ✅ | ❌ | **Backend only** |
| **mapbox** | (any) | ❌ | ❌ | None - Both empty |
| **home** | (any) | N/A | ❌ | Web has app but no models |

---

## Critical Differences Analysis

### 1. User Model Divergence ⚠️

The `User` model differences indicate the two projects may serve different purposes:

**Backend appears to be**:
- API/service focused
- Moderation-centric (warnings, banned emails)
- Audit-trail focused (historical records)
- No user profile features

**Web appears to be**:
- User-facing application
- Profile-centric (bio field)
- May have content creation features (has_eligible_work method suggests writing/content)
- No moderation features built into User model

### 2. BannedEmail Model Missing in Web ⚠️

The Backend has email banning functionality that doesn't exist in Web. This could mean:
- Web doesn't handle user banning
- Web relies on Backend API for ban checks
- Potential security gap if Web allows direct user registration

### 3. User Model Import Differences

**Backend**:
```python
import uuid
# Uses uuid.uuid4 in default parameter
```

**Web**:
```python
from uuid import uuid4
# Uses uuid4 directly in default parameter
```

While functionally identical, this shows different coding conventions between projects.

### 4. Random Name Generation Difference

- **Backend**: `"Backyarder" + digits`
- **Web**: `"User" + digits`

This could cause confusion if users migrate between systems or if data is shared.

---

## Recommendations

### 1. **User Model Synchronization** (Priority: HIGH)
- Decide on canonical User schema
- Either:
  - Add `warnings` and `history` to Web if moderation needed there
  - Add `bio` to Backend if profiles needed there
  - Keep separate but document the divergence clearly

### 2. **BannedEmail Handling** (Priority: HIGH)
- If Web handles user registration:
  - Add BannedEmail model to Web
  - OR ensure Web checks Backend API for banned emails
- Document the ban enforcement strategy

### 3. **Remove Legacy Code** (Priority: MEDIUM)
- The `has_eligible_work()` method in Web's User model appears to be from a different project
- Should be removed unless there's actual `writing` relationship

### 4. **Standardize Conventions** (Priority: LOW)
- Use consistent import styles (`uuid.uuid4` vs `uuid4`)
- Use consistent random name prefixes or make them configurable
- Align Meta class definitions

### 5. **Custom Manager Consistency** (Priority: MEDIUM)
- Web has explicit UserManager, Backend does not
- Consider adding UserManager to Backend for consistency
- OR ensure both approaches handle user creation identically

### 6. **Documentation** (Priority: HIGH)
- Document why projects have different User schemas
- Create data migration strategy if schemas need to align
- Document which project is source of truth for shared models

---

## Migration Considerations

If you need to synchronize schemas:

### To add Backend features to Web:
```python
# Add to Web's User model:
warnings = models.IntegerField(default=0)
history = HistoricalRecords()

# Create BannedEmail model in Web
```

### To add Web features to Backend:
```python
# Add to Backend's User model:
bio = models.CharField("Bio", max_length=10000, default="")
objects = UserManager()
```

### Django Migrations Required:
- Run `makemigrations` after any schema changes
- Test migrations in development first
- Plan for data migration if existing users exist
- Consider backwards compatibility

---

## Notes

1. **TimeStampedModel**: All models use `model_utils.models.TimeStampedModel` which automatically adds `created` and `modified` timestamp fields to all models.

2. **UUID Primary Keys**: Both projects consistently use UUID for primary keys, which is good for distributed systems and avoids sequential ID enumeration attacks.

3. **Historical Records**: Only Backend uses `simple_history.HistoricalRecords`, meaning only Backend tracks model change history.

4. **No models in mapbox app**: Both projects have empty mapbox/models.py files, suggesting mapbox functionality might be handled elsewhere (views, services, or external API calls).

---

## Appendix: Field-by-Field User Model Comparison

| Field/Feature | Backend | Web | Type Match | Notes |
|---------------|---------|-----|------------|-------|
| id | ✅ | ✅ | ✅ | UUIDField |
| email | ✅ | ✅ | ✅ | EmailField, unique |
| name | ✅ | ✅ | ✅ | CharField(255) |
| warnings | ✅ | ❌ | N/A | IntegerField |
| bio | ❌ | ✅ | N/A | CharField(10000) |
| history | ✅ | ❌ | N/A | HistoricalRecords |
| objects | Default | Custom | ⚠️ | Web has UserManager |
| has_eligible_work() | ❌ | ✅ | N/A | Method (likely legacy) |
| Random name prefix | "Backyarder" | "User" | ⚠️ | Different conventions |

---

*End of Report*
