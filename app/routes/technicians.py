from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Technician, HoodTest
from app.utils import get_current_org_id

technicians_bp = Blueprint('technicians', __name__)


@technicians_bp.route('/technicians')
def list_technicians():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard.dashboard'))
    technicians = Technician.query.filter_by(org_id=org_id).all()
    return render_template('technicians.html', technicians=technicians)


@technicians_bp.route('/technicians/<int:id>')
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


@technicians_bp.route('/profile')
def user_profile():
    # Without auth, default to first technician with admin role
    org_id = get_current_org_id()
    tech = Technician.query.filter_by(org_id=org_id, role='admin').first() if org_id else None
    if not tech:
        tech = Technician.query.first()
    if tech:
        return redirect(url_for('technicians.technician_profile', id=tech.id))
    return redirect(url_for('dashboard.dashboard'))


@technicians_bp.route('/technicians/add', methods=['POST'])
def add_technician():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard.dashboard'))
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
    return redirect(url_for('technicians.list_technicians'))


@technicians_bp.route('/technicians/<int:id>/delete', methods=['POST'])
def delete_technician(id):
    tech = Technician.query.get_or_404(id)
    db.session.delete(tech)
    db.session.commit()
    return redirect(url_for('technicians.list_technicians'))
