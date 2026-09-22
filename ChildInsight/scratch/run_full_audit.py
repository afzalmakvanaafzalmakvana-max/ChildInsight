import re
import os
import sys
from html.parser import HTMLParser

# Add current workspace to path
sys.path.insert(0, r'c:\Users\User\Downloads\ChildInsight\ChildInsight')

from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.child_teacher_access import ChildTeacherAccess
from app.models.teacher_assignment import TeacherAssignment
from app.models.recommendation import Recommendation
from app.models.session import ActivitySession
from app.models.notification import Notification
from app.routes.teacher import _get_accessible_children_for_teacher

app = create_app('development')
client = app.test_client()

issues = []

def record_issue(area, page, steps, expected, actual, severity):
    issues.append({
        'area': area,
        'page': page,
        'steps': steps,
        'expected': expected,
        'actual': actual,
        'severity': severity
    })

def get_csrf(client, page_url='/auth/login'):
    res = client.get(page_url)
    html = res.data.decode('utf-8', errors='ignore')
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"\s+name="csrf_token"', html)
    return match.group(1) if match else None

def post_form(client, url, data=None, page_for_csrf=None, follow_redirects=True):
    data = data or {}
    csrf = get_csrf(client, page_for_csrf or url)
    if csrf:
        data['csrf_token'] = csrf
    return client.post(url, data=data, follow_redirects=follow_redirects)

class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.buttons = []
        self.forms = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'a':
            href = attrs_dict.get('href', '')
            self.links.append((href, attrs_dict.get('class', ''), attrs_dict.get('id', '')))
        elif tag == 'button':
            self.buttons.append((attrs_dict.get('type', ''), attrs_dict.get('onclick', ''), attrs_dict.get('class', ''), attrs_dict.get('id', '')))
        elif tag == 'form':
            self.forms.append((attrs_dict.get('action', ''), attrs_dict.get('method', 'get').upper()))

def audit_html_elements(page_url, html, role_name):
    parser = LinkCollector()
    parser.feed(html)
    for href, cls, el_id in parser.links:
        # Check for empty href or '#' that is not an explicit collapse/dropdown/tab/button toggle
        if href == '':
            record_issue(
                area=f'{role_name} Links',
                page=page_url,
                steps=f'Inspect anchor tags on {page_url}',
                expected='Link should have a valid destination',
                actual=f'Found empty href="" (class="{cls}", id="{el_id}")',
                severity='Minor'
            )
        elif href == '#' and not any(k in cls.lower() for k in ['dropdown', 'toggle', 'tab', 'collapse', 'btn']):
            record_issue(
                area=f'{role_name} Links',
                page=page_url,
                steps=f'Inspect anchor tags on {page_url}',
                expected='Link should have functional URL or JavaScript trigger',
                actual=f'Found dead anchor with href="#" (class="{cls}", id="{el_id}")',
                severity='Minor'
            )
        # Check for dead internal links (starting with '/')
        elif href.startswith('/') and not href.startswith('/static') and not href.startswith('/api/docs'):
            # Only test GET endpoints without parameter mutations
            if 'delete' not in href and 'revoke' not in href and 'logout' not in href and 'toggle' not in href:
                res = client.get(href)
                if res.status_code in (404, 500):
                    record_issue(
                        area=f'{role_name} Broken Link',
                        page=page_url,
                        steps=f'Follow link to {href} from {page_url}',
                        expected='Page should return 200 or 302',
                        actual=f'Received HTTP {res.status_code} for {href}',
                        severity='Major'
                    )

    # Check for dead buttons (button without type="submit", type="button" without onclick/id/class)
    for btn_type, onclick, cls, el_id in parser.buttons:
        if btn_type == 'button' and not onclick and not el_id and not cls:
            record_issue(
                area=f'{role_name} Buttons',
                page=page_url,
                steps=f'Inspect button elements on {page_url}',
                expected='Interactive button should have event handler or identifier',
                actual=f'Found unhandled button element with no onclick, id, or class on {page_url}',
                severity='Cosmetic'
            )

print("Starting Full Live System Audit...")

