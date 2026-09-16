import unittest
import re
from html.parser import HTMLParser
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.models.content_suggestion import ContentSuggestion
from app.utils.seed_data import seed_activities
from app.services import audit_service


class HTMLCollector(HTMLParser):
    """Stack-aware HTML parser collecting anchors, buttons, and headings with nested elements."""
    def __init__(self):
        super().__init__()
        self.anchors = []  # list of (href, text)
        self.buttons = []  # list of (type, text)
        self.h1_tags = []  # list of text
        self._tag_stack = []
        self._anchor_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._tag_stack.append((tag, attrs_dict, []))
        if tag == 'a':
            self._anchor_stack.append((attrs_dict.get('href', ''), []))

    def handle_data(self, data):
        for _, _, text_parts in self._tag_stack:
            text_parts.append(data)
        for _, text_parts in self._anchor_stack:
            text_parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self._anchor_stack:
            href, text_parts = self._anchor_stack.pop()
            self.anchors.append((href, ''.join(text_parts).strip()))
        if self._tag_stack:
            t, attrs, text_parts = self._tag_stack.pop()
            text = ''.join(text_parts).strip()
            if t == 'button':
                self.buttons.append((attrs.get('type', ''), text))
            elif t == 'h1':
                self.h1_tags.append(text)


