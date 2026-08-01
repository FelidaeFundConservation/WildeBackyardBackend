# iNaturalist Taxonomy Integration Guide

## Overview

This document analyzes the iNaturalist taxonomy schema and outlines the steps
to replicate a useful subset of it in the Wilde Backyard apps, along with
guidance on filtering for North American vertebrate species.

---

## 1. iNaturalist Taxonomy Schema (Key Tables)

### `taxa` (core table)

| Column | Type | Notes |
|---|---|---|
| `id` | integer PK | |
| `name` | string | Scientific name (e.g. `Anas platyrhynchos`) |
| `rank` | string | `species`, `genus`, `family`, `order`, `class`, `phylum`, `kingdom`, etc. |
| `rank_level` | integer | Numeric level: species=10, genus=20, family=30, order=40, class=50, phylum=60, kingdom=70, stateofmatter=100 |
| `ancestry` | string | Slash-delimited ancestor IDs: `1/2/7/12/` — enables tree queries |
| `parent_id` | integer | Direct parent taxon (redundant with ancestry, kept for joins) |
| `iconic_taxon_id` | integer FK → `taxa.id` | Points to the "iconic" group this taxon belongs to (see below) |
| `is_iconic` | boolean | True for the ~13 iconic top-level groups |
| `is_active` | boolean | False = deprecated/synonymised taxon |
| `observations_count` | integer | iNat observation volume |
| `listed_taxa_count` | integer | |
| `wikipedia_summary` | text | |
| `source_identifier` | string | External ID (GBIF, CoL, etc.) |
| `source_url` | string | |
| `locked` | boolean | Curator-locked subtree |
| `complete_rank` | string | If set, taxon is considered complete at this rank |

**Ancestry pattern:** `ancestry = "48460/1/2/355675/3/"` means the taxon's
ancestors (root → parent) are stored as `/`-separated IDs. Subtree queries use
`ancestry LIKE '1/2/355675/%'`.

### `taxon_names`

| Column | Type | Notes |
|---|---|---|
| `id` | integer PK | |
| `taxon_id` | integer FK | |
| `name` | string | The name itself |
| `lexicon` | string | `"Scientific Names"`, `"English"`, `"French"`, etc. |
| `is_valid` | boolean | Primary/accepted name for this lexicon |
| `position` | integer | Display order (0 = preferred) |
| `source_id` | integer | |
| `creator_id` / `updater_id` | integer | |

Common names are rows with `lexicon != "Scientific Names"`. English common
names have `lexicon = "English"`.

### `place_taxon_names` (place-scoped preferred names)

| Column | Type |
|---|---|
| `place_id` | integer FK → `places` |
| `taxon_name_id` | integer FK → `taxon_names` |
| `position` | integer |

Allows different places to prefer different common name variants.

### `conservation_statuses`

| Column | Type | Notes |
|---|---|---|
| `taxon_id` | integer FK | |
| `status` | string | `LC`, `NT`, `VU`, `EN`, `CR`, `EW`, `EX`, etc. |
| `iucn` | integer | IUCN numeric code |
| `authority` | string | `"IUCN Red List"`, `"NatureServe"`, `"Norma Oficial 059"` |
| `place_id` | integer FK | NULL = global, non-null = jurisdiction-specific |
| `geoprivacy` | string | Obscures observation location for sensitive species |

### `taxon_ranges`

| Column | Type | Notes |
|---|---|---|
| `taxon_id` | integer FK | |
| `geom` | multi_polygon | PostGIS geometry of species range |
| `range_type` | string | |
| `source_id` | integer | |

### `listed_taxa` (place × taxon checklists)

| Column | Type | Notes |
|---|---|---|
| `taxon_id` | integer FK | |
| `list_id` | integer FK | The checklist (often place-linked) |
| `place_id` | integer FK | Direct place denorm for fast filtering |
| `establishment_means` | string | `native`, `introduced`, `endemic`, etc. |
| `occurrence_status_level` | integer | Present=present, Absent=10/20 |
| `primary_listing` | boolean | Authoritative listing for that place |

**Key:** Filtering `listed_taxa WHERE place_id = <north_america_place_id>` gives
taxa that have been observed or listed in North America.

### `places`

| Column | Notes |
|---|---|
| `name` | "United States", "Canada", "Mexico", "North America", etc. |
| `ancestry` | Hierarchical — place can be scoped to continent |
| `place_geometry.geom` | PostGIS polygon — can spatial-join taxa ranges |
| `bbox_*` | Bounding box for fast pre-filter |

---

## 2. Iconic Taxa (iNaturalist's "Vertebrates" mapping)

iNaturalist uses `iconic_taxon_id` to classify every taxon under one of
~13 iconic groups. The vertebrate groups are:

