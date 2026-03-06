from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import random
import os
import qrcode

app = Flask(__name__)

# Use absolute path for DB for simpler execution
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fumehoods.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
from werkzeug.utils import secure_filename

app.secret_key = 'super_secret_dev_key'

@app.context_processor
def inject_orgs():
    all_orgs = Organization.query.all()
    current_org = None
    if 'org_id' in session:
        current_org = Organization.query.get(session['org_id'])

    if not current_org and all_orgs:
        current_org = all_orgs[0]
        session['org_id'] = current_org.id

    return dict(all_orgs=all_orgs, current_org=current_org, org_settings=current_org.settings if current_org else None)

@app.route('/set_org', methods=['POST'])
def set_org():
    org_id = request.form.get('org_id')
    if org_id:
        session['org_id'] = int(org_id)
    return redirect(request.referrer or url_for('dashboard'))

import json

class Organization(db.Model):
    __tablename__ = 'organization'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address_1 = db.Column(db.String(200), nullable=True)
    address_2 = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    logo_path = db.Column(db.String(255), nullable=True)
    buildings = db.relationship('Building', backref='organization', lazy=True, cascade="all, delete-orphan")
    settings = db.relationship('OrgSettings', backref='organization', uselist=False, lazy=True, cascade="all, delete-orphan")
    action_options = db.relationship('ActionOption', backref='organization', lazy=True, cascade="all, delete-orphan", order_by='ActionOption.sort_order')
    custom_test_types = db.relationship('CustomTestType', backref='organization', lazy=True, cascade="all, delete-orphan", order_by='CustomTestType.sort_order')
    technicians = db.relationship('Technician', backref='organization', lazy=True, cascade="all, delete-orphan")

class OrgSettings(db.Model):
    __tablename__ = 'org_settings'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False, unique=True)
    face_velocity_default = db.Column(db.Float, default=100.0)

class CustomTestType(db.Model):
    __tablename__ = 'custom_test_type'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    field_type = db.Column(db.String(50), nullable=False, default='date')  # 'date', 'text', 'number', 'pass_fail'
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    values = db.relationship('CustomTestValue', backref='test_type', lazy=True, cascade='all, delete-orphan')

class CustomTestValue(db.Model):
    __tablename__ = 'custom_test_value'
    id = db.Column(db.Integer, primary_key=True)
    hood_id = db.Column(db.Integer, db.ForeignKey('fumehood.id'), nullable=False)
    test_type_id = db.Column(db.Integer, db.ForeignKey('custom_test_type.id'), nullable=False)
    value = db.Column(db.Text, nullable=True)

class ActionOption(db.Model):
    __tablename__ = 'action_option'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    label = db.Column(db.String(150), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)

class Technician(db.Model):
    __tablename__ = 'technician'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    office = db.Column(db.String(150), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='technician')  # 'admin' or 'technician'
    created_at = db.Column(db.DateTime, default=db.func.now())
    tests = db.relationship('HoodTest', backref='technician', lazy=True)

class Building(db.Model):
    __tablename__ = 'building'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    emergency_phone = db.Column(db.String(50), nullable=True)
    maintenance_phone = db.Column(db.String(50), nullable=True)
    maintenance_email = db.Column(db.String(150), nullable=True)
    what3words = db.Column(db.String(100), nullable=True)
    floors = db.relationship('Floor', backref='building', lazy=True, cascade="all, delete-orphan")

