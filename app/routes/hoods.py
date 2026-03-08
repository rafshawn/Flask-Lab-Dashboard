from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from sqlalchemy.exc import IntegrityError
from datetime import date, timedelta, datetime
from app.extensions import db
from app.models import (
    Fumehood, Room, Floor, Building, HoodTest, HoodTestCycle,
    ActionOption, CustomTestType, CustomTestValue
)
from app.utils import get_current_org_id
from werkzeug.utils import secure_filename
import os
import qrcode

hoods_bp = Blueprint('hoods', __name__)


@hoods_bp.route('/hoods')
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
        elif filter_type == 'ActiveValid':
            if not h.is_expired(today) and h.status == 'Active':
                hoods.append(h)
        elif filter_type == 'Maintenance':
            if h.status == 'Maintenance':
                hoods.append(h)
        elif filter_type == 'ActionTaken':
            if h.action_taken_id is not None:
                hoods.append(h)

    return render_template('hoods.html', hoods=hoods, today=today, current_filter=filter_type)


@hoods_bp.route('/hoods/<int:id>')
def hood_detail(id):
    hood = Fumehood.query.get_or_404(id)
    org_id = get_current_org_id()
    action_options = ActionOption.query.filter_by(org_id=org_id).order_by(ActionOption.sort_order).all() if org_id else []
    custom_tests = CustomTestType.query.filter_by(org_id=org_id, is_active=True).order_by(CustomTestType.sort_order).all() if org_id else []
    return render_template('hood_detail.html', hood=hood, action_options=action_options, custom_tests=custom_tests)


@hoods_bp.route('/hoods/<int:id>/print-qr')
def print_qr(id):
    hood = Fumehood.query.get_or_404(id)
    # Get organization to display logo on the sticker
    org = None
    if hood.room and hood.room.floor and hood.room.floor.building and hood.room.floor.building.organization:
        org = hood.room.floor.building.organization
    return render_template('print_qr.html', hood=hood, org=org)


@hoods_bp.route('/hoods/<int:id>/delete', methods=['POST'])
def delete_hood(id):
    hood = Fumehood.query.get_or_404(id)
    room_id = hood.room_id
    db.session.delete(hood)
    db.session.commit()
    return redirect(url_for('organizations.room_detail', id=room_id))


@hoods_bp.route('/hoods/<int:id>/update_fields', methods=['POST'])
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
    return redirect(url_for('hoods.hood_detail', id=hood.id))


@hoods_bp.route('/add', methods=['GET', 'POST'])
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
            photo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
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
        qr_url = url_for('hoods.view_certificate', id=new_hood.id, _external=True)
        img = qrcode.make(qr_url)
        qr_filename = f"qrcodes/hood_{new_hood.id}.png"
        qr_path = os.path.join(current_app.static_folder, qr_filename)
        img.save(qr_path)

        new_hood.qr_code_path = qr_filename
        db.session.commit()

        return redirect(url_for('hoods.list_hoods'))

    return render_template('add_hood.html', rooms=rooms)


@hoods_bp.route('/hoods/<int:id>/edit', methods=['GET', 'POST'])
def edit_hood(id):
    hood = Fumehood.query.get_or_404(id)
    org_id = get_current_org_id()
    rooms = Room.query.join(Floor).join(Building).filter(Building.org_id == org_id).all() if org_id else []

    if request.method == 'POST':
        hood.hood_id = request.form['hood_id']
        hood.room_id = request.form['room_id']
        hood.status = request.form.get('status', 'Active')
        hood.faculty = request.form.get('faculty', '')
        hood.dept = request.form.get('dept', '')
        hood.contact_name = request.form.get('contact_name', '')
        hood.contact_email = request.form.get('contact_email', '')
        hood.manufacturer = request.form.get('manufacturer', '')
        hood.model = request.form.get('model', '')
        hood.serial_no = request.form.get('serial_no', '')
        hood.hood_type = request.form.get('hood_type', '')
        hood.sash_type = request.form.get('sash_type', '')
        hood.size = request.form.get('size', type=float)

        photo = request.files.get('photo')
        if photo and photo.filename:
            filename = secure_filename(f"hood_{hood.hood_id}_{photo.filename}")
            photo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            hood.photo_path = f"uploads/{filename}"

        try:
            db.session.commit()
            flash('Fumehood updated successfully!', 'success')
            return redirect(url_for('hoods.hood_detail', id=hood.id))
        except IntegrityError:
            db.session.rollback()
            flash('A Fumehood with that ID already exists.', 'error')

    return render_template('edit_hood.html', hood=hood, rooms=rooms)

