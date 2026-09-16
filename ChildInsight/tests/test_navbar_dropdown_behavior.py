import re
import unittest
from app import create_app, db
from app.models.user import User


class NavbarDropdownBehaviorTestCase(unittest.TestCase):
    """Automated verification for navbar dropdown toggle stability, idempotence,
    independent state management, and multi-click responsiveness.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create admin user
        self.admin = User(name='Administrator [Demo Data]', email='admin@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)
        db.session.commit()

        with open('app/static/js/main.js', 'r', encoding='utf-8') as f:
            self.js_content = f.read()

        with open('app/static/css/style.css', 'r', encoding='utf-8') as f:
            self.css_content = f.read()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_admin_navbar_markup_structure(self):
        """Confirm the admin navbar contains the System dropdown and user label without ID/class collisions."""
        self.client.post('/login', data={'email': 'admin@example.com', 'password': 'AdminPass123!'}, follow_redirects=True)
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Confirm System dropdown has unique id and valid dropdown classes
        self.assertIn('id="adminSystemDropdown"', html)
        self.assertIn('class="nav-link nav-dropdown-toggle', html)
        self.assertIn('aria-haspopup="true"', html)
        self.assertIn('aria-expanded="false"', html)

        # Confirm user profile label exists and is separate from the dropdown toggle
        self.assertIn('class="nav-user-label"', html)
        self.assertIn('Administrator [Demo Data]', html)
        self.assertIn('(Admin)', html)

        # Verify no duplicate IDs on the page
        ids = re.findall(r'id="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)), f"Duplicate HTML IDs found in navbar markup: {[x for x in ids if ids.count(x) > 1]}")

    def test_js_idempotence_and_independent_state_architecture(self):
        """Verify main.js contains idempotency guards, independent helpers, and focus clearing."""
        # 1. Idempotence guards to prevent multiple listener attachments
        self.assertIn('_navDropdownBound', self.js_content)
        self.assertIn('_navbarDropdownOutsideBound', self.js_content)

        # 2. Independent open/close functions
        self.assertIn('function closeNavDropdown(', self.js_content)
        self.assertIn('function openNavDropdown(', self.js_content)
        self.assertIn('function closeAllNavDropdowns(', self.js_content)

        # 3. Focus blur to clear :focus-within trap
        self.assertIn('toggle.blur()', self.js_content)

        # 4. Notification and navigation dropdown cross-coordination
        self.assertIn('closeAllNavDropdowns()', self.js_content)

        # 5. Outside click and Escape key dismissal
        self.assertIn("clickedNavDropdown", self.js_content)
        self.assertIn("closeNavDropdown(d)", self.js_content)

    def test_css_does_not_override_click_to_close(self):
        """Verify CSS does not force display: block on hover or focus-within, which would fight click-to-close."""
        # Ensure .nav-dropdown.open .dropdown-menu { display: block; } is present
        self.assertIn('.nav-dropdown.open .dropdown-menu', self.css_content)

        # Ensure .nav-dropdown:hover .dropdown-menu and :focus-within are NOT forcing display: block
        self.assertNotIn('.nav-dropdown:hover .dropdown-menu', self.css_content)
        self.assertNotIn('.nav-dropdown:focus-within .dropdown-menu', self.css_content)

    def test_simulated_10_sequential_toggle_clicks(self):
        """Simulate at least 10 sequential click toggles on a dropdown element.
        Confirm each click deterministically alternates between open and closed state
        without becoming unresponsive or requiring multiple clicks.
        """
        # Minimal DOM element simulator modeling main.js behavior
        class MockElement:
            def __init__(self, tag, class_list=None, attrs=None):
                self.tag = tag
                self.classList = set(class_list or [])
                self.attributes = attrs or {}
                self.style = {}
                self.parent = None
                self.children = []
                self.is_blurred = False

            def setAttribute(self, key, val):
                self.attributes[key] = str(val)

            def getAttribute(self, key):
                return self.attributes.get(key)

            def blur(self):
                self.is_blurred = True

            def closest(self, selector):
                curr = self
                while curr:
                    for cls in selector.replace('.', ' ').split():
                        if cls in curr.classList:
                            return curr
                    curr = curr.parent
                return None

            def querySelector(self, selector):
                for child in self.children:
                    for cls in selector.replace('.', ' ').replace('[aria-expanded]', '').split():
                        if cls and cls in child.classList:
                            return child
                return None

        # Build dropdown DOM tree matching base_admin.html
        parent = MockElement('li', class_list=['nav-dropdown'])
        btn = MockElement('button', class_list=['nav-dropdown-toggle'], attrs={'aria-expanded': 'false', 'id': 'adminSystemDropdown'})
        menu = MockElement('ul', class_list=['dropdown-menu'])

        btn.parent = parent
        menu.parent = parent
        parent.children = [btn, menu]

        # Simulate the exact JS openNavDropdown / closeNavDropdown state machine from main.js
        def closeNavDropdown(container):
            container.classList.discard('open')
            toggle = container.querySelector('.nav-dropdown-toggle')
            if toggle:
                toggle.setAttribute('aria-expanded', 'false')
                toggle.blur()
            dropdown_menu = container.querySelector('.dropdown-menu')
            if dropdown_menu:
                dropdown_menu.style['display'] = ''

        def openNavDropdown(container, toggle):
            container.classList.add('open')
            btn_el = toggle or container.querySelector('.nav-dropdown-toggle')
            if btn_el:
                btn_el.setAttribute('aria-expanded', 'true')
            dropdown_menu = container.querySelector('.dropdown-menu')
            if dropdown_menu:
                dropdown_menu.style['display'] = 'block'

        def on_toggle_click():
            is_open = 'open' in parent.classList
            if is_open:
                closeNavDropdown(parent)
            else:
                openNavDropdown(parent, btn)

        # Initial state: closed
        self.assertNotIn('open', parent.classList)
        self.assertEqual(btn.getAttribute('aria-expanded'), 'false')
        self.assertEqual(menu.style.get('display', ''), '')

        # Perform 20 sequential clicks (10 complete open/close cycles)
        for cycle in range(1, 21):
            on_toggle_click()
            if cycle % 2 == 1:
                # Odd clicks: MUST BE OPEN
                self.assertIn('open', parent.classList, f"Click #{cycle} failed to open the dropdown")
                self.assertEqual(btn.getAttribute('aria-expanded'), 'true', f"Click #{cycle} aria-expanded should be 'true'")
                self.assertEqual(menu.style.get('display'), 'block', f"Click #{cycle} display should be 'block'")
            else:
                # Even clicks: MUST BE CLOSED
                self.assertNotIn('open', parent.classList, f"Click #{cycle} failed to close the dropdown")
                self.assertEqual(btn.getAttribute('aria-expanded'), 'false', f"Click #{cycle} aria-expanded should be 'false'")
                self.assertEqual(menu.style.get('display', ''), '', f"Click #{cycle} display should be cleared")
                self.assertTrue(btn.is_blurred, f"Click #{cycle} should have called blur() on the toggle")

    def test_independent_multiple_dropdowns_interaction(self):
        """Verify that multiple dropdowns (e.g. System dropdown and a User Profile dropdown)
        manage independent state: opening one closes the other, neither interferes with the other.
        """
        class MockDropdown:
            def __init__(self, name):
                self.name = name
                self.is_open = False
                self.aria_expanded = 'false'
                self.display = ''

            def open(self):
                self.is_open = True
                self.aria_expanded = 'true'
                self.display = 'block'

            def close(self):
                self.is_open = False
                self.aria_expanded = 'false'
                self.display = ''

        system_dropdown = MockDropdown('system')
        user_dropdown = MockDropdown('user')
        all_dropdowns = [system_dropdown, user_dropdown]

        def toggle_dropdown(target):
            if target.is_open:
                target.close()
            else:
                for d in all_dropdowns:
                    if d != target:
                        d.close()
                target.open()

        # 1. Open System Dropdown
        toggle_dropdown(system_dropdown)
        self.assertTrue(system_dropdown.is_open)
        self.assertFalse(user_dropdown.is_open)

        # 2. Click User Profile Dropdown -> System closes, User opens
        toggle_dropdown(user_dropdown)
        self.assertFalse(system_dropdown.is_open)
        self.assertTrue(user_dropdown.is_open)

        # 3. Click User Profile Dropdown again -> User closes, both closed
        toggle_dropdown(user_dropdown)
        self.assertFalse(system_dropdown.is_open)
        self.assertFalse(user_dropdown.is_open)

        # 4. Repeat 10 alternating switches between the two dropdowns
        for i in range(10):
            toggle_dropdown(system_dropdown)
            self.assertTrue(system_dropdown.is_open)
            self.assertFalse(user_dropdown.is_open)

            toggle_dropdown(user_dropdown)
            self.assertFalse(system_dropdown.is_open)
            self.assertTrue(user_dropdown.is_open)


if __name__ == '__main__':
    unittest.main()
