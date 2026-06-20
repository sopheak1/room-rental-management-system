# Testing Room Rental Mobile API

## Quick Test Commands

### 1. Login (Get Token)

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "full_name": "Sopheak"
  }
}
```

### 2. Test Protected Endpoint (Dashboard)

```bash
curl -X GET http://localhost:8080/api/v1/dashboard \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Replace `YOUR_TOKEN_HERE` with token from login response.

**Expected Response:**
```json
{
  "statistics": {
    "total_rooms": 38,
    "occupied_rooms": 35,
    "vacant_rooms": 3,
    "occupancy_rate": 92.1,
    "total_expected": 17500000,
    "total_collected": 16200000,
    "collection_rate": 92.6,
    "overdue_count": 2
  },
  "current_month": 6,
  "current_year": 2026
}
```

---

## Postman Setup

### Step 1: Create Login Request

1. **Method**: POST
2. **URL**: `http://localhost:8080/api/v1/auth/login`
3. **Headers Tab**: Add
   - Key: `Content-Type`
   - Value: `application/json`
4. **Body Tab**: 
   - Select: **raw** (not form-data)
   - Paste JSON:
   ```json
   {
     "username": "admin",
     "password": "password"
   }
   ```
5. **Click Send**
6. Copy the `access_token` from response

### Step 2: Create Protected Request

1. **Method**: GET
2. **URL**: `http://localhost:8080/api/v1/dashboard`
3. **Headers Tab**: Add
   - Key: `Authorization`
   - Value: `Bearer {paste_token_here}`
4. **Click Send**

---

## Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Wrong username/password | Use `admin` / `password` |
| 400 Bad Request | Missing JSON body | Add `Content-Type: application/json` header |
| 415 Unsupported Media Type | Wrong Content-Type | Must be `application/json` |
| Token missing | No Authorization header | Add `Authorization: Bearer {token}` |

---

## Admin Credentials

- **Username**: `admin`
- **Password**: `password`

(Reset in database if changed)

---

## All Endpoints

### Auth
- `POST /api/v1/auth/login` — Login, get token
- `POST /api/v1/auth/logout` — Logout

### Dashboard  
- `GET /api/v1/dashboard` — Summary stats

### Buildings
- `GET /api/v1/buildings` — List all
- `POST /api/v1/buildings` — Create
- `PUT /api/v1/buildings/{id}` — Update
- `DELETE /api/v1/buildings/{id}` — Delete

### Rooms
- `GET /api/v1/rooms` — List (filter: building_id, status)
- `POST /api/v1/rooms` — Create
- `PUT /api/v1/rooms/{id}` — Update
- `DELETE /api/v1/rooms/{id}` — Delete

### Tenants
- `POST /api/v1/rooms/{room_id}/tenants` — Add tenant
- `PUT /api/v1/tenants/{id}` — Update tenant
- `POST /api/v1/tenants/{id}/checkout` — Checkout

### Receipts
- `GET /api/v1/receipts` — List (filter: month, year, status)
- `POST /api/v1/receipts` — Create
- `POST /api/v1/receipts/{id}/pay` — Record payment
- `POST /api/v1/receipts/{id}/defer` — Defer to next month

### Reports
- `GET /api/v1/reports/summary` — Monthly summary
- `GET /api/v1/reports/overdue` — Overdue payments
- `GET /api/v1/reports/occupancy` — Occupancy by building

---

**All endpoints require JWT token except `/api/v1/auth/login`**
