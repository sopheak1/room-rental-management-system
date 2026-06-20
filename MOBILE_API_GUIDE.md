# Room Rental Mobile REST API Guide

## Overview

This is a complete JSON-based REST API for mobile applications (Android/iOS). The API is located at `/api/v1/` and requires JWT authentication.

## Features

✅ **JWT Authentication** — Token-based auth for mobile clients
✅ **JSON Request/Response** — No HTML forms, pure API
✅ **CRUD Operations** — Buildings, Rooms, Tenants, Receipts
✅ **Payment Tracking** — Record payments, track balances
✅ **Reporting** — Summary, overdue, occupancy reports
✅ **Error Handling** — Proper HTTP status codes and error messages

---

## Getting Started

### 1. Install Dependencies

```bash
pip install PyJWT  # For JWT token generation
```

### 2. Import Postman Collection

1. Open **Postman**
2. **Import** → Select `Room-Rental-Mobile-API.postman_collection.json`
3. Set `base_url` variable to your server (default: `http://localhost:8080`)

### 3. Test Authentication

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "full_name": "Admin User"
  }
}
```

Save the `access_token` to use in other requests.

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` — Login, get token
- `POST /api/v1/auth/logout` — Logout

### Dashboard
- `GET /api/v1/dashboard` — Summary statistics

### Buildings
- `GET /api/v1/buildings` — List all
- `GET /api/v1/buildings/{id}` — Get with rooms
- `POST /api/v1/buildings` — Create
- `PUT /api/v1/buildings/{id}` — Update
- `DELETE /api/v1/buildings/{id}` — Delete

### Rooms
- `GET /api/v1/rooms` — List (filter by building_id, status)
- `GET /api/v1/rooms/{id}` — Get detail with history
- `POST /api/v1/rooms` — Create
- `PUT /api/v1/rooms/{id}` — Update
- `DELETE /api/v1/rooms/{id}` — Delete

### Tenants
- `POST /api/v1/rooms/{room_id}/tenants` — Add tenant
- `GET /api/v1/tenants/{id}` — Get tenant
- `PUT /api/v1/tenants/{id}` — Update tenant
- `POST /api/v1/tenants/{id}/checkout` — Checkout tenant

### Receipts
- `GET /api/v1/receipts` — List (filter by month, year, status)
- `GET /api/v1/receipts/{id}` — Get detail with payments
- `POST /api/v1/receipts` — Create
- `POST /api/v1/receipts/{id}/pay` — Record payment
- `POST /api/v1/receipts/{id}/defer` — Defer to next month
- `POST /api/v1/receipts/{id}/undefer` — Restore from deferred

### Utilities
- `GET /api/v1/utilities/prices` — Get current prices
- `POST /api/v1/utilities/prices` — Update price

### Reports
- `GET /api/v1/reports/summary` — Monthly payment summary
- `GET /api/v1/reports/overdue` — Overdue payments
- `GET /api/v1/reports/occupancy` — Occupancy by building

---

## Authentication

All API endpoints (except `/auth/login`) require a JWT token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer {access_token}" \
     http://localhost:8080/api/v1/rooms
```

**Token Lifespan:** 24 hours (86400 seconds)

---

## Request Examples

### Create Building
```json
POST /api/v1/buildings
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Building A",
  "address": "123 Main Street"
}
```

### Add Tenant to Room
```json
POST /api/v1/rooms/1/tenants
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "John Doe",
  "gender": "M",
  "nid": "123456789",
  "tel": "0123456789",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_tel": "0987654321",
  "num_roommates": 1,
  "contract_duration": "monthly",
  "move_in_date": "2024-06-01",
  "deposit_paid": 1000000
}
```

### Create Receipt
```json
POST /api/v1/receipts
Content-Type: application/json
Authorization: Bearer {token}

{
  "room_id": 1,
  "billing_month": 6,
  "billing_year": 2024,
  "electricity_total": 40000,
  "water_total": 70000,
  "previous_balance": 0,
  "fee": 0,
  "late_fee": 0,
  "discount": 0
}
```

### Record Payment
```json
POST /api/v1/receipts/1/pay
Content-Type: application/json
Authorization: Bearer {token}

