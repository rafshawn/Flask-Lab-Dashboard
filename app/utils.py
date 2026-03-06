from flask import session
from app.models import Organization


def get_current_org_id():
    """Get the current organization ID from the session, or default to the first org."""
    org_id = session.get('org_id')
    if not org_id:
        org = Organization.query.first()
        if org:
            org_id = org.id
            session['org_id'] = org_id
    return org_id


def inject_orgs():
    """Context processor to inject organization data into all templates."""
    all_orgs = Organization.query.all()
    current_org = None
    if 'org_id' in session:
        current_org = Organization.query.get(session['org_id'])

    if not current_org and all_orgs:
        current_org = all_orgs[0]
        session['org_id'] = current_org.id

    return dict(
        all_orgs=all_orgs,
        current_org=current_org,
        org_settings=current_org.settings if current_org else None
    )
