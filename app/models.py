from datetime import date, timedelta
from app.extensions import db


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
    test_rating = db.Column(db.String(50), nullable=False)  # 'Pass', 'Fail'
    comments = db.Column(db.Text, nullable=True)
    test_media_path = db.Column(db.String(255), nullable=True)

    # Required Tests
    avg_face_velocity_full = db.Column(db.Float, nullable=True)
    avg_face_velocity_half = db.Column(db.Float, nullable=True)
    tri_color_design = db.Column(db.String(50), nullable=True)  # Pass/Fail/NA
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