class Floor(db.Model):
    __tablename__ = 'floor'
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('building.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    rooms = db.relationship('Room', backref='floor', lazy=True, cascade="all, delete-orphan")

class Room(db.Model):
    __tablename__ = 'room'
    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floor.id'), nullable=False)
    room_no = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    hoods = db.relationship('Fumehood', backref='room', lazy=True, cascade="all, delete-orphan")

    @property
    def building_name(self):
        return self.floor.building.name if self.floor and self.floor.building else "Unknown"

class Fumehood(db.Model):
    __tablename__ = 'fumehood'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    hood_id = db.Column(db.String(50), nullable=False, unique=True)
    faculty = db.Column(db.String(100), nullable=True)
    dept = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False)
    contact_name = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    serial_no = db.Column(db.String(100), nullable=True)
    hood_type = db.Column(db.String(100), nullable=True)
    sash_type = db.Column(db.String(100), nullable=True)
    size = db.Column(db.Float, nullable=True)
    qr_code_path = db.Column(db.String(255), nullable=True)
    photo_path = db.Column(db.String(255), nullable=True)
    # Phase 11: Configurable fields
    action_taken_id = db.Column(db.Integer, db.ForeignKey('action_option.id'), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    face_velocity_design = db.Column(db.Float, nullable=True)
    action_taken = db.relationship('ActionOption', foreign_keys=[action_taken_id], lazy=True)
    custom_values = db.relationship('CustomTestValue', backref='hood', lazy=True, cascade='all, delete-orphan')
    tests = db.relationship('HoodTest', backref='hood', lazy=True, order_by="desc(HoodTest.test_date)", cascade="all, delete-orphan")

    def latest_test(self):
        return HoodTest.query.filter_by(hood_id=self.id).order_by(HoodTest.test_date.desc()).first()

    def is_expired(self, ref_date=None):
        if ref_date is None:
            ref_date = date.today()
        lt = self.latest_test()
        if not lt:
            return True
        expiration_date = lt.test_date + timedelta(days=365)
        return ref_date > expiration_date

    def expiration_date(self):
        lt = self.latest_test()
        if not lt:
            return None
        return lt.test_date + timedelta(days=365)

class HoodTest(db.Model):
    __tablename__ = 'hood_test'
    id = db.Column(db.Integer, primary_key=True)
    hood_id = db.Column(db.Integer, db.ForeignKey('fumehood.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('technician.id'), nullable=True)
    work_order_no = db.Column(db.String(50), nullable=True)
    report_no = db.Column(db.String(50), nullable=True)
    test_date = db.Column(db.Date, nullable=False)
    technologist = db.Column(db.String(100), nullable=True)
    test_rating = db.Column(db.String(50), nullable=False) # 'Pass', 'Fail'
    comments = db.Column(db.Text, nullable=True)
    test_media_path = db.Column(db.String(255), nullable=True)

    # Required Tests
    avg_face_velocity_full = db.Column(db.Float, nullable=True)
    avg_face_velocity_half = db.Column(db.Float, nullable=True)
    tri_color_design = db.Column(db.String(50), nullable=True) # Pass/Fail/NA
    tri_color_full = db.Column(db.String(50), nullable=True)
    tri_color_walkby = db.Column(db.String(50), nullable=True)

    # Optional Tests stored as JSON string
    optional_tests = db.Column(db.Text, nullable=True)

    cycles = db.relationship('HoodTestCycle', backref='test', lazy=True, cascade="all, delete-orphan")

class HoodTestCycle(db.Model):
    __tablename__ = 'hood_test_cycle'
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('hood_test.id'), nullable=False)
    cycle_index = db.Column(db.Integer, nullable=False)
    cycle_rating = db.Column(db.String(50), nullable=True)
    opening_height = db.Column(db.Float, nullable=True)
    opening_width = db.Column(db.Float, nullable=True)
    face_v_avg = db.Column(db.Float, nullable=True)
    cross_h_avg = db.Column(db.Float, nullable=True)
    cross_v_avg = db.Column(db.Float, nullable=True)


def get_current_org_id():
    org_id = session.get('org_id')
    if not org_id:
        org = Organization.query.first()
        if org:
            org_id = org.id
            session['org_id'] = org_id
    return org_id

# Routes
@app.route('/')
def dashboard():
    org_id = get_current_org_id()
    if not org_id:
        return render_template('index.html', empty_state=True, status_chart=None, dept_chart=None, tests_chart=None, total=0)

    hoods = Fumehood.query.join(Room).join(Floor).join(Building).filter(Building.org_id == org_id).all()

    # Chart 1: Status Distribution
    expired_count = sum(1 for h in hoods if h.is_expired() and h.status == 'Active')
    active_valid = sum(1 for h in hoods if not h.is_expired() and h.status == 'Active')
    maintenance_count = sum(1 for h in hoods if h.status == 'Maintenance')

    status_chart = {
        'labels': ['Active (Valid)', 'Expired', 'Maintenance'],
        'data': [active_valid, expired_count, maintenance_count]
    }

    # Chart 2: Hoods by Department
    dept_counts = {}
    for h in hoods:
        d = h.dept or 'Unknown'
        dept_counts[d] = dept_counts.get(d, 0) + 1

    dept_chart = {
        'labels': list(dept_counts.keys()),
        'data': list(dept_counts.values())
    }

    # Chart 3: Tests Over Time (Last 6 Months)
    from dateutil.relativedelta import relativedelta
    today = date.today()
    six_months_ago = today - relativedelta(months=5)
    six_months_ago = six_months_ago.replace(day=1)

    tests = HoodTest.query.join(Fumehood).join(Room).join(Floor).join(Building).filter(
        Building.org_id == org_id,
        HoodTest.test_date >= six_months_ago
    ).all()

    # Initialize last 6 months buckets
    months_labels = []
    tests_by_month = {}

    curr = six_months_ago
    while curr <= today:
        label = curr.strftime('%b %Y')
        months_labels.append(label)
        tests_by_month[label] = 0
        curr += relativedelta(months=1)

    for t in tests:
        label = t.test_date.strftime('%b %Y')
        if label in tests_by_month:
            tests_by_month[label] += 1

    tests_chart = {
        'labels': months_labels,
        'data': [tests_by_month[l] for l in months_labels]
    }

    return render_template('index.html',
                           status_chart=status_chart,
                           dept_chart=dept_chart,
                           tests_chart=tests_chart,
                           total=len(hoods))

@app.route('/orgs')
def list_orgs():
    orgs = Organization.query.all()
    return render_template('orgs.html', orgs=orgs)

@app.route('/orgs/add', methods=['GET', 'POST'])
def add_org():
    if request.method == 'POST':
        name = request.form['name']
        address_1 = request.form.get('address_1', '')
        address_2 = request.form.get('address_2', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        zip_code = request.form.get('zip_code', '')
        country = request.form.get('country', '')
        phone = request.form.get('phone', '')
        website = request.form.get('website', '')
        email = request.form.get('email', '')

        logo = request.files.get('logo')
        logo_filename = None
        if logo and logo.filename:
            filename = secure_filename(f"org_{name.replace(' ', '_')}_{logo.filename}")
            logo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            logo_filename = f"uploads/{filename}"

        new_org = Organization(
            name=name, address_1=address_1, address_2=address_2, city=city,
            state=state, zip_code=zip_code, country=country, phone=phone,
            website=website, email=email, logo_path=logo_filename
        )
        db.session.add(new_org)
        db.session.commit()
        return redirect(url_for('list_orgs'))
    return render_template('add_org.html')

@app.route('/orgs/<int:id>')
def org_detail(id):
    org = Organization.query.get_or_404(id)
    return render_template('org_detail.html', org=org)

@app.route('/orgs/<int:id>/delete', methods=['POST'])
def delete_org(id):
    org = Organization.query.get_or_404(id)
    db.session.delete(org)
    db.session.commit()
    # Reset session org_id if they deleted their active org
    if session.get('org_id') == id:
        session.pop('org_id', None)
    return redirect(url_for('list_orgs'))

@app.route('/buildings/<int:id>')
def building_detail(id):
    building = Building.query.get_or_404(id)
    return render_template('building_detail.html', building=building)

@app.route('/buildings/<int:id>/delete', methods=['POST'])
def delete_building(id):
    building = Building.query.get_or_404(id)
    org_id = building.org_id
    db.session.delete(building)
    db.session.commit()
    return redirect(url_for('org_detail', id=org_id))

@app.route('/rooms')
def list_rooms():
    org_id = get_current_org_id()
    rooms = Room.query.join(Floor).join(Building).filter(Building.org_id == org_id).all() if org_id else []
    return render_template('rooms.html', rooms=rooms)

@app.route('/rooms/add', methods=['GET', 'POST'])
def add_room():
    org_id = get_current_org_id()
    if request.method == 'POST':
        floor_id = request.form['floor_id']
        room_no = request.form['room_no']
        is_active = request.form.get('is_active') == 'on'

        new_room = Room(floor_id=floor_id, room_no=room_no, is_active=is_active)
        db.session.add(new_room)
        db.session.commit()
        return redirect(url_for('list_rooms'))

    floors = Floor.query.join(Building).filter(Building.org_id == org_id).all() if org_id else []
    return render_template('add_room.html', floors=floors)

@app.route('/rooms/<int:id>')
def room_detail(id):
    room = Room.query.get_or_404(id)
    return render_template('room_detail.html', room=room)

@app.route('/rooms/<int:id>/delete', methods=['POST'])
def delete_room(id):
    room = Room.query.get_or_404(id)
    building_id = room.floor.building_id
    db.session.delete(room)
    db.session.commit()
    return redirect(url_for('building_detail', id=building_id))

@app.route('/hoods')
def list_hoods():
    org_id = get_current_org_id()
    if not org_id:
        return render_template('hoods.html', hoods=[], empty_state=True)

    filter_type = request.args.get('filter', 'All')
    all_hoods = Fumehood.query.join(Room).join(Floor).join(Building).filter(Building.org_id == org_id).all() if org_id else []
    hoods = []

    today = date.today()
    for h in all_hoods:
        if filter_type == 'All':
            hoods.append(h)
        elif filter_type == 'Overdue':
            if h.is_expired(today):
                hoods.append(h)
        elif filter_type == 'Due1Week':
            exp = h.expiration_date()
            if exp and today <= exp <= today + timedelta(days=7):
                hoods.append(h)
        elif filter_type == 'Due2Months':
            exp = h.expiration_date()
            if exp and today <= exp <= today + timedelta(days=60):
                hoods.append(h)

    return render_template('hoods.html', hoods=hoods, today=today, current_filter=filter_type)

@app.route('/hoods/<int:id>')
def hood_detail(id):
    hood = Fumehood.query.get_or_404(id)
    org_id = get_current_org_id()
    action_options = ActionOption.query.filter_by(org_id=org_id).order_by(ActionOption.sort_order).all() if org_id else []
    custom_tests = CustomTestType.query.filter_by(org_id=org_id, is_active=True).order_by(CustomTestType.sort_order).all() if org_id else []
    return render_template('hood_detail.html', hood=hood, action_options=action_options, custom_tests=custom_tests)

@app.route('/hoods/<int:id>/delete', methods=['POST'])
def delete_hood(id):
    hood = Fumehood.query.get_or_404(id)
    room_id = hood.room_id
    db.session.delete(hood)
    db.session.commit()
    return redirect(url_for('room_detail', id=room_id))

@app.route('/hoods/<int:id>/update_fields', methods=['POST'])
def update_hood_fields(id):
    hood = Fumehood.query.get_or_404(id)
    action_id = request.form.get('action_taken_id')
    hood.action_taken_id = int(action_id) if action_id else None
    hood.comments = request.form.get('comments', '').strip() or None
    fv = request.form.get('face_velocity_design', type=float)
    hood.face_velocity_design = fv if fv else None

    # Handle custom test values
    org_id = get_current_org_id()
    if org_id:
        active_tests = CustomTestType.query.filter_by(org_id=org_id, is_active=True).all()
        for ct in active_tests:
            val = request.form.get(f'custom_{ct.id}', '').strip()
            # Find existing value or create new
            existing = CustomTestValue.query.filter_by(hood_id=hood.id, test_type_id=ct.id).first()
            if val:
                if existing:
                    existing.value = val
                else:
                    db.session.add(CustomTestValue(hood_id=hood.id, test_type_id=ct.id, value=val))
            elif existing:
                db.session.delete(existing)

    db.session.commit()
    return redirect(url_for('hood_detail', id=hood.id))

@app.route('/add', methods=['GET', 'POST'])
def add_hood():
    org_id = get_current_org_id()
    rooms = Room.query.join(Floor).join(Building).filter(Building.org_id == org_id).all() if org_id else []
    if request.method == 'POST':
        hood_id = request.form['hood_id']
        room_id = request.form['room_id']
        status = request.form.get('status', 'Active')
        faculty = request.form.get('faculty', '')
        dept = request.form.get('dept', '')
        contact_name = request.form.get('contact_name', '')
        contact_email = request.form.get('contact_email', '')
        manufacturer = request.form.get('manufacturer', '')
        model = request.form.get('model', '')
        serial_no = request.form.get('serial_no', '')
        hood_type = request.form.get('hood_type', '')
        sash_type = request.form.get('sash_type', '')
        size = request.form.get('size', type=float)

        photo = request.files.get('photo')
        photo_filename = None
        if photo and photo.filename:
            filename = secure_filename(f"hood_{hood_id}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_filename = f"uploads/{filename}"

        new_hood = Fumehood(
            hood_id=hood_id, room_id=room_id, status=status,
            faculty=faculty, dept=dept, contact_name=contact_name,
            contact_email=contact_email, manufacturer=manufacturer,
            model=model, serial_no=serial_no, hood_type=hood_type,
            sash_type=sash_type, size=size, photo_path=photo_filename
        )
        db.session.add(new_hood)
        db.session.commit()

        # Generate QR
        qr_url = url_for('view_certificate', id=new_hood.id, _external=True)
        img = qrcode.make(qr_url)
        qr_filename = f"qrcodes/hood_{new_hood.id}.png"
        qr_path = os.path.join(app.root_path, 'static', qr_filename)
        img.save(qr_path)

        new_hood.qr_code_path = qr_filename
        db.session.commit()

        return redirect(url_for('list_hoods'))

    return render_template('add_hood.html', rooms=rooms)

@app.route('/hoods/<int:id>/tests/add', methods=['GET', 'POST'])
def add_test(id):
    hood = Fumehood.query.get_or_404(id)
    if request.method == 'POST':
        test_date_str = request.form['test_date']
        technologist = request.form.get('technologist', '')
        test_rating = request.form['test_rating']
        work_order_no = request.form.get('work_order_no', '')
        report_no = request.form.get('report_no', '')
        comments = request.form.get('comments', '')

        # Required Tests
        avg_face_velocity_full = request.form.get('avg_face_velocity_full', type=float)
        avg_face_velocity_half = request.form.get('avg_face_velocity_half', type=float)
        tri_color_design = request.form.get('tri_color_design', '')
        tri_color_full = request.form.get('tri_color_full', '')
        tri_color_walkby = request.form.get('tri_color_walkby', '')

        test_media = request.files.get('test_media')
        media_filename = None
        if test_media and test_media.filename:
            filename = secure_filename(f"test_{hood.id}_{test_date_str}_{test_media.filename}")
            test_media.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            media_filename = f"uploads/{filename}"

        test_date = datetime.strptime(test_date_str, '%Y-%m-%d').date()

        new_test = HoodTest(
            hood_id=hood.id, test_date=test_date, technologist=technologist,
            test_rating=test_rating, work_order_no=work_order_no, report_no=report_no, comments=comments,
            avg_face_velocity_full=avg_face_velocity_full, avg_face_velocity_half=avg_face_velocity_half,
            tri_color_design=tri_color_design, tri_color_full=tri_color_full, tri_color_walkby=tri_color_walkby,
            test_media_path=media_filename
        )
        db.session.add(new_test)
        db.session.commit()
        return redirect(url_for('hood_detail', id=hood.id))
    return render_template('add_test.html', hood=hood)

@app.route('/tests/<int:id>')
def test_detail(id):
    test_record = HoodTest.query.get_or_404(id)
    return render_template('test_detail.html', test=test_record)

@app.route('/tests/<int:id>/delete', methods=['POST'])
def delete_test(id):
    test = HoodTest.query.get_or_404(id)
    hood_id = test.hood_id
    db.session.delete(test)
    db.session.commit()
    return redirect(url_for('hood_detail', id=hood_id))

@app.route('/tests/<int:id>/cycles/add', methods=['GET', 'POST'])
def add_cycle(id):
    test_record = HoodTest.query.get_or_404(id)
    if request.method == 'POST':
        if not request.form.get('cycle_index'):
             cycle_index = len(test_record.cycles) + 1
        else:
            cycle_index = int(request.form['cycle_index'])

        cycle_rating = request.form.get('cycle_rating', '')
        opening_height = request.form.get('opening_height', type=float)
        opening_width = request.form.get('opening_width', type=float)
        face_v_avg = request.form.get('face_v_avg', type=float)
        cross_h_avg = request.form.get('cross_h_avg', type=float)
        cross_v_avg = request.form.get('cross_v_avg', type=float)

        new_cycle = HoodTestCycle(
            test_id=test_record.id, cycle_index=cycle_index, cycle_rating=cycle_rating,
            opening_height=opening_height, opening_width=opening_width,
            face_v_avg=face_v_avg, cross_h_avg=cross_h_avg, cross_v_avg=cross_v_avg
        )
        db.session.add(new_cycle)
        db.session.commit()
        return redirect(url_for('test_detail', id=test_record.id))
    return render_template('add_cycle.html', test=test_record)

@app.route('/reports/hoods')
def print_hoods():
    hoods = Fumehood.query.all()
    return render_template('print_report.html', title="All Fumehoods", items=hoods, report_type="hoods")

@app.route('/reports/hoods/<int:id>')
def print_hood_detail(id):
    hood = Fumehood.query.get_or_404(id)
    return render_template('print_report.html', title=f"Fumehood Detail: {hood.hood_id}", hood=hood, report_type="hood_detail")

# --- Phase 11: Settings Routes ---

@app.route('/settings', methods=['GET', 'POST'])
def org_settings():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard'))
    org = Organization.query.get_or_404(org_id)
    # Ensure settings exist
    if not org.settings:
        s = OrgSettings(org_id=org.id)
        db.session.add(s)
        db.session.commit()
    if request.method == 'POST':
        fv = request.form.get('face_velocity_default', type=float)
        if fv:
            org.settings.face_velocity_default = fv
        db.session.commit()
        return redirect(url_for('org_settings'))
    actions = ActionOption.query.filter_by(org_id=org_id).order_by(ActionOption.sort_order).all()
    custom_tests = CustomTestType.query.filter_by(org_id=org_id).order_by(CustomTestType.sort_order).all()
    return render_template('settings.html', org=org, settings=org.settings, actions=actions, custom_tests=custom_tests)

@app.route('/settings/actions/add', methods=['POST'])
def add_action_option():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard'))
    label = request.form.get('label', '').strip()
    if label:
        max_order = db.session.query(db.func.max(ActionOption.sort_order)).filter_by(org_id=org_id).scalar() or 0
        action = ActionOption(org_id=org_id, label=label, is_default=False, sort_order=max_order + 1)
        db.session.add(action)
        db.session.commit()
    return redirect(url_for('org_settings'))

@app.route('/settings/actions/<int:id>/delete', methods=['POST'])
def delete_action_option(id):
    action = ActionOption.query.get_or_404(id)
    if action.is_default:
        return redirect(url_for('org_settings'))
    db.session.delete(action)
    db.session.commit()
    return redirect(url_for('org_settings'))

@app.route('/settings/tests/add', methods=['POST'])
def add_custom_test_type():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard'))
    name = request.form.get('name', '').strip()
    field_type = request.form.get('field_type', 'date')
    if name and field_type in ('date', 'text', 'number', 'pass_fail'):
        max_order = db.session.query(db.func.max(CustomTestType.sort_order)).filter_by(org_id=org_id).scalar() or 0
        ct = CustomTestType(org_id=org_id, name=name, field_type=field_type, is_active=True, sort_order=max_order + 1)
        db.session.add(ct)
        db.session.commit()
    return redirect(url_for('org_settings'))

@app.route('/settings/tests/<int:id>/toggle', methods=['POST'])
def toggle_custom_test_type(id):
    ct = CustomTestType.query.get_or_404(id)
    ct.is_active = not ct.is_active
    db.session.commit()
    return redirect(url_for('org_settings'))

@app.route('/settings/tests/<int:id>/delete', methods=['POST'])
def delete_custom_test_type(id):
    ct = CustomTestType.query.get_or_404(id)
    db.session.delete(ct)
    db.session.commit()
    return redirect(url_for('org_settings'))

# --- Phase 12: Technician Routes ---

@app.route('/technicians')
def list_technicians():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard'))
    technicians = Technician.query.filter_by(org_id=org_id).all()
    return render_template('technicians.html', technicians=technicians)

@app.route('/technicians/<int:id>')
def technician_profile(id):
    tech = Technician.query.get_or_404(id)
    # Get activity: recent tests by this technician
    recent_tests = HoodTest.query.filter_by(technician_id=tech.id).order_by(HoodTest.test_date.desc()).limit(20).all()
    # Stats
    total_tests = HoodTest.query.filter_by(technician_id=tech.id).count()
    passed = HoodTest.query.filter_by(technician_id=tech.id, test_rating='Pass').count()
    pass_rate = round((passed / total_tests * 100), 1) if total_tests > 0 else 0
    # Unique hoods tested
    hoods_tested = db.session.query(db.func.count(db.distinct(HoodTest.hood_id))).filter_by(technician_id=tech.id).scalar() or 0
    return render_template('profile.html', tech=tech, recent_tests=recent_tests,
                           total_tests=total_tests, pass_rate=pass_rate, hoods_tested=hoods_tested)

@app.route('/profile')
def user_profile():
    # Without auth, default to first technician with admin role
    org_id = get_current_org_id()
    tech = Technician.query.filter_by(org_id=org_id, role='admin').first() if org_id else None
    if not tech:
        tech = Technician.query.first()
    if tech:
        return redirect(url_for('technician_profile', id=tech.id))
    return redirect(url_for('dashboard'))

@app.route('/technicians/add', methods=['POST'])
def add_technician():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard'))
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    office = request.form.get('office', '').strip()
    role = request.form.get('role', 'technician')
    if name:
        tech = Technician(org_id=org_id, name=name, email=email or None,
                          phone=phone or None, office=office or None, role=role)
        db.session.add(tech)
        db.session.commit()
    return redirect(url_for('list_technicians'))

@app.route('/technicians/<int:id>/delete', methods=['POST'])
def delete_technician(id):
    tech = Technician.query.get_or_404(id)
    db.session.delete(tech)
    db.session.commit()
    return redirect(url_for('list_technicians'))

@app.route('/api/seed', methods=['POST'])
def seed_data():
    if Organization.query.count() > 0:
        return jsonify({"message": "Data already exists!"}), 200

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
        qr_url = url_for('view_certificate', id=h.id, _external=True)
        img = qrcode.make(qr_url)
        qr_filename = f"qrcodes/hood_{h.id}.png"
        qr_path = os.path.join(app.root_path, 'static', qr_filename)
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

    return jsonify({"message": "Advanced smarter dummy data seeded successfully!"}), 201

@app.route('/certificate/<int:id>')
def view_certificate(id):
    hood = Fumehood.query.get_or_404(id)
    org = hood.room.floor.building.organization
    return render_template('certificate.html', hood=hood, org=org)

if __name__ == '__main__':
    with app.app_context():
        # Clear out current database by dropping and creating
        db.drop_all()
        db.create_all()
    app.run(debug=True, port=8000)
