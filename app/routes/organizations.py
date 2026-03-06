from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Organization, Building, Floor, Room
from app.utils import get_current_org_id
from werkzeug.utils import secure_filename
import os

organizations_bp = Blueprint('organizations', __name__)


@organizations_bp.route('/orgs')
def list_orgs():
    orgs = Organization.query.all()
    return render_template('orgs.html', orgs=orgs)


@organizations_bp.route('/orgs/add', methods=['GET', 'POST'])
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
            logo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            logo_filename = f"uploads/{filename}"

        new_org = Organization(
            name=name, address_1=address_1, address_2=address_2, city=city,
            state=state, zip_code=zip_code, country=country, phone=phone,
            website=website, email=email, logo_path=logo_filename
        )
        db.session.add(new_org)
        db.session.commit()
        return redirect(url_for('organizations.list_orgs'))
    return render_template('add_org.html')


@organizations_bp.route('/orgs/<int:id>')
def org_detail(id):
    org = Organization.query.get_or_404(id)
    return render_template('org_detail.html', org=org)


@organizations_bp.route('/orgs/<int:id>/delete', methods=['POST'])
def delete_org(id):
    org = Organization.query.get_or_404(id)
    db.session.delete(org)
    db.session.commit()
    # Reset session org_id if they deleted their active org
    if session.get('org_id') == id:
        session.pop('org_id', None)
    return redirect(url_for('organizations.list_orgs'))


@organizations_bp.route('/buildings/<int:id>')
def building_detail(id):
    building = Building.query.get_or_404(id)
    return render_template('building_detail.html', building=building)


@organizations_bp.route('/buildings/<int:id>/delete', methods=['POST'])
def delete_building(id):
    building = Building.query.get_or_404(id)
    org_id = building.org_id
    db.session.delete(building)
    db.session.commit()
    return redirect(url_for('organizations.org_detail', id=org_id))


@organizations_bp.route('/rooms')
def list_rooms():
    org_id = get_current_org_id()
    rooms = Room.query.join(Floor).join(Building).filter(Building.org_id == org_id).all() if org_id else []
    return render_template('rooms.html', rooms=rooms)


@organizations_bp.route('/rooms/add', methods=['GET', 'POST'])
def add_room():
    org_id = get_current_org_id()
    if request.method == 'POST':
        floor_id = request.form['floor_id']
        room_no = request.form['room_no']
        is_active = request.form.get('is_active') == 'on'

        new_room = Room(floor_id=floor_id, room_no=room_no, is_active=is_active)
        db.session.add(new_room)
        db.session.commit()
        return redirect(url_for('organizations.list_rooms'))

    floors = Floor.query.join(Building).filter(Building.org_id == org_id).all() if org_id else []
    return render_template('add_room.html', floors=floors)


@organizations_bp.route('/rooms/<int:id>')
def room_detail(id):
    room = Room.query.get_or_404(id)
    return render_template('room_detail.html', room=room)


@organizations_bp.route('/rooms/<int:id>/delete', methods=['POST'])
def delete_room(id):
    room = Room.query.get_or_404(id)
    building_id = room.floor.building_id
    db.session.delete(room)
    db.session.commit()
    return redirect(url_for('organizations.building_detail', id=building_id))


@organizations_bp.route('/orgs/<int:id>/edit', methods=['GET', 'POST'])
def edit_org(id):
    org = Organization.query.get_or_404(id)
    if request.method == 'POST':
        org.name = request.form['name']
        org.address_1 = request.form.get('address_1', '')
        org.address_2 = request.form.get('address_2', '')
        org.city = request.form.get('city', '')
        org.state = request.form.get('state', '')
        org.zip_code = request.form.get('zip_code', '')
        org.country = request.form.get('country', '')
        org.phone = request.form.get('phone', '')
        org.website = request.form.get('website', '')
        org.email = request.form.get('email', '')

        logo = request.files.get('logo')
        if logo and logo.filename:
            filename = secure_filename(f"org_{org.name.replace(' ', '_')}_{logo.filename}")
            logo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            org.logo_path = f"uploads/{filename}"

        try:
            db.session.commit()
            flash('Organization updated successfully!', 'success')
            return redirect(url_for('organizations.org_detail', id=org.id))
        except IntegrityError:
            db.session.rollback()
            flash('An Organization with that name already exists.', 'error')

    return render_template('edit_org.html', org=org)


@organizations_bp.route('/buildings/<int:id>/edit', methods=['GET', 'POST'])
def edit_building(id):
    building = Building.query.get_or_404(id)
    if request.method == 'POST':
        building.name = request.form['name']
        building.address_1 = request.form.get('address_1', '')
        building.address_2 = request.form.get('address_2', '')
        building.city = request.form.get('city', '')
        building.state = request.form.get('state', '')
        building.zip_code = request.form.get('zip_code', '')
        building.country = request.form.get('country', '')
        building.campus = request.form.get('campus', '')

        try:
            db.session.commit()
            flash('Building updated successfully!', 'success')
            return redirect(url_for('organizations.building_detail', id=building.id))
        except IntegrityError:
            db.session.rollback()
            flash('A Building with that name already exists.', 'error')

    return render_template('edit_building.html', building=building)


@organizations_bp.route('/rooms/<int:id>/edit', methods=['GET', 'POST'])
def edit_room(id):
    room = Room.query.get_or_404(id)
    org_id = get_current_org_id()
    if request.method == 'POST':
        room.floor_id = request.form['floor_id']
        room.room_no = request.form['room_no']
        room.is_active = request.form.get('is_active') == 'on'

        try:
            db.session.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('organizations.room_detail', id=room.id))
        except IntegrityError:
            db.session.rollback()
            flash('This exact Room already exists on the selected floor.', 'error')

    floors = Floor.query.join(Building).filter(Building.org_id == org_id).all() if org_id else []
    return render_template('edit_room.html', room=room, floors=floors)