class ChildUIFixesTestCase(unittest.TestCase):
    """Automated tests verifying landing page heading cleanup, category button links, and child screen back navigation."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed categories and sample activities
        seed_activities()

        # Create parent user with two children
        self.parent = User(name='Test Parent', email='parent@example.com', role='parent')
        self.parent.set_password('DemoPass123!')
        db.session.add(self.parent)
        db.session.commit()

        self.child1 = Child(parent_id=self.parent.id, name='Lily', age=6, grade='1st Grade')
        self.child2 = Child(parent_id=self.parent.id, name='Sam', age=8, grade='2nd Grade')
        db.session.add_all([self.child1, self.child2])
        db.session.commit()

        # Create admin user
        self.admin = User(name='Admin User', email='admin@example.com', role='admin')
        self.admin.set_password('DemoPass123!')
        db.session.add(self.admin)
        db.session.commit()

        self.visual_cat = Category.query.filter_by(slug='visual').first()
        self.activity = Activity.query.filter_by(category_id=self.visual_cat.id).first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login_parent(self):
        return self.client.post('/login', data={
            'email': 'parent@example.com',
            'password': 'DemoPass123!'
        }, follow_redirects=True)

    def _login_admin(self):
        return self.client.post('/login', data={
            'email': 'admin@example.com',
            'password': 'DemoPass123!'
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # Bug 1: Landing page hero section single clean heading
    # -------------------------------------------------------------------------
    def test_landing_page_renders_single_clean_heading_without_duplicates(self):
        """Landing page must render exactly one clean <h1> heading with ChildInsight, no duplicate headings or ghost text."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')

        # Check for exactly one <h1> tag in raw HTML using regex
        h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        self.assertEqual(len(h1_matches), 1, f"Expected exactly 1 <h1> tag on landing page, found {len(h1_matches)}")

        # Strip inner HTML tags from h1 content
        h1_text = re.sub(r'<[^>]+>', '', h1_matches[0]).strip()
        self.assertEqual(h1_text, 'ChildInsight')

        # Verify tagline is in the subtitle paragraph, not in the h1 heading
        self.assertIn('class="hero-subtitle"', html)
        self.assertIn('Intelligent Learning', html)
        self.assertNotIn('Intelligent Learning', h1_matches[0])

        # Verify hero-title has proper CSS classes and no duplicate ghost elements
        self.assertIn('class="hero-title"', html)
        self.assertIn('class="hero-highlight"', html)

    # -------------------------------------------------------------------------
    # Bug 2: Child home category buttons produce working navigation link/href
    # -------------------------------------------------------------------------
    def test_unauthenticated_child_home_category_buttons_have_working_href(self):
        """On /child/home, category buttons must be interactive <a> tags with working hrefs, not dummy buttons."""
        res = self.client.get('/child/home')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        # Find category buttons by label
        category_button_labels = ['Visual Puzzles', 'Logic & Patterns', 'Numbers & Shapes']
        found_links = []
        for label in category_button_labels:
            matched_anchors = [href for href, text in parser.anchors if label in text]
            self.assertGreaterEqual(
                len(matched_anchors), 1,
                f"Expected an <a> tag with label containing '{label}' on /child/home"
            )
            self.assertTrue(bool(matched_anchors[0]), f"Expected '{label}' link to have non-empty href")
            found_links.append(matched_anchors[0])

            # Ensure no dummy <button> elements exist for this category
            matched_buttons = [text for btype, text in parser.buttons if label in text]
            self.assertEqual(
                len(matched_buttons), 0,
                f"Found dummy <button> tag for '{label}' on /child/home — must be interactive <a> link"
            )

        self.assertEqual(len(found_links), 3)

    def test_authenticated_child_home_category_buttons_have_working_href(self):
        """When child is selected, category cards must be working links pointing to activity lists."""
        self._login_parent()
        res = self.client.get(f'/child/{self.child1.id}/activities')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        category_links = [href for href, text in parser.anchors if f'/child/{self.child1.id}/category/' in href]
        self.assertGreaterEqual(len(category_links), 3, "Expected at least 3 category links pointing to category activity lists")

    # -------------------------------------------------------------------------
    # Bug 3: Every child-facing screen has clear back navigation
    # -------------------------------------------------------------------------
    def test_child_home_has_back_navigation(self):
        """Unauthenticated /child/home screen has a clear back navigation option."""
        res = self.client.get('/child/home')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        back_links = [href for href, text in parser.anchors if 'back' in text.lower()]
        self.assertGreaterEqual(len(back_links), 1, "Expected a Back navigation link on /child/home")
        self.assertTrue(bool(back_links[0]))

    def test_select_child_screen_has_back_navigation(self):
        """Parent multi-child picker (/child/home) has a clear Back to Parent Dashboard option."""
        self._login_parent()
        res = self.client.get('/child/home')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        back_links = [href for href, text in parser.anchors if 'parent dashboard' in text.lower()]
        self.assertGreaterEqual(len(back_links), 1, "Expected 'Back to Parent Dashboard' link on /child/select_child")
        self.assertTrue(any('/parent/dashboard' in href for href in back_links))

    def test_activities_hub_screen_has_back_navigation(self):
        """Categories hub (/child/<id>/activities) has exactly ONE Back navigation option (no duplicate bottom button)."""
        self._login_parent()
        res = self.client.get(f'/child/{self.child1.id}/activities')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        back_links = [href for href, text in parser.anchors if 'back' in text.lower()]
        self.assertEqual(len(back_links), 1, "Expected exactly ONE Back navigation link on categories hub")
        self.assertTrue(any('/parent/dashboard' in href for href in back_links))

    def test_activity_list_screen_has_back_navigation(self):
        """Activity list (/child/<id>/category/<cat_id>) has exactly ONE Back to Categories link (no duplicate bottom or empty-state buttons)."""
        self._login_parent()
        # 1. Populated category
        res = self.client.get(f'/child/{self.child1.id}/category/{self.visual_cat.id}')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        back_links = [href for href, text in parser.anchors if 'back to categories' in text.lower()]
        self.assertEqual(len(back_links), 1, "Expected exactly ONE 'Back to Categories' link on populated activity list screen")
        self.assertTrue(any(f'/child/{self.child1.id}/activities' in href for href in back_links))

        # 2. Empty-state category (e.g. category with no activities for this age)
        empty_cat = Category(name="Empty Science", icon="🔬", slug="empty-sci")
        db.session.add(empty_cat)
        db.session.commit()

        res_empty = self.client.get(f'/child/{self.child1.id}/category/{empty_cat.id}')
        self.assertEqual(res_empty.status_code, 200)

        parser_empty = HTMLCollector()
        parser_empty.feed(res_empty.data.decode('utf-8'))
        empty_back_links = [href for href, text in parser_empty.anchors if 'back to categories' in text.lower()]
        self.assertEqual(len(empty_back_links), 1, "Expected exactly ONE 'Back to Categories' link on empty-state activity list screen")
        self.assertTrue(any(f'/child/{self.child1.id}/activities' in href for href in empty_back_links))

    def test_player_screen_has_back_navigation(self):
        """Player screen (/child/<id>/play/<act_id>) has clear Back to Activities navigation."""
        self._login_parent()
        res = self.client.get(f'/child/{self.child1.id}/play/{self.activity.id}')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        back_links = [href for href, text in parser.anchors if 'back to activities' in text.lower()]
        self.assertGreaterEqual(len(back_links), 1, "Expected 'Back to Activities' link on player screen")
        self.assertTrue(any(f'/child/{self.child1.id}/play/{self.activity.id}/abandon' in href for href in back_links))

    def test_results_screen_has_back_navigation(self):
        """Results screen (/child/<id>/play/<act_id>/results) has clear Back to Categories navigation."""
        self._login_parent()
        # Create a completed session so results page renders cleanly
        act_session = ActivitySession(
            child_id=self.child1.id,
            activity_id=self.activity.id,
            status='completed',
            attempts=3,
            correct_answers=3,
            accuracy=100.0,
            duration_seconds=45
        )
        db.session.add(act_session)
        db.session.commit()

        res = self.client.get(f'/child/{self.child1.id}/play/{self.activity.id}/results')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        parser = HTMLCollector()
        parser.feed(html)

        back_links = [href for href, text in parser.anchors if 'back to categories' in text.lower()]
        self.assertGreaterEqual(len(back_links), 1, "Expected 'Back to Categories' link on results screen")
        self.assertTrue(any(f'/child/{self.child1.id}/activities' in href for href in back_links))

    # -------------------------------------------------------------------------
    # Bug: Answer Option Randomization & Scoring Verification
    # -------------------------------------------------------------------------
    def test_question_options_shuffled_on_render(self):
        """Answer options must be shuffled on render so correct answer is NOT always in the first position."""
        self._login_parent()
        q = self.activity.questions.order_by(ActivityQuestion.order_num).first()
        self.assertIsNotNone(q)
        self.assertGreaterEqual(len(q.options), 3, "Test requires a question with at least 3 options")

        stored_options_before = list(q.options)
        stored_json_before = q.options_json

        positions = []
        for _ in range(15):
            res = self.client.get(f'/child/{self.child1.id}/play/{self.activity.id}?q=0')
            self.assertEqual(res.status_code, 200)

            html = res.data.decode('utf-8')
            # Extract option button values in visual display order
            rendered_options = re.findall(
                r'<button[^>]*name="selected_answer"[^>]*value="([^"]+)"',
                html,
                re.IGNORECASE
            )
            self.assertEqual(
                len(rendered_options), len(q.options),
                "Every render must display all available question options"
            )
            self.assertEqual(
                set(rendered_options), set(q.options),
                "Rendered options must contain the exact same choices as the question"
            )

            # Find the 0-indexed position of the correct answer in the rendered choices
            correct_pos = rendered_options.index(q.correct_answer)
            positions.append(correct_pos)

        # Confirm the correct answer is NOT always at index 0 (first position)
        unique_positions = set(positions)
        self.assertGreater(
            len(unique_positions), 1,
            f"Expected correct answer to appear in multiple distinct visual positions across 15 renders, got: {positions}"
        )

        # Confirm database storage was not mutated by shuffling
        db.session.refresh(q)
        self.assertEqual(q.options, stored_options_before, "Underlying question.options must remain unchanged in database")
        self.assertEqual(q.options_json, stored_json_before, "Underlying question.options_json must not be mutated")

    def test_scoring_evaluates_correctly_regardless_of_shuffled_position(self):
        """Scoring must evaluate accurately regardless of which visual position the option was rendered in."""
        self._login_parent()
        q = self.activity.questions.order_by(ActivityQuestion.order_num).first()

        # 1. Test correct answer submission
        res = self.client.post(
            f'/child/{self.child1.id}/play/{self.activity.id}/answer',
            data={
                'question_id': q.id,
                'selected_answer': q.correct_answer,
                'q_idx': 0
            }
        )
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Great job!", html)

        # 2. Test incorrect answer submission
        wrong_option = [opt for opt in q.options if opt.strip().lower() != q.correct_answer.strip().lower()][0]
        res_wrong = self.client.post(
            f'/child/{self.child1.id}/play/{self.activity.id}/answer',
            data={
                'question_id': q.id,
                'selected_answer': wrong_option,
                'q_idx': 0
            }
        )
        self.assertEqual(res_wrong.status_code, 200)
        html_wrong = res_wrong.data.decode('utf-8')
        self.assertIn("Good try!", html_wrong)
        self.assertIn(q.correct_answer, html_wrong)

    # -------------------------------------------------------------------------
    # Bug 3: Admin Badge & Pill High Contrast and Action Differentiation
    # -------------------------------------------------------------------------
    def test_admin_badge_contrast_palette_and_audit_log_badges(self):
        """Admin audit log action badges must have strong contrast and be visually distinct per action type."""
        # 1. Verify mathematical contrast ratios for all defined badge variants
        def luminance(r, g, b):
            def channel(c):
                c = c / 255.0
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

        def hex_to_rgb(hex_str):
            hex_str = hex_str.lstrip('#')
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

        def blend(fg_rgb, alpha, bg_rgb):
            return tuple(int(fg_rgb[i] * alpha + bg_rgb[i] * (1 - alpha)) for i in range(3))

        def contrast_ratio(c1, c2):
            l1, l2 = luminance(*c1), luminance(*c2)
            if l1 < l2:
                l1, l2 = l2, l1
            return (l1 + 0.05) / (l2 + 0.05)

        palette = {
            "create/success (light)": ("#14532D", hex_to_rgb("#DCFCE7")),
            "create/success (dark)": ("#6EE7B7", blend(hex_to_rgb("#10B981"), 0.2, hex_to_rgb("#1E293B"))),
            "update/warning (light)": ("#78350F", hex_to_rgb("#FEF3C7")),
            "update/warning (dark)": ("#FDE68A", blend(hex_to_rgb("#F59E0B"), 0.2, hex_to_rgb("#1E293B"))),
            "delete/danger (light)": ("#7F1D1D", hex_to_rgb("#FEE2E2")),
            "delete/danger (dark)": ("#FECACA", blend(hex_to_rgb("#EF4444"), 0.2, hex_to_rgb("#1E293B"))),
            "run/pipeline (light)": ("#4C1D95", hex_to_rgb("#EDE9FE")),
            "run/pipeline (dark)": ("#DDD6FE", blend(hex_to_rgb("#8B5CF6"), 0.2, hex_to_rgb("#1E293B"))),
            "reset/amber (light)": ("#78350F", hex_to_rgb("#FEF3C7")),
            "reset/amber (dark)": ("#FDE68A", blend(hex_to_rgb("#F59E0B"), 0.25, hex_to_rgb("#1E293B"))),
            "assign/sky (light)": ("#075985", hex_to_rgb("#E0F2FE")),
            "assign/sky (dark)": ("#7DD3FC", blend(hex_to_rgb("#0EA5E9"), 0.2, hex_to_rgb("#1E293B"))),
            "neutral/default (light)": ("#1E293B", hex_to_rgb("#F1F5F9")),
            "neutral/default (dark)": ("#F8FAFC", hex_to_rgb("#334155")),
            "primary/info (light)": ("#1E40AF", hex_to_rgb("#EFF6FF")),
            "primary/info (dark)": ("#93C5FD", blend(hex_to_rgb("#3B82F6"), 0.2, hex_to_rgb("#1E293B"))),
        }

        for variant_name, (fg, bg) in palette.items():
            fg_rgb = hex_to_rgb(fg) if isinstance(fg, str) else fg
            ratio = contrast_ratio(fg_rgb, bg)
            self.assertGreaterEqual(
                ratio, 4.5,
                f"Badge variant {variant_name} has contrast ratio {ratio:.2f}:1, which is below the WCAG AA minimum 4.5:1"
            )

        # 2. Log multiple distinct action types in the database
        audit_service.log_action(user_id=self.admin.id, action='RUN_AGENTS_PIPELINE', target_type='system')
        audit_service.log_action(user_id=self.admin.id, action='PASSWORD_RESET_COMPLETED', target_type='user', target_id='1')
        audit_service.log_action(user_id=self.admin.id, action='ADD_ACTIVITY', target_type='activity', target_id='101')
        audit_service.log_action(user_id=self.admin.id, action='UPDATE_ACTIVITY', target_type='activity', target_id='101')
        audit_service.log_action(user_id=self.admin.id, action='DELETE_ACTIVITY', target_type='activity', target_id='101')
        audit_service.log_action(user_id=self.admin.id, action='ASSIGN_ACTIVITY', target_type='assignment', target_id='1')
        audit_service.log_action(user_id=self.admin.id, action='UPDATE_USER_ROLE', target_type='user', target_id='2')

        # 3. Log in as admin and render /admin/audit-logs
        self._login_admin()
        res = self.client.get('/admin/audit-logs')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Assert specific semantic badge classes are rendered for each action type
        self.assertIn('badge-run', html, "RUN_AGENTS_PIPELINE should be styled with badge-run")
        self.assertIn('badge-reset', html, "PASSWORD_RESET_COMPLETED should be styled with badge-reset")
        self.assertIn('badge-create', html, "ADD_ACTIVITY should be styled with badge-create")
        self.assertIn('badge-update', html, "UPDATE_ACTIVITY should be styled with badge-update")
        self.assertIn('badge-delete', html, "DELETE_ACTIVITY should be styled with badge-delete")
        self.assertIn('badge-assign', html, "ASSIGN_ACTIVITY should be styled with badge-assign")
        self.assertIn('badge-purple', html, "UPDATE_USER_ROLE should be styled with badge-purple")
        self.assertIn('badge-neutral', html, "Entries count should be styled with badge-neutral")

        # Confirm old low-contrast inline styling is completely removed
        self.assertNotIn('background: #F3F4F6; color: var(--color-text-main);', html)
        self.assertNotIn('background: #F3F4F6; color: var(--color-text-muted);', html)

    def test_other_admin_pages_badge_contrast(self):
        """Admin category, activity, and content suggestion pages must use consistent high-contrast badges."""
        self._login_admin()

        # 1. Check Categories page
        res_cat = self.client.get('/admin/categories')
        self.assertEqual(res_cat.status_code, 200)
        html_cat = res_cat.data.decode('utf-8')
        self.assertIn('badge-primary', html_cat)

        # 2. Check Activities list page
        res_act = self.client.get('/admin/activities')
        self.assertEqual(res_act.status_code, 200)
        html_act = res_act.data.decode('utf-8')
        self.assertIn('badge-sky', html_act)
        self.assertIn('badge-success', html_act)
        self.assertIn('badge-neutral', html_act)

        # 3. Check Content Suggestions page
        sugg = ContentSuggestion(
            suggestion_type='progression_gap',
            category_id=self.visual_cat.id,
            age_band='6-9',
            target_difficulty='Medium',
            suggested_title='Pattern Master Level 2',
            reason='Learners are succeeding at Beginner with 90% accuracy.',
            status='pending'
        )
        db.session.add(sugg)
        db.session.commit()

        res_sugg = self.client.get('/admin/content-suggestions')
        self.assertEqual(res_sugg.status_code, 200)
        html_sugg = res_sugg.data.decode('utf-8')
        self.assertIn('badge-warning', html_sugg)
        self.assertIn('badge-neutral', html_sugg)
        # Verify no low-contrast inline colors like #D97706 or broken var(--color-background)
        self.assertNotIn('color: #D97706;', html_sugg)
        self.assertNotIn('var(--color-background)', html_sugg)


if __name__ == '__main__':
    unittest.main()