| `taxa.name` | Common Group |
|---|---|
| `Mammalia` | Mammals |
| `Aves` | Birds |
| `Reptilia` | Reptiles |
| `Amphibia` | Amphibians |
| `Actinopterygii` | Ray-finned Fishes |
| `Animalia` | Other Animals (catch-all) |

**Note:** iNaturalist does NOT have a single "Vertebrata" iconic taxon.
Agnatha (lampreys), Chondrichthyes (sharks/rays), and Cephalaspidomorphi
are **not** iconic groups — they fall under `Animalia`. If "vertebrates"
means strictly the five classes above, those are well-covered. A broader
filter would need ancestry-based filtering from the `Vertebrata` node.

**Filter for vertebrates via iconic_taxon:**
```sql
SELECT t.* FROM taxa t
JOIN taxa iconic ON iconic.id = t.iconic_taxon_id
WHERE iconic.name IN ('Mammalia','Aves','Reptilia','Amphibia','Actinopterygii')
  AND t.rank = 'species'
  AND t.is_active = true;
```

---

## 3. Current Wilde Backyard Species Model

The current `SpeciesName` model in `WildeBackyardBackend/siteapps/species/` is
extremely minimal:

```python
class SpeciesName(TimeStampedModel):
    name = models.CharField("Common Name", max_length=250, unique=True)
    scientific_name = models.CharField(max_length=250, null=True, blank=True)
    active = models.BooleanField(default=True)
```

This only stores a flat list of common + scientific name pairs. There is no
taxonomy tree, no rank, no ancestry, no place association, and no iconic group.

---

## 4. Steps to Replicate iNaturalist Taxonomy in Wilde Backyard

### Step 1 — Acquire iNaturalist Open Data Export

iNaturalist publishes a free open data export at:
**https://www.inaturalist.org/pages/developers** → "Taxa CSV export"

