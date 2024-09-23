from django.urls import path

from .models import UserActivity
from .views import UserSignupView, UserLoginView, UserSearchView, SendFriendRequestView, BlockUserView, UnblockUserView, \
    AcceptFriendRequestView, RejectFriendRequestView, FriendListView, PendingFriendRequestsView, UserActivityView

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='signup'), # Signup
    path('login/', UserLoginView.as_view(), name='login'), # Login
    path('search/', UserSearchView.as_view(), name='user-search'),  # Search users by email or name
    path('friend-request/send/', SendFriendRequestView.as_view(), name='send-friend-request'),  # Send a friend request
    path('friend-request/accept/', AcceptFriendRequestView.as_view(), name='accept-friend-request'),  # Accept a friend request
    path('friend-request/reject/', RejectFriendRequestView.as_view(), name='reject-friend-request'),  # Reject a friend request
    path('friends-list/', FriendListView.as_view(), name='friends-list'),  # List friends
    path('friend-requests/pending/', PendingFriendRequestsView.as_view(), name='pending-friend-requests'),  # List pending friend requests
    path('block-user/', BlockUserView.as_view(), name='block-user'),  # Block a user
    path('unblock-user/', UnblockUserView.as_view(), name='unblock-user'),  # Unblock a user
    path('user-activity/', UserActivityView.as_view(), name='user-activity'), # User activity log
]
