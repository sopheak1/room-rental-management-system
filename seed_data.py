#!/usr/bin/env python3
"""
Seed database with comprehensive test data for room-rental-management-system.

Usage:
  python seed_data.py                # Seed with default data
  python seed_data.py --clear        # Clear all data first
"""

import sys
from datetime import datetime, date, timedelta
from app import create_app, db
from app.models import (
    User, Building, Room, Tenant, TenantHistory,
    UtilityPrice, UtilityUsage, Receipt, PaymentLog
)


def clear_all_data():
    """Delete all existing data from all tables."""
    print("🗑️  Clearing all existing data...")
    PaymentLog.query.delete()
    Receipt.query.delete()
    UtilityUsage.query.delete()
    UtilityPrice.query.delete()
    TenantHistory.query.delete()
    Tenant.query.delete()
    Room.query.delete()
    Building.query.delete()
    User.query.delete()
    db.session.commit()
    print("✅ All data cleared.")


def seed_users():
    """Create admin user."""
    print("\n👤 Seeding users...")
    admin = User(
        username='admin',
        full_name='Admin User'
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print("✅ Admin user created (username: admin, password: admin123)")
    return admin


def seed_buildings():
    """Create test buildings."""
    print("\n🏢 Seeding buildings...")
    buildings = [
        Building(
            name='Downtown Heights',
            address='123 Main Street, Phnom Penh'
        ),
        Building(
            name='Riverside Apartments',
            address='456 Sisowath Quay, Phnom Penh'
        ),
        Building(
            name='Tech Park Residences',
            address='789 Soviet Boulevard, Phnom Penh'
        ),
    ]
    db.session.add_all(buildings)
    db.session.commit()
    print(f"✅ Created {len(buildings)} buildings")
    return buildings


def seed_rooms(buildings):
    """Create test rooms across buildings."""
    print("\n🚪 Seeding rooms...")
    rooms = []

    # Building 1: 5 rooms
    for i in range(1, 6):
        room = Room(
            building_id=buildings[0].id,
            room_number=f'101{i}',
            floor=1,
            room_type='single' if i <= 3 else 'double',
            price=300 if i <= 3 else 450,
            deposit_amount=500,
            status='occupied' if i <= 4 else 'available'
        )
        rooms.append(room)

    # Building 2: 5 rooms
    for i in range(1, 6):
        room = Room(
            building_id=buildings[1].id,
            room_number=f'201{i}',
            floor=2,
            room_type='double' if i <= 3 else 'studio',
            price=400 if i <= 3 else 250,
            deposit_amount=600,
            status='occupied' if i <= 3 else 'available'
        )
        rooms.append(room)

    # Building 3: 5 rooms
    for i in range(1, 6):
        room = Room(
            building_id=buildings[2].id,
            room_number=f'301{i}',
            floor=3,
            room_type='single' if i in [1, 2, 5] else 'double',
            price=350 if i in [1, 2, 5] else 500,
            deposit_amount=550,
            status='occupied' if i in [1, 2, 3] else 'maintenance' if i == 4 else 'available'
        )
        rooms.append(room)

    db.session.add_all(rooms)
    db.session.commit()
    print(f"✅ Created {len(rooms)} rooms")
    return rooms


def seed_utility_prices():
    """Create utility price rates."""
    print("\n💰 Seeding utility prices...")
    prices = [
        UtilityPrice(
            utility_type='electricity',
            price_per_unit=1850,  # KHR per kWh
            effective_date=date(2026, 1, 1)
        ),
        UtilityPrice(
            utility_type='water',
            price_per_unit=3200,  # KHR per m³
            effective_date=date(2026, 1, 1)
        ),
    ]
    db.session.add_all(prices)
    db.session.commit()
    print(f"✅ Created {len(prices)} utility price rates")
    return prices


def seed_tenants(rooms):
    """Create active tenants in occupied rooms."""
    print("\n👥 Seeding tenants...")
    occupied_rooms = [r for r in rooms if r.status == 'occupied']

    tenants_data = [
        {
            'name': 'Samnang Khouth',
            'gender': 'M',
            'nid': '123456789012',
            'tel': '0971234567',
            'emergency_contact_name': 'Mom Khouth',
            'emergency_contact_tel': '0971234568',
            'num_roommates': 1,
            'contract_duration': 'monthly',
            'move_in_date': date(2025, 6, 1),
            'deposit_paid': 500,
        },
        {
            'name': 'Chhorvy Touch',
            'gender': 'F',
            'nid': '987654321098',
            'tel': '0879876543',
            'emergency_contact_name': 'Dad Touch',
            'emergency_contact_tel': '0879876544',
            'num_roommates': 1,
            'contract_duration': 'monthly',
            'move_in_date': date(2025, 8, 15),
            'deposit_paid': 600,
        },
        {
            'name': 'Sokhem Ratana',
            'gender': 'M',
            'nid': '555666777888',
            'tel': '0869999999',
            'emergency_contact_name': 'Sister Ratana',
            'emergency_contact_tel': '0869999990',
            'num_roommates': 2,
            'contract_duration': 'monthly',
            'move_in_date': date(2025, 4, 20),
            'deposit_paid': 600,
        },
        {
            'name': 'Phary Lily',
            'gender': 'F',
            'nid': '111222333444',
            'tel': '0955555555',
            'emergency_contact_name': 'Mom Lily',
            'emergency_contact_tel': '0955555556',
            'num_roommates': 1,
            'contract_duration': 'monthly',
            'move_in_date': date(2025, 9, 1),
            'deposit_paid': 500,
        },
    ]

    tenants = []
    for i, tenant_data in enumerate(tenants_data):
        if i < len(occupied_rooms):
            tenant = Tenant(
                room_id=occupied_rooms[i].id,
                **tenant_data,
                is_active=True
            )
            tenants.append(tenant)

    db.session.add_all(tenants)
    db.session.commit()
    print(f"✅ Created {len(tenants)} active tenants")
    return tenants


def seed_tenant_history(rooms):
    """Create historical tenant records (moved out)."""
    print("\n📋 Seeding tenant history...")
    history = [
        TenantHistory(
            room_id=rooms[0].id,
            name='Somchai Old Tenant',
            gender='M',
            nid='999888777666',
            tel='0961111111',
            num_roommates=1,
            move_in_date=date(2024, 1, 10),
            move_out_date=date(2025, 5, 31),
            move_out_reason='End of contract',
            deposit_paid=500,
            deposit_refunded=500,
        ),
        TenantHistory(
            room_id=rooms[1].id,
            name='Bopha Former Tenant',
            gender='F',
            nid='555444333222',
            tel='0962222222',
            num_roommates=1,
            move_in_date=date(2024, 6, 1),
            move_out_date=date(2025, 8, 10),
            move_out_reason='Job transfer',
            deposit_paid=600,
            deposit_refunded=600,
        ),
    ]
    db.session.add_all(history)
    db.session.commit()
    print(f"✅ Created {len(history)} tenant history records")
    return history


def seed_utility_usage(rooms):
    """Create sample meter readings for current billing period."""
    print("\n📊 Seeding utility usage (meter readings)...")
    current_month = 6
    current_year = 2026

    usage = []
    for i, room in enumerate(rooms[:8]):  # Sample 8 rooms
        meter_reading = UtilityUsage(
            room_id=room.id,
            billing_month=current_month,
            billing_year=current_year,
            electricity_from=100 + i * 10,
            electricity_to=120 + i * 10,
            electricity_amount=None,
            water_from=50 + i * 5,
            water_to=60 + i * 5,
            water_amount=None,
        )
        usage.append(meter_reading)

    db.session.add_all(usage)
    db.session.commit()
    print(f"✅ Created {len(usage)} utility usage records")
    return usage


def seed_receipts(tenants, rooms):
    """Create sample receipts/bills."""
    print("\n📄 Seeding receipts (bills)...")

    receipts = []
    base_date = date(2026, 6, 19)

    for month_offset in range(3):  # 3 months of history
        billing_month = (base_date.month - month_offset - 1) % 12 + 1
        billing_year = base_date.year if month_offset == 0 else base_date.year - 1

        for i, tenant in enumerate(tenants):
            receipt_num = f"RCP-{billing_year}-{billing_month:02d}-{i+1:03d}"
            room = tenant.room

            electricity_units = 20 + i * 5
            water_units = 5 + i * 2

            electricity_total = electricity_units * 1850
            water_total = water_units * 3200

            total = room.price + electricity_total + water_total

            # Vary payment status
            payment_status = 'paid' if month_offset > 0 else 'unpaid' if i % 2 == 0 else 'partial'
            paid_amount = total if payment_status == 'paid' else total * 0.5 if payment_status == 'partial' else 0

            receipt = Receipt(
                receipt_number=receipt_num,
                room_id=room.id,
                tenant_id=tenant.id,
                billing_month=billing_month,
                billing_year=billing_year,
                room_price=room.price,
                electricity_from=100 + i * 10,
                electricity_to=100 + i * 10 + electricity_units,
                electricity_units=electricity_units,
                electricity_price_per_unit=1850,
                electricity_total=electricity_total,
                water_from=50 + i * 2,
                water_to=50 + i * 2 + water_units,
                water_units=water_units,
                water_price_per_unit=3200,
                water_total=water_total,
                previous_balance=0,
                fee=0,
                late_fee=50 if month_offset > 1 else 0,
                discount=0,
                total_amount=total,
                paid_amount=paid_amount,
                remaining_balance=total - paid_amount,
                payment_status=payment_status,
                payment_method='cash' if payment_status == 'paid' else None,
                payment_date=base_date if payment_status == 'paid' else None,
                notes='Sample receipt from seed data' if month_offset == 0 else None,
            )
            receipts.append(receipt)

    db.session.add_all(receipts)
    db.session.commit()
    print(f"✅ Created {len(receipts)} receipt records")
    return receipts


def seed_payment_logs(receipts):
    """Create payment log records for paid receipts."""
    print("\n💳 Seeding payment logs...")

    logs = []
    base_date = date(2026, 6, 19)

    for receipt in receipts:
        if receipt.payment_status == 'paid':
            log = PaymentLog(
                receipt_id=receipt.id,
                amount=receipt.total_amount,
                payment_method=receipt.payment_method,
                payment_date=receipt.payment_date,
                verification_hash='VER12345' + str(receipt.id).zfill(5),
            )
            logs.append(log)
        elif receipt.payment_status == 'partial':
            log = PaymentLog(
                receipt_id=receipt.id,
                amount=receipt.paid_amount,
                payment_method='cash',
                payment_date=base_date,
                verification_hash='VER67890' + str(receipt.id).zfill(5),
            )
            logs.append(log)

    db.session.add_all(logs)
    db.session.commit()
    print(f"✅ Created {len(logs)} payment log records")
    return logs


def main():
    """Run all seed functions."""
    app = create_app()

    with app.app_context():
        clear_all = '--clear' in sys.argv

        if clear_all:
            clear_all_data()

        print("\n" + "="*60)
        print("🌱 Room Rental Management System - Database Seeding")
        print("="*60)

        # Seed in order
        seed_users()
        buildings = seed_buildings()
        rooms = seed_rooms(buildings)
        seed_utility_prices()
        tenants = seed_tenants(rooms)
        seed_tenant_history(rooms)
        seed_utility_usage(rooms)
        receipts = seed_receipts(tenants, rooms)
        seed_payment_logs(receipts)

        print("\n" + "="*60)
        print("✨ Database seeding complete!")
        print("="*60)
        print("\n📊 Summary:")
        print(f"   • {len(buildings)} buildings")
        print(f"   • {len(rooms)} rooms")
        print(f"   • {len(tenants)} active tenants")
        print(f"   • {len(receipts)} receipts (3 months of billing)")
        print("\n🔐 Test credentials:")
        print("   • Username: admin")
        print("   • Password: admin123")
        print("\n")


if __name__ == '__main__':
    main()
