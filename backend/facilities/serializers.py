from rest_framework import serializers


class FacilitySerializer(serializers.Serializer):
    """Serializer for a healthcare facility coming from Overpass."""

    osm_id = serializers.CharField()
    name = serializers.CharField(allow_blank=True, required=False)
    facility_type = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    phone = serializers.CharField(allow_blank=True, required=False)
    is_24_7 = serializers.BooleanField(required=False)
    is_emergency = serializers.BooleanField(required=False)
    ownership = serializers.CharField(allow_blank=True, required=False)
    lat = serializers.FloatField()
    lon = serializers.FloatField()