{
  "paid_amount": 500000,
  "payment_method": "cash",
  "payment_date": "2024-06-15"
}
```

---

## Response Examples

### Successful Response (200 OK)
```json
{
  "rooms": [
    {
      "id": 1,
      "building_id": 1,
      "building_name": "Building A",
      "room_number": "101",
      "floor": 1,
      "room_type": "single",
      "price": 500000,
      "deposit_amount": 1000000,
      "status": "occupied",
      "tenant": {
        "id": 1,
        "name": "John Doe",
        "move_in_date": "2024-06-01"
      }
    }
  ]
}
```

### Created Response (201 Created)
```json
{
  "message": "Room created successfully",
  "room": {
    "id": 1,
    "building_id": 1,
    "room_number": "101",
    "price": 500000,
    "status": "available"
  }
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "Building name is required"
}
```

### Error Response (404 Not Found)
```json
{
  "error": "Not found"
}
```

### Error Response (401 Unauthorized)
```json
{
  "error": "Authorization token required"
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — Request succeeded |
| 201 | Created — Resource created |
| 400 | Bad Request — Invalid input |
| 401 | Unauthorized — Invalid/missing token |
| 404 | Not Found — Resource doesn't exist |
| 500 | Server Error |

---

## Common Queries

### Get Rooms in Building A
```bash
GET /api/v1/rooms?building_id=1
```

### Get Only Occupied Rooms
```bash
GET /api/v1/rooms?status=occupied
```

### Get Unpaid Receipts for June 2024
```bash
GET /api/v1/receipts?month=6&year=2024&status=unpaid
```

### Get Overdue Payments
```bash
GET /api/v1/reports/overdue
```

---

## Mobile App Integration Tips

### 1. Store Token Securely
```javascript
// DO NOT store in localStorage or SharedPreferences
// Use secure storage (Keychain on iOS, Keystore on Android)
// Token expires after 24 hours — refresh by re-logging in
```

### 2. Handle Token Expiration
```javascript
// If response is 401 Unauthorized:
// 1. Clear stored token
// 2. Redirect to login screen
// 3. Ask user to re-authenticate
```

### 3. Retry Logic
```javascript
// For network errors, implement exponential backoff
// Max 3-5 retries with increasing delays (1s, 2s, 4s, 8s)
```

### 4. Offline Support
```javascript
// Cache API responses locally
// Sync when connection restored
// Use unique receipt IDs to avoid duplicates
```

### 5. Error Handling
```javascript
if (response.status === 400) {
  // Bad request — validation error, show to user
  showError(response.data.error);
} else if (response.status === 401) {
  // Unauthorized — token expired, redirect to login
  redirectToLogin();
} else if (response.status === 500) {
  // Server error — retry or show generic message
  showError("Server error. Please try again.");
}
```

---

## Development vs Production

### Development (localhost:8080)
```bash
base_url = "http://localhost:8080"
# Token validation disabled for testing
# CORS enabled for local development
```

### Production
```bash
base_url = "https://your-domain.com"
# Use HTTPS only
# Validate tokens strictly
# Enable CORS only for your app domain
```

---

## Troubleshooting

### "Token is missing" Error
- Make sure to include `Authorization: Bearer {token}` header
- Token must be from `/auth/login` response
- Token expires after 24 hours

### "Invalid token" Error
- Token format must be: `Authorization: Bearer {token}`
- Not: `Authorization: {token}` (missing "Bearer")

### "Resource not found" (404)
- Verify the ID exists (list first, then use ID)
- Check building_id exists before creating rooms
- Check room exists before adding tenants

### "Cannot checkout — outstanding balances" Error
- Pay or defer outstanding receipts first
- Or set `force_checkout: true` in checkout request

---

## Next Steps

1. **Import Collection** — Use `Room-Rental-Mobile-API.postman_collection.json`
2. **Set Variables** — Configure `base_url` and `access_token`
3. **Login** — Call `/api/v1/auth/login` to get token
4. **Test Endpoints** — Try reading buildings, rooms, receipts
5. **Build Mobile UI** — Use endpoints to power your app

---

## Files

- **API Implementation** — `app/routes/api.py`
- **Postman Collection** — `Room-Rental-Mobile-API.postman_collection.json`
- **Web Routes** (for reference) — `app/routes/` (buildings, receipts, etc.)

---

**Last Updated:** 2024-06-20  
**API Version:** v1  
**Status:** Ready for mobile development
