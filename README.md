# Social-Networking-Platform

A RESTful API built with Django Rest Framework for a social networking application, featuring user authentication, friend requests, user activities, and blocking functionalities.

## Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [API Documentation](#api-documentation)
- [Design Choices](#design-choices)

## Features

- User registration and authentication
- Sending and accepting friend requests
- Viewing friend lists and pending requests
- Blocking and unblocking users
- Logging user activities

## Technologies Used

- Django
- Django Rest Framework
- PostgreSQL
- Django Simple JWT for authentication
- Python 3.x
- Redis

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/social-networking-api.git
   cd social-networking-api/social_network

2. **Create a virtual environment:**
    python -m venv venv
    source venv/bin/activate
 
3. **Install dependencies:**
    pip install -r requirements.txt

4. **Set up the database:**
    - Update your database settings in settings.py.
    - Run migrations:
        python manage.py migrate
      
5. **For docker**
    - Make changes in docker-compose file for database

## API Documentation

### User Signup
- **Endpoint:** `/signup/`
- **Method:** `POST`
- **Body:**
  ```json
  {
    "email": "user@example.com",
    "first_name": "First",
    "last_name": "Last",
    "password": "password123"
  }

### User Login
- **Endpoint:** `/login/`
- **Method:** `POST`
- **Body:**
  ```json
  {
  "email": "user@example.com",
  "password": "password123"
  }

### Search Users
- **Endpoint:** `/search/`
- **Method:** `GET`
- **Query Parameters:** `query=<search_term>`

### Send Friend Request
- **Endpoint:** `/friend-request/send/`
- **Method:** `POST`
- **Body:**
  ```json
  {
  "to_user_id": 1
  }

### Accept Friend Request
- **Endpoint:** `/friend-request/accept/`
- **Method:** `PUT`
- **Body:**
  ```json
  {
  "request_id": 1
  }

### Reject Friend Request
- **Endpoint:** `/friend-request/reject/`
- **Method:** `POST`
- **Body:**
  ```json
  {
  "request_id": 1
}

### Friend List
- **Endpoint:** `/friends-list/`
- **Method:** `GET`

### Pending Friend Request List
- **Endpoint:** `/friend-requests/pending/`
- **Method:** `GET`

### Block User
- **Endpoint:** `/block-user/`
- **Method:** `POST`
- **Body:**
  ```json
  {
  "blocked_user_id": 1
  }

### Unblock User
- **Endpoint:** `/unblock-user/`
- **Method:** `DELETE`
- **Body:**
  ```json
  {
  "blocked_user_id": 1
  }

### User Activity
- **Endpoint:** `/user-activity/`
- **Method:** `GET`

### Design Choices
- Custom User Model: Used CustomUser model to handle user authentication with email instead of username.
- Friendship Management: Used a Friendship model to manage relationships between users, allowing statuses like pending, accepted, and rejected.
- User Activity Logging: Created a UserActivity model to log significant user actions for tracking and auditing.
- Blocking Mechanism: Implemented blocking functionality to prevent users from interacting with blocked users.
- Caching: Used caching for friend lists and pending requests to improve performance.

