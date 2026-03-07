from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import date, timedelta
from app.extensions import db
from app.models import (
    Organization, Fumehood, Room, Floor, Building, HoodTest
)
from app.utils import get_current_org_id

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def dashboard():
    org_id = get_current_org_id()
    if not org_id:
        return render_template('index.html',
            empty_state=True,
            status_chart=None,
            dept_chart=None,
            tests_chart=None,
            total=0
        )

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
        total=len(hoods)
    )


@dashboard_bp.route('/set_org', methods=['POST'])
def set_org():
    org_id = request.form.get('org_id')
    if org_id:
        session['org_id'] = int(org_id)
    return redirect(request.referrer or url_for('dashboard.dashboard'))
