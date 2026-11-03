from rest_framework import serializers


class FacilitySerializer(serializers.Serializer):
    """Serializer for a normalized healthcare facility (healthsites.io or Overpass)."""

    osm_id = serializers.CharField()
    name = serializers.CharField(allow_blank=True, required=False)
    facility_type = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    phone = serializers.CharField(allow_blank=True, required=False)
    website = serializers.CharField(allow_blank=True, required=False)
    email = serializers.CharField(allow_blank=True, required=False)
    is_24_7 = serializers.BooleanField(required=False)
    is_emergency = serializers.BooleanField(required=False)
    # "yes", "limited", "no", or "" when unknown
    wheelchair = serializers.CharField(allow_blank=True, required=False)
    ownership = serializers.CharField(allow_blank=True, required=False)
    # Kilometres from the visitor / city centre; null when no reference point is known.
    distance_km = serializers.FloatField(allow_null=True, required=False)
    lat = serializers.FloatField()
    lon = serializers.FloatField()

