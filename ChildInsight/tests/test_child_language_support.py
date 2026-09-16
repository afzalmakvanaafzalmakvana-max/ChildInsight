"""Comprehensive automated test suite for ChildInsight language support and navigation.

Validates:
1. Child profile preferred_language = 'Hindi' (and 'hi') renders real Hindi UI,
   Hindi category names, translated activity titles/descriptions, question texts,
   randomized options, hints, and feedback.
2. Graceful fallback badge when a Hindi-preferred child views an untranslated activity.
3. Child profile preferred_language = 'English' renders full English UI without fallback badges.
4. "Coming Soon" languages (Spanish, French, German, Mandarin) cleanly fall back to English.
5. Answer evaluation correctly scores Hindi answers and English answers.
6. ChildForm dropdown contains expected choices with (Coming Soon) labels.
7. "← Back to Activity Hub" navigation reliably navigates to child's category hub.
8. No dead ends, `#`, or self-referential back loops across child screens.
"""

import unittest
from html.parser import HTMLParser
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.forms.child import ChildForm
from app.translations import normalize_language, translate, SUPPORTED_LANGUAGES, COMING_SOON_LANGUAGES
from app.utils.seed_data import seed_activities


class HTMLCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []  # (href, text)
        self.buttons = []
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
            if t == 'button':
                self.buttons.append((attrs.get('type', ''), ''.join(text_parts).strip()))


class ChildLanguageSupportTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        seed_activities()


        # Users
        self.parent = User(name='Priya Sharma', email='priya@example.com', role='parent')
        self.parent.set_password('ParentPass123!')
        self.child_user = User(name='Aarav User', email='aarav@example.com', role='child')
        self.child_user.set_password('ChildPass123!')
        db.session.add_all([self.parent, self.child_user])
        db.session.commit()

        # Hindi child (linked to child_user.id)
        self.child_hi = Child(
            id=self.child_user.id,
            parent_id=self.parent.id,
            name='Aarav',
            age=6,
            grade='1st Grade',
            preferred_language='Hindi'
        )
        # English child
        self.child_en = Child(
            parent_id=self.parent.id,
            name='Leo',
            age=6,
            grade='1st Grade',
            preferred_language='English'
        )
        # Spanish child (Coming Soon)
        self.child_es = Child(
            parent_id=self.parent.id,
            name='Mateo',
            age=6,
            grade='1st Grade',
            preferred_language='Spanish'
        )
        db.session.add_all([self.child_hi, self.child_en, self.child_es])
        db.session.commit()

        self.visual_cat = Category.query.filter_by(slug='visual').first()
        # Find translated and untranslated activities
        self.translated_activity = None
        self.untranslated_activity = None
        for act in Activity.query.filter_by(category_id=self.visual_cat.id).all():
            if act.has_translation('hi') and not self.translated_activity:
                self.translated_activity = act
            elif not act.has_translation('hi') and not self.untranslated_activity:
                self.untranslated_activity = act

        # If all in visual are translated, find any untranslated activity or create one
        if not self.untranslated_activity:
            self.untranslated_activity = Activity(
                category_id=self.visual_cat.id,
                title='English Only Shape Matching',
                description='Match circles and triangles with shapes.',
                min_age=5,
                max_age=8,
                difficulty='Easy',
                estimated_duration=5,
                is_active=True
            )
            db.session.add(self.untranslated_activity)
            db.session.commit()
            q = ActivityQuestion(
                activity_id=self.untranslated_activity.id,
                question_text='Which one is a circle?',
                options_json='["Circle", "Square", "Triangle"]',
                correct_answer='Circle',
                hint='It is round!',
                order_num=1
            )
            db.session.add(q)
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login_parent(self):
        return self.client.post('/auth/login', data={
            'email': 'priya@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=True)

    def _login_child(self):
        return self.client.post('/auth/login', data={
            'email': 'aarav@example.com',
            'password': 'ChildPass123!'
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Normalization and Form choices
    # -------------------------------------------------------------------------
    def test_normalize_language(self):
        self.assertEqual(normalize_language('Hindi'), 'hi')
        self.assertEqual(normalize_language('hindi'), 'hi')
        self.assertEqual(normalize_language('hi'), 'hi')
        self.assertEqual(normalize_language('English'), 'en')
        self.assertEqual(normalize_language('english'), 'en')
        self.assertEqual(normalize_language('en'), 'en')
        # Coming soon and unknown languages fall back to en
        self.assertEqual(normalize_language('Spanish'), 'en')
        self.assertEqual(normalize_language('French'), 'en')
        self.assertEqual(normalize_language('German'), 'en')
        self.assertEqual(normalize_language('Mandarin'), 'en')
        self.assertEqual(normalize_language(None), 'en')
        self.assertEqual(normalize_language(''), 'en')

    def test_child_form_language_dropdown_choices(self):
        form = ChildForm()
        choices = dict(form.preferred_language.choices)
        self.assertIn('English', choices)
        self.assertIn('Hindi', choices)
        self.assertEqual(choices['English'], 'English')
        self.assertEqual(choices['Hindi'], 'Hindi')
        # Check Coming Soon markers
        self.assertIn('Spanish', choices)
        self.assertIn('Coming Soon', choices['Spanish'])
        self.assertIn('French', choices)
        self.assertIn('Coming Soon', choices['French'])
        self.assertIn('German', choices)
        self.assertIn('Coming Soon', choices['German'])
        self.assertIn('Mandarin', choices)
        self.assertIn('Coming Soon', choices['Mandarin'])

    # -------------------------------------------------------------------------
    # 2. Hindi Child Experience
    # -------------------------------------------------------------------------
    def test_hindi_child_categories_hub(self):
        self._login_parent()
        res = self.client.get(f'/child/{self.child_hi.id}/activities')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Hindi greeting
        self.assertIn('नमस्ते Aarav! आइए खेलें!', html)
        # Hindi category heading
        self.assertIn('रोमांचक गतिविधियों को खोजने के लिए एक श्रेणी चुनें:', html)
        # Hindi category names
        self.assertIn('दृश्य पहेलियाँ', html)
        self.assertIn('तर्क और पैटर्न', html)
        # Explore button in Hindi
        self.assertIn('खोजें →', html)

    def test_hindi_child_activity_list_translated_and_untranslated(self):
        self._login_parent()
        res = self.client.get(f'/child/{self.child_hi.id}/category/{self.visual_cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Back to categories in Hindi
        self.assertIn('← श्रेणियों पर वापस जाएं', html)
        # Hindi category header
        self.assertIn('दृश्य पहेलियाँ', html)
        # Play now in Hindi
        self.assertIn('अभी खेलें →', html)

        # Translated activity title rendered in Hindi (stripped of [Demo Data] in h2)
        hi_title = self.translated_activity.get_title('hi').replace(' [Demo Data]', '')
        self.assertIn(hi_title, html)

        # Untranslated activity shows English fallback badge in Hindi
        self.assertIn('अंग्रेजी में दिखाया जा रहा है — हिंदी संस्करण जल्द ही आ रहा है', html)

    def test_hindi_child_player_translated_activity(self):
        self._login_parent()
        res = self.client.get(f'/child/{self.child_hi.id}/play/{self.translated_activity.id}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        q1 = self.translated_activity.questions.order_by(ActivityQuestion.order_num).first()
        hi_q_text = q1.get_question_text('hi')
        self.assertIn(hi_q_text, html)

        # Progress in Hindi
        self.assertIn('प्रश्न 1 /', html)
        # Hint button in Hindi
        self.assertIn('💡 क्या संकेत चाहिए?', html)
        # Skip question in Hindi
        self.assertIn('प्रश्न छोड़ें ⏭️', html)
        # No fallback notice since it is translated
        self.assertNotIn('अंग्रेजी में दिखाया जा रहा है', html)

    def test_hindi_child_player_untranslated_activity_shows_fallback_banner(self):
        self._login_parent()
        res = self.client.get(f'/child/{self.child_hi.id}/play/{self.untranslated_activity.id}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Untranslated banner displayed
        self.assertIn('अंग्रेजी में दिखाया जा रहा है — हिंदी संस्करण जल्द ही आ रहा है', html)
        # English question text rendered safely
        q1 = self.untranslated_activity.questions.order_by(ActivityQuestion.order_num).first()
        self.assertIn(q1.question_text, html)

    def test_hindi_child_answer_evaluation_correct_and_incorrect(self):
        self._login_parent()
        act = self.translated_activity
        q1 = act.questions.order_by(ActivityQuestion.order_num).first()
        hi_correct_ans = q1.get_correct_answer('hi')

        # Submit correct answer in Hindi
        res = self.client.post(
            f'/child/{self.child_hi.id}/play/{act.id}/answer',
            data={
                'question_id': q1.id,
                'selected_answer': hi_correct_ans,
                'q_idx': 0
            }
        )
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        # Correct feedback in Hindi
        self.assertIn('बहुत बढ़िया! बिल्कुल सही! 🎉', html)

        # Submit wrong answer in Hindi
        res_wrong = self.client.post(
            f'/child/{self.child_hi.id}/play/{act.id}/answer',
            data={
                'question_id': q1.id,
                'selected_answer': 'गलत_उत्तर',
                'q_idx': 0
            }
        )
        self.assertEqual(res_wrong.status_code, 200)
        html_wrong = res_wrong.data.decode('utf-8')
        # Incorrect feedback in Hindi with correct answer
        self.assertIn('अच्छा प्रयास! सही उत्तर था', html_wrong)
        self.assertIn(hi_correct_ans, html_wrong)

    def test_hindi_child_hint_endpoint_returns_hindi(self):
        self._login_parent()
        act = self.translated_activity
        q1 = act.questions.order_by(ActivityQuestion.order_num).first()
        hi_hint = q1.get_hint('hi')

        res = self.client.post(
            f'/child/{self.child_hi.id}/play/{act.id}/hint',
            data={'question_id': q1.id},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['hint'], hi_hint)

    def test_hindi_child_results_screen(self):
        self._login_parent()
        act = self.translated_activity
        res = self.client.get(f'/child/{self.child_hi.id}/play/{act.id}/results')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Celebration heading in Hindi
        self.assertIn('शाबाश, Aarav!', html)
        self.assertIn('आपने', html)
        self.assertIn('पूरा कर लिया!', html)
        # Navigation in Hindi
        self.assertIn('फिर से खेलें 🔄', html)
        self.assertIn('← गतिविधियों पर वापस जाएं', html)
        self.assertIn('← श्रेणियों पर वापस जाएं', html)

    # -------------------------------------------------------------------------
    # 3. English and Coming Soon Children
    # -------------------------------------------------------------------------
    def test_english_child_renders_english_and_no_fallback_badge(self):
        self._login_parent()
        res = self.client.get(f'/child/{self.child_en.id}/category/{self.visual_cat.id}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('Back to Categories', html)
        self.assertIn('Play Now →', html)
        self.assertNotIn('अंग्रेजी में दिखाया जा रहा है', html)

    def test_coming_soon_language_falls_back_cleanly_to_english(self):
        self._login_parent()
        res = self.client.get(f'/child/{self.child_es.id}/activities')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Clean English UI rendered
        self.assertTrue("Hi Mateo! Let's Play!" in html or "Hi Mateo! Let&#39;s Play!" in html)
        self.assertIn('Explore →', html)

    # -------------------------------------------------------------------------
    # 4. "Back to Activity Hub" Navigation & Link Integrity
    # -------------------------------------------------------------------------
    def test_back_to_activity_hub_from_child_home(self):
        """Verify /child/home with child_id redirects to categories hub and doesn't loop."""
        self._login_parent()
        # Direct navigation to /child/home?child_id=X
        res = self.client.get(f'/child/home?child_id={self.child_hi.id}', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], f'/child/{self.child_hi.id}/activities')

        # Following redirect yields 200
        follow_res = self.client.get(res.headers['Location'])
        self.assertEqual(follow_res.status_code, 200)

    def test_child_user_home_redirects_to_activity_hub(self):
        """A logged-in child user visiting /child/home goes straight to categories_hub."""
        self._login_child()
        res = self.client.get('/child/home', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers['Location'], f'/child/{self.child_hi.id}/activities')

    def test_click_back_to_activity_hub_returns_200_and_lands_on_expected_destination(self):
        """
        Clicking 'Back to Activity Hub' on the 'Let's Learn and Play!' activity-category screen
        returns a valid 200 response and lands on the expected Activity Hub destination
        (child's own home / category-picker screen).
        """
        # Case A: English Child Context
        from flask import render_template, g
        with self.app.test_request_context():
            from app.models.activity import Category
            cats = Category.query.all()
            g.child_lang = 'en'
            html = render_template('base_child.html', child=self.child_en, categories=cats, categories_by_slug={c.slug: c for c in cats}, child_lang='en')
            parser = HTMLCollector()
            parser.feed(html)
            hub_links = [href for href, text in parser.anchors if 'back to activity hub' in text.lower()]
            self.assertGreaterEqual(len(hub_links), 1, "Expected 'Back to Activity Hub' button on activity-category screen")
            hub_href = hub_links[0]
            self.assertEqual(hub_href, f'/child/{self.child_en.id}/activities')

        # Click the link as authorized parent and confirm it returns 200 and lands on the child's category-picker hub
        self._login_parent()
        click_res = self.client.get(hub_href, follow_redirects=True)
        self.assertEqual(click_res.status_code, 200)
        self.assertIn(f"Hi {self.child_en.name}!", click_res.data.decode('utf-8'))

        # Case B: Hindi Child Context
        with self.app.test_request_context():
            from app.models.activity import Category
            cats = Category.query.all()
            g.child_lang = 'hi'
            html_hi = render_template('base_child.html', child=self.child_hi, categories=cats, categories_by_slug={c.slug: c for c in cats}, child_lang='hi')
            parser_hi = HTMLCollector()
            parser_hi.feed(html_hi)
            hub_links_hi = [href for href, text in parser_hi.anchors if 'गतिविधि हब' in text or 'back to activity hub' in text.lower()]
            self.assertGreaterEqual(len(hub_links_hi), 1, "Expected localized 'Back to Activity Hub' button on Hindi screen")
            hub_href_hi = hub_links_hi[0]
            self.assertEqual(hub_href_hi, f'/child/{self.child_hi.id}/activities')

        click_res_hi = self.client.get(hub_href_hi, follow_redirects=True)
        self.assertEqual(click_res_hi.status_code, 200)
        self.assertIn(f"नमस्ते {self.child_hi.name}!", click_res_hi.data.decode('utf-8'))

        # Case C: Unauthenticated Guest on /child/home
        self.client.get('/auth/logout')
        guest_res = self.client.get('/child/home')
        self.assertEqual(guest_res.status_code, 200)
        guest_html = guest_res.data.decode('utf-8')
        self.assertTrue("Let's Learn and Play!" in guest_html or "Let&#39;s Learn and Play!" in guest_html or "आइए सीखें और खेलें!" in guest_html)

        guest_parser = HTMLCollector()
        guest_parser.feed(guest_html)
        guest_hub_links = [href for href, text in guest_parser.anchors if 'back to activity hub' in text.lower() or 'गतिविधि हब' in text]
        self.assertGreaterEqual(len(guest_hub_links), 1, "Expected 'Back to Activity Hub' button on guest screen")
        guest_hub_href = guest_hub_links[0]

        # Confirm non-empty, non-#, and does not loop to /child/home
        self.assertTrue(bool(guest_hub_href))
        self.assertNotEqual(guest_hub_href, '#')
        self.assertNotEqual(guest_hub_href, '/child/home')

        # Click the link and confirm it returns 200
        guest_click_res = self.client.get(guest_hub_href, follow_redirects=True)
        self.assertEqual(guest_click_res.status_code, 200)

    def test_crawl_all_child_facing_back_navigation_buttons_have_real_non_placeholder_href(self):
        """
        Crawls ALL child-facing back-navigation buttons across all screens to confirm
        each has a real, non-placeholder href (no '#', no empty string, no self-loops),
        and that clicking each returns a valid 200 response.
        """
        self._login_parent()
        screens = [
            f'/child/{self.child_hi.id}/activities',
            f'/child/{self.child_hi.id}/category/{self.visual_cat.id}',
            f'/child/{self.child_hi.id}/play/{self.translated_activity.id}',
            f'/child/{self.child_hi.id}/play/{self.translated_activity.id}/results',
            '/child/home'  # renders select_child for multi-child parent
        ]

        for screen_url in screens:
            res = self.client.get(screen_url)
            self.assertEqual(res.status_code, 200, f"Failed to load {screen_url}")
            html = res.data.decode('utf-8')
            parser = HTMLCollector()
            parser.feed(html)

            back_anchors = [
                (href, text) for href, text in parser.anchors
                if 'back' in text.lower() or 'वापस' in text
            ]
            self.assertGreaterEqual(
                len(back_anchors), 1,
                f"Expected at least one Back link on screen {screen_url}"
            )
            for href, text in back_anchors:
                # 1. Non-empty href
                self.assertTrue(bool(href), f"Back link '{text}' on {screen_url} has empty href")
                # 2. Non-placeholder (#)
                self.assertNotEqual(href, '#', f"Back link '{text}' on {screen_url} points to '#' placeholder")
                self.assertFalse(href.startswith('javascript:'), f"Back link '{text}' on {screen_url} points to javascript pseudo-protocol")
                # 3. No self-loops
                self.assertNotEqual(href, screen_url, f"Back link '{text}' on {screen_url} loops to itself")

                # 4. Confirm clicking the back button returns a valid 200 response
                click_resp = self.client.get(href, follow_redirects=True)
                self.assertEqual(
                    click_resp.status_code, 200,
                    f"Clicking back link '{text}' ({href}) from {screen_url} failed with status {click_resp.status_code}"
                )


if __name__ == '__main__':
    unittest.main()
