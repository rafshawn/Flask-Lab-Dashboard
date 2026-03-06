from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import (
    Organization, OrgSettings, ActionOption, CustomTestType
)
from app.utils import get_current_org_id

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings', methods=['GET', 'POST'])
def org_settings():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard.dashboard'))
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
        return redirect(url_for('settings.org_settings'))
    actions = ActionOption.query.filter_by(org_id=org_id).order_by(ActionOption.sort_order).all()
    custom_tests = CustomTestType.query.filter_by(org_id=org_id).order_by(CustomTestType.sort_order).all()
    return render_template('settings.html', org=org, settings=org.settings, actions=actions, custom_tests=custom_tests)


@settings_bp.route('/settings/actions/add', methods=['POST'])
def add_action_option():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard.dashboard'))
    label = request.form.get('label', '').strip()
    if label:
        max_order = db.session.query(db.func.max(ActionOption.sort_order)).filter_by(org_id=org_id).scalar() or 0
        action = ActionOption(org_id=org_id, label=label, is_default=False, sort_order=max_order + 1)
        db.session.add(action)
        db.session.commit()
    return redirect(url_for('settings.org_settings'))


@settings_bp.route('/settings/actions/<int:id>/delete', methods=['POST'])
def delete_action_option(id):
    action = ActionOption.query.get_or_404(id)
    if action.is_default:
        return redirect(url_for('settings.org_settings'))
    db.session.delete(action)
    db.session.commit()
    return redirect(url_for('settings.org_settings'))


@settings_bp.route('/settings/tests/add', methods=['POST'])
def add_custom_test_type():
    org_id = get_current_org_id()
    if not org_id:
        return redirect(url_for('dashboard.dashboard'))
    name = request.form.get('name', '').strip()
    field_type = request.form.get('field_type', 'date')
    if name and field_type in ('date', 'text', 'number', 'pass_fail'):
        max_order = db.session.query(db.func.max(CustomTestType.sort_order)).filter_by(org_id=org_id).scalar() or 0
        ct = CustomTestType(org_id=org_id, name=name, field_type=field_type, is_active=True, sort_order=max_order + 1)
        db.session.add(ct)
        db.session.commit()
    return redirect(url_for('settings.org_settings'))


@settings_bp.route('/settings/tests/<int:id>/toggle', methods=['POST'])
def toggle_custom_test_type(id):
    ct = CustomTestType.query.get_or_404(id)
    ct.is_active = not ct.is_active
    db.session.commit()
    return redirect(url_for('settings.org_settings'))


@settings_bp.route('/settings/tests/<int:id>/delete', methods=['POST'])
def delete_custom_test_type(id):
    ct = CustomTestType.query.get_or_404(id)
    db.session.delete(ct)
    db.session.commit()
    return redirect(url_for('settings.org_settings'))
