"""Seed the database with sample data for development and testing."""
from datetime import date, timedelta
from flask import url_for, current_app
import random
import json
import os
import qrcode

from app.extensions import db
from app.models import (
    Organization, OrgSettings, CustomTestType, ActionOption, Technician,
    Building, Floor, Room, Fumehood, HoodTest, HoodTestCycle
)


def seed_data():
    """Populate the database with comprehensive dummy data."""
    if Organization.query.count() > 0:
        return {"message": "Data already exists!"}, 200

    # 1. Create Organization
    org1 = Organization(
        name="Memorial University of Newfoundland",
        address_1="230 Elizabeth Ave",
        city="St. John's",
        state="NL",
        zip_code="A1C 5S7",
        country="Canada",
        phone="709-864-8000",
        website="mun.ca",
        email="info@mun.ca"
    )
    db.session.add(org1)
    db.session.commit()

    # 1b. Create OrgSettings and default ActionOptions
    org_settings = OrgSettings(org_id=org1.id, face_velocity_default=100.0)
    db.session.add(org_settings)

    # Default custom test type (inactive by default per spec)
    tracer_gas = CustomTestType(org_id=org1.id, name='Tracer Gas Test', field_type='date', is_active=False, sort_order=0)
    db.session.add(tracer_gas)

    default_actions = [
        'Out of Service',
        'Referred to Facilities',
        'Referred to Tech Services',
        'Referred to EHS',
        'Referred to PI',
        'Could not gain access to lab',
        'Permanently out of service'
    ]
    for i, label in enumerate(default_actions):
        db.session.add(ActionOption(org_id=org1.id, label=label, is_default=True, sort_order=i))
    db.session.commit()

    # 2. Add Buildings
    building_names = ['Science Building', 'Chemistry Annex', 'Engineering Tower', 'Medicine West']
    buildings_db = []
    for b in building_names:
        b_obj = Building(
            org_id=org1.id,
            name=b,
            emergency_phone="555-" + str(random.randint(1000, 9999)),
            maintenance_phone="555-" + str(random.randint(1000, 9999)),
            maintenance_email="maint@" + "".join(b.split()).lower() + ".edu",
            what3words=f"word1.word2.{random.randint(1,100)}"
        )
        buildings_db.append(b_obj)
    db.session.add_all(buildings_db)
    db.session.commit()

    # 3. Add Floors and Rooms
    rooms_db = []
    for b in buildings_db:
        for f_idx in range(1, 4):
            f = Floor(building_id=b.id, name=f"Floor {f_idx}")
            db.session.add(f)
            db.session.commit()

            for r_idx in range(1, 4):
                r = Room(floor_id=f.id, room_no=f"{f_idx}0{r_idx}", is_active=True)
                rooms_db.append(r)
    db.session.add_all(rooms_db)
    db.session.commit()

    # 4. Setup Data pools
    depts = ['Biology', 'Chemistry', 'Physics', 'Biochemistry', 'Earth Sciences', 'Engineering']
    manufacturers = ['LabConco', 'Fisher Hamilton', 'Mott', 'Kewaunee', 'Baker']
    hood_types = ['Standard', 'Walk-in', 'Benchtop', 'Radioisotope']
    sash_types = ['Vertical', 'Horizontal', 'Combination']

    today = date.today()

    # 5. Create 35 Hoods distributed
    hoods_db = []
    for i in range(35):
        r = random.choice(rooms_db)
        d = random.choice(depts)
        m = random.choice(manufacturers)

        status = 'Maintenance' if random.random() < 0.1 else 'Active'

        h = Fumehood(
            hood_id=f"{d[:3].upper()}-FH{i+1:03d}",
            room_id=r.id,
            status=status,
            faculty='Science',
            dept=d,
            manufacturer=m,
            model=f"Pro-{random.randint(1,9)}X",
            serial_no=f"{random.randint(10000,99999)}A{i}",
            hood_type=random.choice(hood_types),
            sash_type=random.choice(sash_types),
            size=random.choice([4.0, 5.0, 6.0, 8.0])
        )
        hoods_db.append(h)
    db.session.add_all(hoods_db)
    db.session.commit()

    # Generate QR codes for seeded hoods
    for h in hoods_db:
        qr_url = f"http://127.0.0.1:8000/certificate/{h.id}"
        img = qrcode.make(qr_url)
        qr_filename = f"qrcodes/hood_{h.id}.png"
        qr_path = os.path.join(current_app.static_folder, qr_filename)
        img.save(qr_path)
        h.qr_code_path = qr_filename
    db.session.commit()

    # 5b. Create sample technicians
    tech_data = [
        {'name': 'Jamie Smith', 'email': 'j.smith@mun.ca', 'phone': '709-555-1001', 'office': 'Science Building 2, Room 204', 'role': 'admin'},
        {'name': 'Alex Admin', 'email': 'a.admin@mun.ca', 'phone': '709-555-1002', 'office': 'Core Science 1, Room 110', 'role': 'admin'},
        {'name': 'Taylor Tech', 'email': 't.tech@mun.ca', 'phone': '709-555-1003', 'office': 'Chemistry Building, Room 301', 'role': 'technician'},
        {'name': 'Sam Connor', 'email': 's.connor@mun.ca', 'phone': '709-555-1004', 'office': 'Science Building 2, Room 112', 'role': 'technician'},
    ]
    technicians_db = []
    for td in tech_data:
        t = Technician(org_id=org1.id, **td)
        technicians_db.append(t)
    db.session.add_all(technicians_db)
    db.session.commit()

    # 6. Create Tests and Cycles
    tests_db = []
    cycles_db = []

    for h in hoods_db:
        is_expired = random.random() < 0.3
        if is_expired:
            latest_test_days_ago = random.randint(370, 450)
        else:
            latest_test_days_ago = random.randint(5, 350)

        num_tests = random.randint(1, 3)
        for t_idx in range(num_tests):
            days_ago = latest_test_days_ago + (t_idx * random.randint(300, 360))
            t_date = today - timedelta(days=days_ago)

            rating = 'Fail' if random.random() < 0.05 else 'Pass'
            comment = "Standard certification passed." if rating == 'Pass' else "Failed velocity check. Needs motor repair."

            # Additional Optional test JSON map
            opt_tests = {
                "cross_draft": "Pass" if random.random() > 0.1 else "Fail",
                "noise_level": f"{random.randint(50, 65)} dB",
                "mechanical_system": "Operational"
            }

            assigned_tech = random.choice(technicians_db)

            t = HoodTest(
                hood_id=h.id,
                technician_id=assigned_tech.id,
                work_order_no=f"WO-202{t_idx}-{random.randint(1000,9999)}",
                report_no=f"REP-{random.randint(10000,99999)}",
                test_date=t_date,
                technologist=assigned_tech.name,
                test_rating=rating,
                comments=comment,
                avg_face_velocity_full=round(random.uniform(90.0, 110.0), 1),
                avg_face_velocity_half=round(random.uniform(95.0, 115.0), 1),
                tri_color_design='Pass',
                tri_color_full='Pass' if rating == 'Pass' else 'Fail',
                tri_color_walkby='Pass',
                optional_tests=json.dumps(opt_tests)
            )
            tests_db.append(t)

    db.session.add_all(tests_db)
    db.session.commit()

    for t in tests_db:
        for c_idx in range(random.randint(1, 2)):
            face_v = random.uniform(95.0, 115.0) if t.test_rating == 'Pass' else random.uniform(70.0, 85.0)
            c = HoodTestCycle(
                test_id=t.id,
                cycle_index=c_idx + 1,
                cycle_rating=t.test_rating,
                opening_height=random.choice([18.0, 20.0, 24.0]),
                opening_width=random.choice([48.0, 72.0, 96.0]),
                face_v_avg=round(face_v, 1),
                cross_h_avg=round(random.uniform(15.0, 30.0), 1),
                cross_v_avg=round(random.uniform(10.0, 25.0), 1)
            )
            cycles_db.append(c)

    db.session.add_all(cycles_db)
    db.session.commit()

    return {"message": "Advanced smarter dummy data seeded successfully!"}, 201
