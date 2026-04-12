"""Django models for habitat classification and GeoNames data."""

from django.contrib.gis.db import models


class Admin1Code(models.Model):
    """
    Administrative division codes (states/provinces).

    Example: US.CA = California, CA.ON = Ontario
    """

    code = models.CharField(max_length=20, primary_key=True, help_text="Country.AdminCode (e.g., US.CA)")
    name = models.CharField(max_length=200, help_text="Full name of state/province")
    name_ascii = models.CharField(max_length=200, help_text="ASCII version of name")
    geonameid = models.IntegerField(null=True, blank=True, help_text="GeoNames ID for this admin division")

    class Meta:
        db_table = "admin1_codes"
        verbose_name = "Admin1 Code"
        verbose_name_plural = "Admin1 Codes"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.name}"


class FeatureCode(models.Model):
    """
    GeoNames feature classification codes.

    Examples: PPL = populated place, PPLA = capital of admin1 division
    """

    code = models.CharField(max_length=10, primary_key=True, help_text="Feature code (e.g., PPL, ADM1)")
    name = models.CharField(max_length=200, help_text="Short name of feature type")
    description = models.TextField(blank=True, help_text="Detailed description of feature type")

    class Meta:
        db_table = "feature_codes"
        verbose_name = "Feature Code"
        verbose_name_plural = "Feature Codes"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.name}"


class GeoName(models.Model):
    """
    GeoNames geographical database entries for North America.

    Contains cities, towns, states, parks, mountains, lakes, and other
    geographic features with coordinates and metadata.
    """

    geonameid = models.IntegerField(primary_key=True, help_text="Unique GeoNames identifier")
    name = models.CharField(max_length=200, help_text="Name in UTF-8 format")
    asciiname = models.CharField(max_length=200, help_text="Name in ASCII characters")
    alternatenames = models.CharField(max_length=10000, blank=True, help_text="Comma-separated alternate names")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, help_text="Latitude in decimal degrees")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, help_text="Longitude in decimal degrees")
    fclass = models.CharField(max_length=1, help_text="Feature class (A=admin, P=populated place, H=water, etc)")
    fcode = models.CharField(max_length=10, help_text="Feature code (detailed classification)")
    country = models.CharField(max_length=2, help_text="ISO-3166 2-letter country code")
    cc2 = models.CharField(max_length=200, blank=True, help_text="Alternate country codes")
    admin1 = models.CharField(max_length=20, blank=True, help_text="State/province code (FIPS)")
    admin2 = models.CharField(max_length=80, blank=True, help_text="County/second-level admin code")
    admin3 = models.CharField(max_length=20, blank=True, help_text="Third-level admin code")
    admin4 = models.CharField(max_length=20, blank=True, help_text="Fourth-level admin code")
    population = models.BigIntegerField(null=True, blank=True, help_text="Population (0 if not applicable)")
    elevation = models.IntegerField(null=True, blank=True, help_text="Elevation in meters")
    gtopo30 = models.IntegerField(null=True, blank=True, help_text="Average elevation from GTOPO30")
    timezone = models.CharField(max_length=40, blank=True, help_text="Timezone (e.g., America/Los_Angeles)")
    moddate = models.DateField(help_text="Date of last modification")
    geom = models.PointField(srid=4326, help_text="PostGIS Point geometry (WGS84)")

    class Meta:
        db_table = "geonames"
        verbose_name = "GeoName"
        verbose_name_plural = "GeoNames"
        ordering = ["-population", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country"]),
            models.Index(fields=["admin1"]),
            models.Index(fields=["fcode"]),
            models.Index(fields=["-population"]),
            models.Index(fields=["country", "admin1"]),
            models.Index(fields=["country", "fcode"]),
        ]

    def __str__(self):
        parts = [self.name]
        if self.admin1:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)

    @property
    def display_name(self):
        """Return a human-readable display name with location context."""
        parts = [self.name]
        if self.admin1 and self.country:
            try:
                admin_code = Admin1Code.objects.get(code=f"{self.country}.{self.admin1}")
                parts.append(admin_code.name)
            except Admin1Code.DoesNotExist:
                parts.append(self.admin1)
        elif self.admin1:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)


class PostalCode(models.Model):
    """
    North American postal codes (US ZIP codes and Canadian postal codes).

    Provides centroid coordinates for each postal code for geocoding.
    Data source: GeoNames postal code database.
    """

    country = models.CharField(max_length=2, help_text="ISO-3166 2-letter country code (US or CA)")
    postal_code = models.CharField(max_length=20, help_text="Postal code (ZIP for US, postal code for CA)")
    place_name = models.CharField(max_length=180, help_text="Place name associated with postal code")
    admin1_name = models.CharField(max_length=100, blank=True, help_text="State/province name")
    admin1_code = models.CharField(max_length=20, blank=True, help_text="State/province code")
    admin2_name = models.CharField(max_length=100, blank=True, help_text="County/district name")
    admin2_code = models.CharField(max_length=20, blank=True, help_text="County/district code")
    admin3_name = models.CharField(max_length=100, blank=True, help_text="Community name")
    admin3_code = models.CharField(max_length=20, blank=True, help_text="Community code")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, help_text="Latitude of centroid")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, help_text="Longitude of centroid")
    accuracy = models.SmallIntegerField(
        null=True, blank=True, help_text="Accuracy of coordinates (1-6, lower is better)"
    )
    geom = models.PointField(srid=4326, help_text="PostGIS Point geometry for centroid (WGS84)")
    boundary = models.MultiPolygonField(
        srid=4326, null=True, blank=True, help_text="PostGIS MultiPolygon for ZIP/postal code boundaries"
    )

    class Meta:
        db_table = "postal_codes"
        verbose_name = "Postal Code"
        verbose_name_plural = "Postal Codes"
        ordering = ["country", "postal_code"]
        indexes = [
            models.Index(fields=["country", "postal_code"]),
            models.Index(fields=["postal_code"]),
            models.Index(fields=["country", "admin1_code"]),
            models.Index(fields=["place_name"]),
        ]
        # Note: No unique constraint - some postal codes serve multiple places

    def __str__(self):
        return f"{self.postal_code}, {self.place_name}, {self.admin1_code} {self.country}"

    @property
    def display_name(self):
        """Return formatted display name."""
        parts = [self.postal_code]
        if self.place_name:
            parts.append(self.place_name)
        if self.admin1_name:
            parts.append(self.admin1_name)
        elif self.admin1_code:
            parts.append(self.admin1_code)
        return ", ".join(parts)