Or use the **GBIF backbone taxonomy** (which iNaturalist publishes to):
- Download: https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c
- Format: Darwin Core Archive (CSV)
- Columns: `taxonID`, `parentNameUsageID`, `scientificName`, `taxonRank`,
  `vernacularName`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`

For iNaturalist-specific data (with `iconic_taxon`, `observations_count`):
```bash
# iNaturalist taxa CSV (updated weekly):
curl -O "https://www.inaturalist.org/taxa/export.csv"
# Columns: id, name, rank, parent_id, iconic_taxon_name, observations_count,
#          is_active, ancestry
```

### Step 2 — Extend the Django `Taxon` Model

Create a new `Taxon` model replacing or supplementing `SpeciesName`:

```python
class Taxon(TimeStampedModel):
    inat_id = models.IntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=250, db_index=True)        # scientific
    rank = models.CharField(max_length=50)                        # species/genus/...
    rank_level = models.IntegerField(null=True)
    ancestry = models.CharField(max_length=500, null=True, blank=True, db_index=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    iconic_taxon = models.ForeignKey('self', null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='iconic_members')
    is_active = models.BooleanField(default=True)
    observations_count = models.IntegerField(default=0)

class TaxonName(TimeStampedModel):
    taxon  = models.ForeignKey(Taxon, on_delete=models.CASCADE, related_name='names')
    name   = models.CharField(max_length=250, db_index=True)
    lexicon = models.CharField(max_length=100)   # "English", "Scientific Names", etc.
    is_valid = models.BooleanField(default=True)
    position = models.IntegerField(default=0)
```

Migrate `SpeciesName` → `Taxon`/`TaxonName` or keep `SpeciesName` as a
curated overlay on top of the taxonomy data.

### Step 3 — Write a Management Command to Load Taxa

```python
# siteapps/species/management/commands/load_inat_taxa.py
import csv
from django.core.management.base import BaseCommand
from siteapps.species.models import Taxon, TaxonName

VERTEBRATE_ICONIC = {'Mammalia', 'Aves', 'Reptilia', 'Amphibia', 'Actinopterygii'}

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--taxa-csv', required=True)
        parser.add_argument('--names-csv', required=True)
        parser.add_argument('--vertebrates-only', action='store_true')
        parser.add_argument('--species-only', action='store_true')

    def handle(self, *args, **options):
        # Pass 1: load taxa rows
        with open(options['taxa_csv']) as f:
            for row in csv.DictReader(f):
                iconic = row.get('iconic_taxon_name', '')
                if options['vertebrates_only'] and iconic not in VERTEBRATE_ICONIC:
                    continue
                if options['species_only'] and row['rank'] != 'species':
                    continue
                Taxon.objects.update_or_create(
                    inat_id=int(row['id']),
                    defaults={
                        'name': row['name'],
                        'rank': row['rank'],
                        'ancestry': row['ancestry'],
                        'is_active': row['is_active'] == 'true',
                        'observations_count': int(row.get('observations_count', 0)),
                    }
                )
        # Pass 2: link parents + iconic_taxon (requires all taxa loaded first)
        # Pass 3: load taxon_names CSV for common names
```

### Step 4 — Filter for North American Species

iNaturalist does **not** publish a per-place taxa CSV directly.
Use one of these approaches:

**Option A — iNaturalist API (real-time, small sets)**
```
GET https://api.inaturalist.org/v1/taxa?place_id=97394&iconic_taxa=Mammalia,Aves,Reptilia,Amphibia,Actinopterygii&per_page=500
```
`place_id=97394` = continental North America (USA + Canada + Mexico)
`place_id=1` = World

**Option B — GBIF occurrence data (bulk)**
Download a GBIF occurrence export filtered by:
- `country IN (US, CA, MX)`
- `taxonKey` in Vertebrata subtree

**Option C — Ancestry filter after full load**
Load all taxa, then filter by ancestry containing the `Vertebrata` node ID:
```python
vertebrata_id = Taxon.objects.get(name='Vertebrata').inat_id
na_species = Taxon.objects.filter(
    ancestry__contains=f'/{vertebrata_id}/',
    rank='species',
    is_active=True
)
```
Then cross-reference against a list of North American species from a
GBIF checklist or from listed_taxa via the iNat API.

**Option D — Use iNat's `listed_taxa` concept via API**
```
GET https://api.inaturalist.org/v1/taxa?place_id=97394&rank=species&per_page=500
```
Paginate through all pages, storing taxa that have observations in NA.

### Step 5 — Update the Species Suggestion System

The existing `similarity/similarity.py` `suggest_species()` function
currently works against the flat `species_speciesname` table.
After the taxonomy migration:

1. Load `TaxonName` rows with `lexicon="English"` into the suggestion index
2. Include `scientific_name` from `Taxon.name` as a secondary match
3. Expose `iconic_taxon` group and `rank_level` in the suggestion response
   so the frontend can show "Birds > Mallard (Anas platyrhynchos)"

---

## 5. Can Only North American Vertebrates Be Included?

**Yes, with caveats:**

| Filter axis | Mechanism | Feasibility |
|---|---|---|
| **Vertebrates only** | Filter on `iconic_taxon_name IN (Mammalia, Aves, Reptilia, Amphibia, Actinopterygii)` | ✅ Easy — iNat CSV includes `iconic_taxon_name` |
| **North America only** | iNat API `place_id=97394` scope, or GBIF occurrence data cross-ref | ✅ Feasible but adds complexity |
| **Both combined** | Load vertebrate iconic taxa, then cross-ref against NA checklist | ✅ Recommended approach |

**Important caveats:**
- "North America" in iNat is determined by *observations*, not native range —
  a migratory species observed passing through counts
- Marine species (sharks, whales) with ranges touching NA coastlines will be
  included even if rarely seen inland
- Fishes (`Actinopterygii`) cover both freshwater and marine species — if
  only backyard-visible species are desired, further filtering by
  rank/common-name curation is needed
- iNat place-based filtering uses `listed_taxa` which requires the iNat
  database or API — it is not in the open-data CSV export

**Recommended practical approach for Wilde Backyard:**
1. Download iNat taxa CSV (free, weekly updates)
2. Filter: `is_active=true AND rank=species AND iconic_taxon_name IN (...vertebrates...)`
3. Cross-reference against GBIF North America species checklist
   (GBIF dataset `7ddf754f-d193-4cc9-b351-99906754a03b` = Vertebrates of North America)
4. Result: ~20,000–40,000 vertebrate species with NA presence

---

## 6. Summary of Required Changes

| # | Change | App | Effort |
|---|---|---|---|
| 1 | Add `Taxon` + `TaxonName` models with ancestry, rank, iconic_taxon | Backend | Medium |
| 2 | Migration from flat `SpeciesName` to `Taxon`/`TaxonName` | Backend | Medium |
| 3 | Management command `load_inat_taxa` to import CSV | Backend | Medium |
| 4 | Update `serialize_post()` to return full taxonomy context | Backend | Low |
| 5 | Update similarity suggestion to use `TaxonName` table | Web | Low |
| 6 | Update species suggest API `/species/api/suggest/` | Web | Low |
| 7 | Update Flutter app species list fetch/cache | Flutter | Low |
| 8 | Optional: add `ConservationStatus` model | Backend | Low |
| 9 | Optional: add PostGIS `taxon_range` for range-map display | Backend | High |