with app.app_context():
    # -------------------------------------------------------------
    # 1. Template Static Audit: check all .html files
    # -------------------------------------------------------------
    templates_dir = os.path.join(app.root_path, 'templates')
    for root, _, files in os.walk(templates_dir):
        for f in files:
            if f.endswith('.html'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, templates_dir)
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as tf:
                    content = tf.read()
                # Check for dead href="#"
                dead_hrefs = re.findall(r'<a\s+[^>]*href=["\']#["\'][^>]*>', content)
                for dh in dead_hrefs:
                    if not any(k in dh.lower() for k in ['dropdown', 'collapse', 'tab', 'btn', 'toggle', 'javascript']):
                        record_issue(
                            area='Static Template Inspection',
                            page=rel_path,
                            steps=f'Inspect template file {rel_path}',
                            expected='Anchor tags should have valid url_for or JavaScript trigger',
                            actual=f'Found href="#" without toggle handler: {dh.strip()}',
                            severity='Minor'
                        )

    # -------------------------------------------------------------
    # 2. Child Journey Audit
    # -------------------------------------------------------------
    print("\n--- Auditing Child Journey ---")
    # 2.1 Guest visits /child/home
    res = client.get('/child/home')
    if res.status_code != 200:
        record_issue('Child Journey', '/child/home', 'Visit /child/home as unauthenticated user', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/child/home', res.data.decode('utf-8', errors='ignore'), 'Child Guest')

    # Get sample children
    en_child = Child.query.filter_by(preferred_language='English').first() or Child.query.first()
    hi_child = Child.query.filter_by(preferred_language='Hindi').first() or Child.query.first()

    # Login as parent of en_child
    parent_user = db.session.get(User, en_child.parent_id)
    post_form(client, '/auth/login', {'email': parent_user.email, 'password': 'DemoPass123!'})

    # 2.2 Category Hub in English
    res = client.get(f'/child/{en_child.id}/activities')
    if res.status_code != 200:
        record_issue('Child Journey', f'/child/{en_child.id}/activities', 'Access English child category hub', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        html = res.data.decode('utf-8', errors='ignore')
        audit_html_elements(f'/child/{en_child.id}/activities', html, 'Child (EN)')
        if 'Visual Learning' not in html and 'Logic' not in html:
            record_issue('Child Journey', f'/child/{en_child.id}/activities', 'View category cards', 'Category names in English', 'Expected English categories not found', 'Major')

    # 2.3 Category Hub in Hindi
    if hi_child and hi_child.parent_id != parent_user.id:
        hi_parent = db.session.get(User, hi_child.parent_id)
        client.get('/auth/logout')
        post_form(client, '/auth/login', {'email': hi_parent.email, 'password': 'DemoPass123!'})

    res = client.get(f'/child/{hi_child.id}/activities')
    if res.status_code != 200:
        record_issue('Child Journey', f'/child/{hi_child.id}/activities', 'Access Hindi child category hub', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        html = res.data.decode('utf-8', errors='ignore')
        audit_html_elements(f'/child/{hi_child.id}/activities', html, 'Child (HI)')
        if not re.search(r'[\u0900-\u097F]', html):
            record_issue('Child Journey', f'/child/{hi_child.id}/activities', 'View category cards in Hindi', 'Devanagari script in category names', 'No Devanagari text rendered', 'Major')

    # 2.4 Activity List Screen
    cat = Category.query.first()
    res = client.get(f'/child/{hi_child.id}/category/{cat.id}')
    if res.status_code != 200:
        record_issue('Child Journey', f'/child/{hi_child.id}/category/{cat.id}', 'Open category activities list', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        html = res.data.decode('utf-8', errors='ignore')
        audit_html_elements(f'/child/{hi_child.id}/category/{cat.id}', html, 'Child (HI)')

    # 2.5 Play Activity Fully
    act = Activity.query.filter_by(category_id=cat.id, is_active=True).first()
    if act and act.questions.count() > 0:
        first_q = act.questions.first()
        res = client.get(f'/child/{hi_child.id}/play/{act.id}')
        if res.status_code != 200:
            record_issue('Child Journey', f'/child/{hi_child.id}/play/{act.id}', 'Open activity player', 'Status 200', f'Status {res.status_code}', 'Major')
        else:
            html = res.data.decode('utf-8', errors='ignore')
            audit_html_elements(f'/child/{hi_child.id}/play/{act.id}', html, 'Child Player')

        # Hint endpoint
        res = client.get(f'/child/{hi_child.id}/play/{act.id}/hint/{first_q.id}')
        if res.status_code != 200:
            record_issue('Child Journey', f'/child/{hi_child.id}/play/{act.id}/hint/{first_q.id}', 'Click hint button', 'Status 200 JSON with hint', f'Status {res.status_code}', 'Minor')

        # Answer submission
        res = post_form(client, f'/child/{hi_child.id}/play/{act.id}/answer', {
            'question_id': first_q.id,
            'answer': first_q.correct_answer,
            'response_time_seconds': 3.2
        }, page_for_csrf=f'/child/{hi_child.id}/play/{act.id}')
        if res.status_code not in (200, 302):
            record_issue('Child Journey', f'/child/{hi_child.id}/play/{act.id}/answer', 'Submit answer', 'Status 200 or 302', f'Status {res.status_code}', 'Major')

        # Skip question
        res = post_form(client, f'/child/{hi_child.id}/play/{act.id}/skip', {
            'question_id': first_q.id
        }, page_for_csrf=f'/child/{hi_child.id}/play/{act.id}')
        if res.status_code not in (200, 302):
            record_issue('Child Journey', f'/child/{hi_child.id}/play/{act.id}/skip', 'Click skip button', 'Status 200 or 302', f'Status {res.status_code}', 'Minor')

        # Results screen
        res = client.get(f'/child/{hi_child.id}/results/{act.id}')
        if res.status_code != 200:
            record_issue('Child Journey', f'/child/{hi_child.id}/results/{act.id}', 'View activity results', 'Status 200', f'Status {res.status_code}', 'Major')
        else:
            html = res.data.decode('utf-8', errors='ignore')
            audit_html_elements(f'/child/{hi_child.id}/results/{act.id}', html, 'Child Results')

    # 2.6 Back navigation traversal at every screen
    child_screens = [
        f'/child/{hi_child.id}/activities',
        f'/child/{hi_child.id}/category/{cat.id}',
        f'/child/{hi_child.id}/play/{act.id}',
        f'/child/{hi_child.id}/results/{act.id}'
    ]
    for scr in child_screens:
        res = client.get(scr)
        if res.status_code == 200:
            html = res.data.decode('utf-8', errors='ignore')
            parser = LinkCollector()
            parser.feed(html)
            back_links = [href for href, cls, _ in parser.links if 'back' in href.lower() or 'back' in cls.lower() or '←' in href or 'categories' in href or 'activities' in href]
            for bl in back_links:
                if bl.startswith('/'):
                    chk = client.get(bl)
                    if chk.status_code not in (200, 302):
                        record_issue('Child Back Navigation', scr, f'Click back link {bl} on {scr}', 'Status 200 or 302', f'Status {chk.status_code}', 'Major')
                    if bl.startswith('/admin'):
                        record_issue('Child Back Navigation Security', scr, f'Inspect back link {bl}', 'Never link to admin routes', f'Admin route exposed: {bl}', 'Critical')

    # -------------------------------------------------------------
    # 3. Parent Journey Audit
    # -------------------------------------------------------------
    print("\n--- Auditing Parent Journey ---")
    client.get('/auth/logout')

    # 3.1 Register new parent
    unique_id = os.getpid()
    parent_email = f"audit_parent_{unique_id}@childinsight.demo"
    res = post_form(client, '/auth/register', {
        'name': 'Live Audit Parent',
        'email': parent_email,
        'password': 'AuditPassword123!',
        'confirm_password': 'AuditPassword123!',
        'role': 'parent'
    }, page_for_csrf='/auth/register')
    if res.status_code != 200 or b'Account created successfully' not in res.data:
        record_issue('Parent Journey', '/auth/register', 'Register new parent account', 'Account created flash message', f'Status {res.status_code}', 'Major')

    # 3.2 Login
    res = post_form(client, '/auth/login', {
        'email': parent_email,
        'password': 'AuditPassword123!'
    }, page_for_csrf='/auth/login')
    if b'Welcome back' not in res.data and b'Parent Dashboard' not in res.data:
        record_issue('Parent Journey', '/auth/login', 'Login as registered parent', 'Successful login to dashboard', 'Login failed', 'Critical')

    # 3.3 Add Child
    res = post_form(client, '/parent/children/add', {
        'name': f'Audit Learner {unique_id}',
        'age': 8,
        'grade': '3rd Grade',
        'preferred_language': 'Hindi'
    }, page_for_csrf='/parent/children/add')
    if res.status_code != 200 or f'Audit Learner {unique_id}'.encode() not in res.data:
        record_issue('Parent Journey', '/parent/children/add', 'Add a child profile', 'Child displayed on dashboard', f'Status {res.status_code}', 'Major')

    created_child = Child.query.filter_by(name=f'Audit Learner {unique_id}').first()

    if created_child:
        # 3.4 Edit Child
        res = post_form(client, f'/parent/children/{created_child.id}/edit', {
            'name': f'Audit Learner {unique_id} Edited',
            'age': 9,
            'grade': '4th Grade',
            'preferred_language': 'English'
        }, page_for_csrf=f'/parent/children/{created_child.id}/edit')
        if res.status_code != 200 or f'Audit Learner {unique_id} Edited'.encode() not in res.data:
            record_issue('Parent Journey', f'/parent/children/{created_child.id}/edit', 'Update child profile', 'Updated name displayed on dashboard', f'Status {res.status_code}', 'Major')

        # 3.5 View Dashboard
        res = client.get('/parent/dashboard')
        if res.status_code != 200:
            record_issue('Parent Journey', '/parent/dashboard', 'View parent dashboard', 'Status 200', f'Status {res.status_code}', 'Critical')
        else:
            audit_html_elements('/parent/dashboard', res.data.decode('utf-8', errors='ignore'), 'Parent')

        # 3.6 View Recommendations
        res = client.get(f'/parent/recommendations?child_id={created_child.id}')
        if res.status_code != 200:
            record_issue('Parent Journey', f'/parent/recommendations?child_id={created_child.id}', 'View recommendations', 'Status 200', f'Status {res.status_code}', 'Major')
        else:
            audit_html_elements(f'/parent/recommendations?child_id={created_child.id}', res.data.decode('utf-8', errors='ignore'), 'Parent')

        # 3.7 View Progress Reports
        res = client.get(f'/parent/progress-reports?child_id={created_child.id}')
        if res.status_code != 200:
            record_issue('Parent Journey', f'/parent/progress-reports?child_id={created_child.id}', 'View progress reports', 'Status 200', f'Status {res.status_code}', 'Major')
        else:
            audit_html_elements(f'/parent/progress-reports?child_id={created_child.id}', res.data.decode('utf-8', errors='ignore'), 'Parent')

        # 3.8 Export PDF & CSV
        res = client.get(f'/parent/children/{created_child.id}/report/pdf')
        if res.status_code != 200 or res.mimetype != 'application/pdf':
            record_issue('Parent Journey', f'/parent/children/{created_child.id}/report/pdf', 'Download PDF report', 'Status 200 application/pdf', f'Status {res.status_code}, type {res.mimetype}', 'Major')

        res = client.get(f'/parent/children/{created_child.id}/report/csv')
        if res.status_code != 200 or 'text/csv' not in res.mimetype:
            record_issue('Parent Journey', f'/parent/children/{created_child.id}/report/csv', 'Download CSV report', 'Status 200 text/csv', f'Status {res.status_code}, type {res.mimetype}', 'Major')

        # 3.9 Invite a Teacher
        teacher_account = User.query.filter_by(role='teacher', is_active=True).first()
        res = post_form(client, f'/parent/children/{created_child.id}/teacher-access/invite', {
            'teacher_email': teacher_account.email
        }, page_for_csrf=f'/parent/children/{created_child.id}')
        if res.status_code != 200 or b'Access request sent' not in res.data:
            record_issue('Parent Journey', f'/parent/children/{created_child.id}/teacher-access/invite', 'Invite teacher by email', 'Access request sent flash message', f'Status {res.status_code}', 'Major')

        # 3.10 Revoke Teacher Access
        grant = ChildTeacherAccess.query.filter_by(child_id=created_child.id, teacher_id=teacher_account.id).first()
        if grant:
            res = post_form(client, f'/parent/children/{created_child.id}/teacher-access/{grant.id}/revoke', {}, page_for_csrf=f'/parent/children/{created_child.id}')
            if res.status_code != 200:
                record_issue('Parent Journey', f'/parent/children/{created_child.id}/teacher-access/{grant.id}/revoke', 'Revoke teacher access', 'Status 200', f'Status {res.status_code}', 'Major')

        # 3.11 Notifications API
        res = client.get('/api/notifications')
        if res.status_code != 200:
            record_issue('Parent Journey', '/api/notifications', 'Fetch notifications API', 'Status 200 JSON', f'Status {res.status_code}', 'Minor')
        else:
            data = res.get_json()
            if not data or 'notifications' not in data:
                record_issue('Parent Journey', '/api/notifications', 'Inspect notifications API JSON', 'JSON with "notifications" array', f'Output: {data}', 'Minor')

    # -------------------------------------------------------------
    # 4. Teacher Journey Audit
    # -------------------------------------------------------------
    print("\n--- Auditing Teacher Journey ---")
    client.get('/auth/logout')
    teacher_user = User.query.filter_by(role='teacher', is_active=True).first()
    res = post_form(client, '/auth/login', {
        'email': teacher_user.email,
        'password': 'DemoPass123!'
    }, page_for_csrf='/auth/login')
    if res.status_code != 200 or b'Teacher' not in res.data:
        record_issue('Teacher Journey', '/auth/login', 'Teacher login', 'Successful login to teacher workspace', f'Status {res.status_code}', 'Critical')

    # 4.1 Teacher Dashboard
    res = client.get('/teacher/dashboard')
    if res.status_code != 200:
        record_issue('Teacher Journey', '/teacher/dashboard', 'View teacher dashboard', 'Status 200', f'Status {res.status_code}', 'Critical')
    else:
        audit_html_elements('/teacher/dashboard', res.data.decode('utf-8', errors='ignore'), 'Teacher Dashboard')

    # 4.2 Assigned & Invited Students List
    res = client.get('/teacher/students')
    if res.status_code != 200:
        record_issue('Teacher Journey', '/teacher/students', 'View students list', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/teacher/students', res.data.decode('utf-8', errors='ignore'), 'Teacher Students')

    # 4.3 Accept & Decline Invite Test
    demo_p = User.query.filter_by(role='parent').first()
    demo_c = Child.query.filter_by(parent_id=demo_p.id).first()
    inv1 = ChildTeacherAccess(
        child_id=demo_c.id,
        teacher_id=teacher_user.id,
        invited_email=teacher_user.email,
        status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
        requested_by_parent_id=demo_p.id
    )
    db.session.add(inv1)
    db.session.commit()

    # Accept
    res = post_form(client, f'/teacher/access-requests/{inv1.id}/accept', {}, page_for_csrf='/teacher/dashboard')
    if res.status_code != 200 or b'Access granted' not in res.data:
        record_issue('Teacher Journey', f'/teacher/access-requests/{inv1.id}/accept', 'Accept access request', 'Access granted flash message', f'Status {res.status_code}', 'Major')

    # Decline
    inv2 = ChildTeacherAccess(
        child_id=demo_c.id,
        teacher_id=teacher_user.id,
        invited_email=teacher_user.email,
        status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
        requested_by_parent_id=demo_p.id
    )
    db.session.add(inv2)
    db.session.commit()
    res = post_form(client, f'/teacher/access-requests/{inv2.id}/decline', {}, page_for_csrf='/teacher/dashboard')
    if res.status_code != 200 or b'declined' not in res.data.lower():
        record_issue('Teacher Journey', f'/teacher/access-requests/{inv2.id}/decline', 'Decline access request', 'Declined flash message', f'Status {res.status_code}', 'Major')

    # 4.4 View student's full report
    res = client.get(f'/teacher/students/{demo_c.id}')
    if res.status_code != 200:
        record_issue('Teacher Journey', f'/teacher/students/{demo_c.id}', 'View student full report', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements(f'/teacher/students/{demo_c.id}', res.data.decode('utf-8', errors='ignore'), 'Teacher Student Detail')

    # 4.5 Assign an activity
    assign_act = Activity.query.filter_by(is_active=True).first()
    res = post_form(client, f'/teacher/students/{demo_c.id}/assign-activity', {
        'activity_id': assign_act.id,
        'note': 'Audit test guided assignment'
    }, page_for_csrf=f'/teacher/students/{demo_c.id}')
    if res.status_code != 200 or b'assigned' not in res.data.lower():
        record_issue('Teacher Journey', f'/teacher/students/{demo_c.id}/assign-activity', 'Assign activity to student', 'Activity assigned flash message', f'Status {res.status_code}', 'Major')

    # 4.6 Assignments Hub
    res = client.get('/teacher/assignments')
    if res.status_code != 200:
        record_issue('Teacher Journey', '/teacher/assignments', 'View activity assignments hub', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/teacher/assignments', res.data.decode('utf-8', errors='ignore'), 'Teacher Assignments')

    # -------------------------------------------------------------
    # 5. Admin Journey Audit
    # -------------------------------------------------------------
    print("\n--- Auditing Admin Journey ---")
    client.get('/auth/logout')
    admin_user = User.query.filter_by(role='admin', is_active=True).first()
    res = post_form(client, '/auth/login', {
        'email': admin_user.email,
        'password': 'DemoPass123!'
    }, page_for_csrf='/auth/login')
    if res.status_code != 200 or b'Admin Console' not in res.data:
        record_issue('Admin Journey', '/auth/login', 'Admin login', 'Successful login to Admin Console', f'Status {res.status_code}', 'Critical')

    # 5.1 Dashboard
    res = client.get('/admin/dashboard')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/dashboard', 'View admin dashboard', 'Status 200', f'Status {res.status_code}', 'Critical')
    else:
        audit_html_elements('/admin/dashboard', res.data.decode('utf-8', errors='ignore'), 'Admin Dashboard')

    # 5.2 User Management
    res = client.get('/admin/users')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/users', 'View user directory', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/users', res.data.decode('utf-8', errors='ignore'), 'Admin Users')

    # 5.3 Category Management
    res = client.get('/admin/categories')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/categories', 'View category directory', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/categories', res.data.decode('utf-8', errors='ignore'), 'Admin Categories')

    # New category form
    res = client.get('/admin/categories/new')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/categories/new', 'Open new category form', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/categories/new', res.data.decode('utf-8', errors='ignore'), 'Admin New Category')

    # 5.4 Activity Management
    res = client.get('/admin/activities')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/activities', 'View activity catalog', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/activities', res.data.decode('utf-8', errors='ignore'), 'Admin Activities')

    # AI Draft Generation page
    res = client.get('/admin/activities/ai-draft/generate')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/activities/ai-draft/generate', 'Open AI draft generation screen', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/activities/ai-draft/generate', res.data.decode('utf-8', errors='ignore'), 'Admin AI Draft')

    # Bulk Review Workflow
    res = client.get('/admin/activities/bulk-draft-review')
    if res.status_code not in (200, 302):
        record_issue('Admin Journey', '/admin/activities/bulk-draft-review', 'Open bulk draft review screen', 'Status 200 or 302', f'Status {res.status_code}', 'Major')

    # 5.5 Audit Logs
    res = client.get('/admin/audit-logs')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/audit-logs', 'View audit logs', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/audit-logs', res.data.decode('utf-8', errors='ignore'), 'Admin Audit Logs')

    # 5.6 Action Center
    res = client.get('/admin/action-center')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/action-center', 'View Action Center', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/action-center', res.data.decode('utf-8', errors='ignore'), 'Admin Action Center')

    # 5.7 System Agents Page
    res = client.get('/admin/agents')
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/agents', 'View System Agents page', 'Status 200', f'Status {res.status_code}', 'Major')
    else:
        audit_html_elements('/admin/agents', res.data.decode('utf-8', errors='ignore'), 'Admin Agents')

    # 5.8 Admin Assistant in English & Hindi
    csrf_tok = get_csrf(client, '/admin/action-center')
    # English
    res = client.post('/admin/assistant/chat', json={'question': 'What is our current user count by role?'}, headers={'X-CSRFToken': csrf_tok})
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/assistant/chat', 'Send English question to Admin Assistant', 'Status 200 JSON with answer', f'Status {res.status_code}', 'Major')
    else:
        ans = res.get_json()
        if not ans or 'answer' not in ans:
            record_issue('Admin Journey', '/admin/assistant/chat', 'Admin Assistant English output structure', 'JSON answer object', f'Output: {ans}', 'Major')

    # Hindi
    res = client.post('/admin/assistant/chat', json={'question': 'सिस्टम में कितने शिक्षक और अभिभावक हैं?'}, headers={'X-CSRFToken': csrf_tok})
    if res.status_code != 200:
        record_issue('Admin Journey', '/admin/assistant/chat', 'Send Hindi question to Admin Assistant', 'Status 200 JSON with answer', f'Status {res.status_code}', 'Major')
    else:
        ans = res.get_json()
        if not ans or not re.search(r'[\u0900-\u097F]', ans.get('answer', '')):
            record_issue('Admin Journey', '/admin/assistant/chat', 'Admin Assistant Hindi response', 'Grounded answer in Devanagari Hindi', f'Output: {ans}', 'Major')

    # 5.9 Run Agent Scheduler Manually
    res = post_form(client, '/admin/agents/run', {}, page_for_csrf='/admin/action-center')
    if res.status_code != 200 or b'Agent pipeline executed successfully' not in res.data:
        record_issue('Admin Journey', '/admin/agents/run', 'Trigger agent pipeline execution', 'Success flash message', f'Status {res.status_code}', 'Major')

    # -------------------------------------------------------------
    # 6. Access Control & RBAC Matrix Audit
    # -------------------------------------------------------------
    print("\n--- Auditing RBAC & Access Control Matrix ---")
    admin_routes_to_test = [
        '/admin/dashboard', '/admin/users', '/admin/categories', '/admin/activities',
        '/admin/action-center', '/admin/agents', '/admin/audit-logs'
    ]

    # 6.1 Parent attempts to access admin routes
    client.get('/auth/logout')
    post_form(client, '/auth/login', {'email': demo_p.email, 'password': 'DemoPass123!'})
    for ar in admin_routes_to_test:
        res = client.get(ar)
        if res.status_code != 403:
            record_issue('Access Control', ar, f'Parent requests admin page {ar}', 'Status 403 Forbidden', f'Status {res.status_code}', 'Critical')

    # 6.2 Parent attempts to access another parent's child
    other_child = Child.query.filter(Child.parent_id != demo_p.id).first()
    if other_child:
        res = client.get(f'/parent/children/{other_child.id}/edit')
        if res.status_code != 403:
            record_issue('Access Control', f'/parent/children/{other_child.id}/edit', 'Parent accesses another parent child edit page', 'Status 403 Forbidden', f'Status {res.status_code}', 'Critical')

    # 6.3 Teacher attempts to access admin routes
    client.get('/auth/logout')
    post_form(client, '/auth/login', {'email': teacher_user.email, 'password': 'DemoPass123!'})
    for ar in admin_routes_to_test:
        res = client.get(ar)
        if res.status_code != 403:
            record_issue('Access Control', ar, f'Teacher requests admin page {ar}', 'Status 403 Forbidden', f'Status {res.status_code}', 'Critical')

    # 6.4 Teacher attempts to access unassigned student
    accessible_ids = [c.id for c in _get_accessible_children_for_teacher(teacher_user.id)]
    unassigned = Child.query.filter(~Child.id.in_(accessible_ids)).first()
    if unassigned:
        res = client.get(f'/teacher/students/{unassigned.id}')
        if res.status_code != 403:
            record_issue('Access Control', f'/teacher/students/{unassigned.id}', 'Teacher accesses unassigned student report', 'Status 403 Forbidden', f'Status {res.status_code}', 'Critical')

    # 6.5 Unauthenticated visitor attempting to access protected routes
    client.get('/auth/logout')
    protected_routes = ['/parent/dashboard', '/teacher/dashboard', '/admin/dashboard', f'/child/{en_child.id}/activities']
    for pr in protected_routes:
        res = client.get(pr)
        if res.status_code != 302 or '/login' not in res.headers.get('Location', ''):
            record_issue('Access Control', pr, f'Unauthenticated visitor requests {pr}', '302 redirect to login', f'Status {res.status_code}, loc: {res.headers.get("Location")}', 'Critical')

print(f"\n==========================================")
print(f"Audit Run Completed! Total issues found: {len(issues)}")
print(f"==========================================")
for idx, itm in enumerate(issues, 1):
    print(f"\n[{idx}] [{itm['severity']}] Area: {itm['area']}")
    print(f"    Page/URL: {itm['page']}")
    print(f"    Steps: {itm['steps']}")
    print(f"    Expected: {itm['expected']}")
    print(f"    Actual: {itm['actual']}")