@hoods_bp.route('/hoods/<int:id>/tests/add', methods=['GET', 'POST'])
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
            test_media.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
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
        return redirect(url_for('hoods.hood_detail', id=hood.id))
    return render_template('add_test.html', hood=hood)


@hoods_bp.route('/tests/<int:id>')
def test_detail(id):
    test_record = HoodTest.query.get_or_404(id)
    return render_template('test_detail.html', test=test_record)


@hoods_bp.route('/tests/<int:id>/delete', methods=['POST'])
def delete_test(id):
    test = HoodTest.query.get_or_404(id)
    hood_id = test.hood_id
    db.session.delete(test)
    db.session.commit()
    return redirect(url_for('hoods.hood_detail', id=hood_id))


@hoods_bp.route('/tests/<int:id>/cycles/add', methods=['GET', 'POST'])
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
        return redirect(url_for('hoods.test_detail', id=test_record.id))
    return render_template('add_cycle.html', test=test_record)


@hoods_bp.route('/reports/hoods')
def print_hoods():
    filter_type = request.args.get('filter', 'All')
    status_filter = request.args.get('status', '')
    condition_filter = request.args.get('condition', '')
    search_q = request.args.get('q', '').lower()
    org_id = get_current_org_id()
    all_hoods = Fumehood.query.join(Room).join(Floor).join(Building).filter(Building.org_id == org_id).all() if org_id else []

    hoods = []
    title = "All Fumehoods"
    today = date.today()
    for h in all_hoods:
        if filter_type == 'All':
            title = "All Fumehoods"
            hoods.append(h)
        elif filter_type == 'Overdue':
            title = "Overdue Fumehoods Report"
            if h.is_expired(today): hoods.append(h)
        elif filter_type == 'Due1Week':
            title = "Hoods Due within 7 Days Report"
            exp = h.expiration_date()
            if exp and today <= exp <= today + timedelta(days=7): hoods.append(h)
        elif filter_type == 'Due2Months':
            title = "Hoods Due within 2 Months Report"
            exp = h.expiration_date()
            if exp and today <= exp <= today + timedelta(days=60): hoods.append(h)
        elif filter_type == 'ActiveValid':
            title = "Active & Valid Hoods Report"
            if not h.is_expired(today) and h.status == 'Active': hoods.append(h)
        elif filter_type == 'Maintenance':
            title = "Maintenance Hoods Report"
            if h.status == 'Maintenance': hoods.append(h)
        elif filter_type == 'ActionTaken':
            title = "Action Required Report"
            if h.action_taken_id is not None: hoods.append(h)

    # Apply client-side filters passed via query params
    if status_filter:
        hoods = [h for h in hoods if h.status == status_filter]
        title = f"{status_filter} Fumehoods Report"
    if condition_filter:
        if condition_filter.upper() == 'EXPIRED':
            hoods = [h for h in hoods if h.is_expired(today)]
            title = "Expired Fumehoods Report"
    if search_q:
        def matches_search(h):
            searchable = f"{h.hood_id} {h.room.building_name} {h.room.room_no} {h.dept or ''} {h.status}".lower()
            return search_q in searchable
        hoods = [h for h in hoods if matches_search(h)]

    return render_template('print_report.html', title=title, items=hoods, report_type="hoods")


@hoods_bp.route('/reports/hoods/<int:id>')
def print_hood_detail(id):
    hood = Fumehood.query.get_or_404(id)
    return render_template('print_report.html', title=f"Fumehood Detail: {hood.hood_id}", hood=hood, report_type="hood_detail")


@hoods_bp.route('/reports/tests/<int:id>')
def print_test_report(id):
    test = HoodTest.query.get_or_404(id)
    title = f"Test Report: {test.hood.hood_id} on {test.test_date}"
    return render_template('print_report.html', title=title, test=test, report_type="test_detail")


@hoods_bp.route('/certificate/<int:id>')
def view_certificate(id):
    hood = Fumehood.query.get_or_404(id)
    org = hood.room.floor.building.organization
    return render_template('certificate.html', hood=hood, org=org)
