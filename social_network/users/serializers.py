from rest_framework import serializers
from .models import CustomUser, UserActivity


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email']

class UserSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_first_name(self, value):
        if not value:
            raise serializers.ValidationError("First name is required")
        return value

    def validate_last_name(self, value):
        if not value:
            raise serializers.ValidationError("Last name is required")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            password=validated_data['password']
        )
        return user

class UserActivitySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserActivity
        fields = ['user_email', 'action', 'timestamp']