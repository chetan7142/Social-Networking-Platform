from django.db.models import Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.postgres.search import SearchVector
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

from .models import Friendship, CustomUser, BlockedUser, UserActivity
from .serializers import UserSerializer, UserSignupSerializer, UserActivitySerializer
from .throttle import FriendRequestThrottle


class UserSignupView(generics.CreateAPIView):
    serializer_class = UserSignupSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "body": {
                    "status": status.HTTP_201_CREATED,
                    "message": "User created successfully",
                    "error": ""
                }
            })
        return Response({
            "body": {
                "status": status.HTTP_400_BAD_REQUEST,
                "error": serializer.errors
            }
        })


class UserLoginView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        user = CustomUser.objects.filter(email__iexact=email).first()
        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response({
                "body": {
                    "status": status.HTTP_200_OK,
                    "message": "User logged in successfully",
                    "token": {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    "error": ""
                }
            })
        return Response({
            "body": {
                "status": status.HTTP_401_UNAUTHORIZED,
                "error": "Invalid credentials"
            }
        })


class UserSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        query = self.request.query_params.get('query', '')
        user = self.request.user

        if not query:
            return CustomUser.objects.none()

        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')

        blocked_user_ids = {blocker_id for blocker_id, blocked_id in blocked_users} | {blocked_id for
                                                                                       blocker_id, blocked_id in
                                                                                       blocked_users}

        queryset = CustomUser.objects.exclude(id__in=blocked_user_ids)

        if '@' in query:
            return queryset.filter(email__iexact=query)

        return queryset.annotate(search=SearchVector('first_name', 'last_name')).filter(
            Q(search=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).order_by('id')


class SendFriendRequestView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [FriendRequestThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from_user = request.user
        to_user_id = request.data.get('to_user_id')

        try:

            to_user = CustomUser.objects.prefetch_related('friendships_sent', 'friendships_received').get(id=to_user_id)
        except CustomUser.DoesNotExist:
            return Response({"message": "Recipient user does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if BlockedUser.objects.filter(blocker=from_user, blocked=to_user).exists() or \
                BlockedUser.objects.filter(blocker=to_user, blocked=from_user).exists():
            return Response({"message": "Cannot send a friend request to this user."}, status=status.HTTP_403_FORBIDDEN)


        cooldown_period = timedelta(hours=24)
        rejected_request = Friendship.objects.filter(
            from_user=from_user, to_user=to_user, status='rejected'
        ).order_by('-updated_at').first()
        if rejected_request and (timezone.now() - rejected_request.updated_at) < cooldown_period:
            remaining_time = cooldown_period - (timezone.now() - rejected_request.updated_at)
            return Response(
                {
                    "message": f"Cannot send another request for {remaining_time.seconds // 3600} hours and {remaining_time.seconds % 3600 // 60} minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        existing_request = Friendship.objects.filter(from_user=from_user, to_user=to_user).first()
        if existing_request:
            if existing_request.status == 'pending':
                return Response({"message": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)
            elif existing_request.status == 'accepted':
                return Response({"message": "You are already friends."}, status=status.HTTP_400_BAD_REQUEST)

        Friendship.objects.create(from_user=from_user, to_user=to_user, status='pending')

        UserActivity.objects.create(
            user=from_user,
            action=f"Sent a friend request to {to_user.email}"
        )

        return Response({"message": "Friend request sent."}, status=status.HTTP_201_CREATED)


class AcceptFriendRequestView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        from_user_id = request.data.get('request_id')
        to_user_id = request.user.id
        try:
            friendship = Friendship.objects.select_related('from_user', 'to_user').get(
                from_user_id=from_user_id, to_user_id=to_user_id, status='pending'
            )
        except Friendship.DoesNotExist:
            return Response({"error": "Friend request not found"}, status=status.HTTP_404_NOT_FOUND)

        if friendship.to_user_id != to_user_id:
            return Response({"error": "You are not authorized to accept this request"},
                            status=status.HTTP_403_FORBIDDEN)

        friendship.status = 'accepted'
        friendship.save()

        UserActivity.objects.create(
            user=request.user,
            action=f"Accepted friend request from {friendship.from_user.email}"
        )

        UserActivity.objects.create(
            user=friendship.from_user,
            action=f"{request.user.email} accepted your friend request"
        )

        return Response({"message": "Friend request accepted"}, status=status.HTTP_200_OK)


class RejectFriendRequestView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user.id
        request_id = request.data.get('request_id')

        friendship = Friendship.objects.select_related('from_user', 'to_user').filter(
            from_user_id=request_id, to_user_id=user, status='pending'
        ).first()

        if not friendship:
            return Response({"message": "Friend request not found or not sent to you"},
                            status=status.HTTP_400_BAD_REQUEST)

        friendship.status = 'rejected'
        friendship.updated_at = timezone.now()
        friendship.save()

        UserActivity.objects.create(
            user=request.user,
            action=f"Rejected friend request from {friendship.from_user.email}"
        )

        UserActivity.objects.create(
            user=friendship.from_user,
            action=f"{request.user.email} rejected your friend request"
        )

        return Response({"message": "Friend request rejected. Sender cannot resend for 24 hours."},
                        status=status.HTTP_200_OK)


class FriendListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        user = self.request.user

        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')

        blocked_user_ids = {blocker_id for blocker_id, blocked_id in blocked_users} | {blocked_id for
                                                                                       blocker_id, blocked_id in
                                                                                       blocked_users}

        friends_from_user = Friendship.objects.filter(from_user=user, status='accepted').exclude(
            to_user_id__in=blocked_user_ids
        ).values_list('to_user', flat=True)

        friends_to_user = Friendship.objects.filter(to_user=user, status='accepted').exclude(
            from_user_id__in=blocked_user_ids
        ).values_list('from_user', flat=True)

        friend_ids = list(set(friends_from_user) | set(friends_to_user))

        return CustomUser.objects.filter(id__in=friend_ids).order_by('id').prefetch_related('friendships_sent',
                                                                                            'friendships_received')


class PendingFriendRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        user = self.request.user

        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')

        blocked_user_ids = {blocker_id for blocker_id, blocked_id in blocked_users} | {blocked_id for
                                                                                       blocker_id, blocked_id in
                                                                                       blocked_users}

        pending_requests = Friendship.objects.select_related('from_user').filter(
            to_user_id=user, status='pending'
        ).exclude(from_user_id__in=blocked_user_ids).order_by('created_at')

        return CustomUser.objects.filter(
            id__in=pending_requests.values_list('from_user_id', flat=True)).prefetch_related('friendships_sent',
                                                                                             'friendships_received')


class BlockUserView(generics.CreateAPIView):
    """
    Handles blocking a user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Blocks a user from interacting with the authenticated user.
        """
        blocker = request.user
        blocked_user_id = request.data.get('blocked_user_id')
        try:
            blocked_user = CustomUser.objects.get(id=blocked_user_id)
        except CustomUser.DoesNotExist:
            return Response({"message": "User to block not found"}, status=status.HTTP_404_NOT_FOUND)

        if BlockedUser.objects.filter(blocker=blocker, blocked=blocked_user).exists():
            return Response({"message": "User already blocked"}, status=status.HTTP_400_BAD_REQUEST)

        BlockedUser.objects.create(blocker=blocker, blocked=blocked_user)

        UserActivity.objects.create(
            user=blocker,
            action=f"Blocked user {blocked_user.email}"
        )

        return Response({"message": "User blocked successfully"}, status=status.HTTP_201_CREATED)


class UnblockUserView(generics.DestroyAPIView):
    """
    Handles unblocking a user.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        blocker = request.user
        blocked_user_id = request.data.get('blocked_user_id')
        try:
            blocked_user = CustomUser.objects.get(id=blocked_user_id)
        except CustomUser.DoesNotExist:
            return Response({"message": "User to unblock not found"}, status=status.HTTP_404_NOT_FOUND)

        blocked_user_entry = BlockedUser.objects.filter(blocker=blocker, blocked=blocked_user).first()
        if not blocked_user_entry:
            return Response({"message": "User not blocked"}, status=status.HTTP_400_BAD_REQUEST)

        blocked_user_entry.delete()

        UserActivity.objects.create(
            user=blocker,
            action=f"Unblocked user {blocked_user.email}"
        )

        return Response({"message": "User unblocked successfully"}, status=status.HTTP_200_OK)


class UserActivityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserActivitySerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return UserActivity.objects.select_related('user').filter(user=self.request.user).order_by('-timestamp')
