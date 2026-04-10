from rest_framework import serializers

from events.models import Event, Place


class EventListQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)


class PlaceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ("id", "name", "city", "address")


class PlaceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ("id", "name", "city", "address", "seats_pattern")


class EventListSerializer(serializers.ModelSerializer):
    place = PlaceSummarySerializer()

    class Meta:
        model = Event
        fields = (
            "id",
            "name",
            "place",
            "event_time",
            "registration_deadline",
            "status",
            "number_of_visitors",
        )


class EventDetailSerializer(serializers.ModelSerializer):
    place = PlaceDetailSerializer()

    class Meta:
        model = Event
        fields = (
            "id",
            "name",
            "place",
            "event_time",
            "registration_deadline",
            "status",
            "number_of_visitors",
        )
