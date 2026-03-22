# Agricyle Backend (Django REST API)

Backend API for Agricyle — a marketplace connecting farmers (waste/raw material suppliers) with processors. Built with Django + Django REST Framework + JWT authentication. Supports waste listings with image uploads.

---

## Features

- Custom User model with roles: `FARMER`, `PROCESSOR`, `ADMIN`
- JWT Authentication (SimpleJWT)
  - Register
  - Login (access + refresh tokens)
  - Refresh access token
- Waste Listings
  - List + filter
  - Create (FARMER only)
  - Retrieve / update / delete (owner only)
- Listing Images
  - Upload images (FARMER + owner)
  - Delete images (FARMER + owner)
  - Set primary image (FARMER + owner)
- CORS enabled for frontend integration

---

## Tech Stack

- Python 3.12+
- Django 6.0.2
- Django REST Framework
- djangorestframework-simplejwt
- django-cors-headers
- SQLite (dev)

---

## Project Structure

config/ # Project settings + root urls
accounts/ # Custom User + auth endpoints
listings/ # Waste listings + listing images
orders/ # Orders (in progress)
media/ # Uploaded files (dev only)


---
