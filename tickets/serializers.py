from rest_framework import serializers


class TicketCreateRequestSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    seat = serializers.CharField(max_length=32)


class TicketCreateResponseSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField()
