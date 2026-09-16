import unittest
from html.parser import HTMLParser
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.utils.seed_data import seed_activities


class HTMLCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []  # list of (href, text)
        self._current_href = None
        self._current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get('href', '')
            self._current_text = []

    def handle_endtag(self, tag):
        if tag == 'a' and self._current_href is not None:
            text = ' '.join(''.join(self._current_text).split())
            self.anchors.append((self._current_href, text))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_entityref(self, name):
        if self._current_href is not None:
            if name == 'larr':
                self._current_text.append('←')
            elif name == 'rarr':
                self._current_text.append('→')


class ChildNavAndProfileEditTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        seed_activities()

        # Create parent user with children
        self.parent = User(name='Farhan Parent', email='farhan.parent@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)
        db.session.commit()

        # Child 1: afzal (demonstrates adolescent age & higher grade)
        self.child_afzal = Child(parent_id=self.parent.id, name='afzal', age=14, grade='2nd Grade', preferred_language='English')
        # Child 2: sara (gives parent multiple children to test select_child screen)
        self.child_sara = Child(parent_id=self.parent.id, name='sara', age=7, grade='2nd Grade', preferred_language='English')
        db.session.add_all([self.child_afzal, self.child_sara])
        db.session.commit()

        # Existing category with activities
        self.cat = Category.query.first()
        self.activity = Activity.query.filter_by(category_id=self.cat.id, is_active=True).first()

        # Empty category (0 activities)
        self.empty_cat = Category(name="Empty Explorer", icon="🔭", slug="empty-explorer")
        db.session.add(self.empty_cat)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login_parent(self):
        return self.client.post('/auth/login', data={
            'email': 'farhan.parent@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. No Screen Has Duplicate Back-Navigation Buttons for Same Destination
    # -------------------------------------------------------------------------
    def test_no_screen_has_duplicate_back_navigation_for_same_destination(self):
        """
        Audit all child-facing screens and ensure that NO screen renders duplicate/redundant
        back-navigation buttons pointing to the same destination URL.
        """
        self._login_parent()

        # Complete a session so results page renders cleanly
        act_session = ActivitySession(
            child_id=self.child_afzal.id,
            activity_id=self.activity.id,
            status='completed',
            attempts=3,
            correct_answers=3,
            accuracy=100.0,
            duration_seconds=40
        )
        db.session.add(act_session)
        db.session.commit()

        screens_to_test = [
            ("Select Child Picker", '/child/home'),
            ("Categories Hub", f'/child/{self.child_afzal.id}/activities'),
            ("Populated Activity List", f'/child/{self.child_afzal.id}/category/{self.cat.id}'),
            ("Empty-State Activity List", f'/child/{self.child_afzal.id}/category/{self.empty_cat.id}'),
            ("Activity Player", f'/child/{self.child_afzal.id}/play/{self.activity.id}'),
            ("Activity Results", f'/child/{self.child_afzal.id}/play/{self.activity.id}/results')
        ]

        for screen_name, url in screens_to_test:
            with self.subTest(screen=screen_name):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Failed to load {screen_name} at {url}")

                html = res.data.decode('utf-8')
                parser = HTMLCollector()
                parser.feed(html)

                # Identify all back-navigation links:
                # Text contains 'back', '←', or '&larr;'
                back_links = [
                    (href, text) for href, text in parser.anchors
                    if 'back' in text.lower() or '←' in text or 'larr' in text.lower()
                ]

                # Group by destination href
                href_counts = {}
                for href, text in back_links:
                    href_counts[href] = href_counts.get(href, 0) + 1

                # Confirm NO destination appears more than once as a back link
                for href, count in href_counts.items():
                    self.assertEqual(
                        count, 1,
                        f"Screen '{screen_name}' ({url}) has {count} duplicate back navigation links pointing to '{href}'! Back links found: {back_links}"
                    )

    def test_activity_list_empty_and_populated_has_single_top_back_button(self):
        """Confirm both populated and empty-state activity lists have only 1 Back to Categories button at top."""
        self._login_parent()

        # Populated
        res_pop = self.client.get(f'/child/{self.child_afzal.id}/category/{self.cat.id}')
        parser_pop = HTMLCollector()
        parser_pop.feed(res_pop.data.decode('utf-8'))
        pop_back = [href for href, text in parser_pop.anchors if 'back to categories' in text.lower()]
        self.assertEqual(len(pop_back), 1, "Populated activity list must have exactly one 'Back to Categories' link")

        # Empty
        res_empty = self.client.get(f'/child/{self.child_afzal.id}/category/{self.empty_cat.id}')
        parser_empty = HTMLCollector()
        parser_empty.feed(res_empty.data.decode('utf-8'))
        empty_back = [href for href, text in parser_empty.anchors if 'back to categories' in text.lower()]
        self.assertEqual(len(empty_back), 1, "Empty activity list must have exactly one 'Back to Categories' link")

    # -------------------------------------------------------------------------
    # 2. Child Profile Edit: Persistence, Age & Grade Saving, and Display
    # -------------------------------------------------------------------------
    def test_edit_child_profile_persists_changes_and_displays_correctly(self):
        """
        Verify editing a child profile (e.g. afzal's Learning Journey) saves updated age and grade,
        persists to the database, and displays correctly on the child detail page.
        """
        self._login_parent()
        child_id = self.child_afzal.id

        # 1. GET child edit page
        get_res = self.client.get(f'/parent/children/{child_id}/edit')
        self.assertEqual(get_res.status_code, 200)
        get_html = get_res.data.decode('utf-8')
        self.assertIn('Edit afzal&#39;s Profile', get_html)

        # 2. Submit updated age=15 and grade='8th Grade'
        post_res = self.client.post(f'/parent/children/{child_id}/edit', data={
            'name': 'afzal',
            'age': '15',
            'grade': '8th Grade',
            'preferred_language': 'English'
        }, follow_redirects=True)

        self.assertEqual(post_res.status_code, 200)
        # Should redirect to child detail page
        self.assertEqual(post_res.request.path, f'/parent/children/{child_id}')

        # 3. Verify changes persist to the database
        db.session.expire_all()
        updated_child = db.session.get(Child, child_id)
        self.assertEqual(updated_child.age, 15, "Child age must persist to database")
        self.assertEqual(updated_child.grade, '8th Grade', "Child grade must persist to database")

        # 4. Verify new values display correctly on the child detail page
        detail_html = post_res.data.decode('utf-8')
        self.assertIn('15 years old', detail_html)
        self.assertIn('8th Grade', detail_html)
        self.assertIn('Profile for afzal updated.', detail_html)

    def test_edit_child_profile_cancel_button_returns_to_child_detail(self):
        """Confirm Cancel button on edit form returns to the child detail page."""
        self._login_parent()
        res = self.client.get(f'/parent/children/{self.child_afzal.id}/edit')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        cancel_links = [href for href, text in parser.anchors if text.strip() == 'Cancel']
        self.assertEqual(len(cancel_links), 1)
        self.assertEqual(cancel_links[0], f'/parent/children/{self.child_afzal.id}')

    def test_edit_child_profile_supports_secondary_and_high_school_grades(self):
        """Confirm 7th through 12th Grade save cleanly without validation errors."""
        self._login_parent()
        child_id = self.child_afzal.id

        test_grades = ['7th Grade', '8th Grade', '9th Grade', '10th Grade', '11th Grade', '12th Grade']
        for g in test_grades:
            with self.subTest(grade=g):
                post_res = self.client.post(f'/parent/children/{child_id}/edit', data={
                    'name': 'afzal',
                    'age': '16',
                    'grade': g,
                    'preferred_language': 'English'
                }, follow_redirects=True)
                self.assertEqual(post_res.status_code, 200)
                self.assertEqual(post_res.request.path, f'/parent/children/{child_id}')

                db.session.expire_all()
                c = db.session.get(Child, child_id)
                self.assertEqual(c.grade, g)


if __name__ == '__main__':
    unittest.main()
