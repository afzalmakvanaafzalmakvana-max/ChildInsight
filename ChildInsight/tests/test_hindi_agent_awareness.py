import json
import re
import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.agent import compliance_agent, content_integrity_agent, content_suggestion_agent, content_draft_agent


class HindiAgentAwarenessTestCase(unittest.TestCase):
    """
    Comprehensive test suite ensuring all internal agents are fully aware of Hindi
    content, enforce strict clinical blacklists in both English and Hindi, detect
    partial/broken translations, surface data-backed translation gaps with exact DB counts,
    and produce dual-language drafts for human review and approval without auto-publishing.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create roles
        self.admin = User(name='Admin User', email='admin@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent User', email='parent@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')

        db.session.add_all([self.admin, self.parent])
        db.session.commit()

        # Create test categories
        self.cat_logic = Category(name='Logic', slug='logic', icon='🧩', description='Logic and reasoning puzzles')
        self.cat_numbers = Category(name='Numbers', slug='numbers', icon='🔢', description='Numerical problem solving')
        db.session.add_all([self.cat_logic, self.cat_numbers])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, user):
        self.client.get('/auth/logout')
        return self.client.post('/auth/login', data={
            'email': user.email,
            'password': 'AdminPass123!' if user.role == 'admin' else 'ParentPass123!'
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Compliance Agent Tests (Hindi & English Clinical Blacklist)
    # -------------------------------------------------------------------------
    def test_compliance_agent_catches_hindi_clinical_terms(self):
        """Test that ComplianceAgent catches clinical/diagnostic terms in Hindi as strictly as English."""
        # English clinical term caught
        safe_en, reason_en = compliance_agent.check_text("This child has an attention deficit disorder.")
        self.assertFalse(safe_en)
        self.assertIn("deficit", reason_en.lower())

        # Hindi clinical terms caught
        hindi_violations = [
            ("यह गतिविधि विकार का निदान करती है", "विकार"),
            ("छात्र का आईक्यू स्तर कम है", "आईक्यू"),
            ("नैदानिक मूल्यांकन के अनुसार", "नैदानिक"),
            ("मानसिक मंदता से ग्रस्त", "मंदता"),
            ("इस बच्चे में अक्षमता पाई गई", "अक्षमता"),
            ("एडीएचडी और अतिसक्रियता की जांच", "एडीएचडी"),
            ("ऑटिज्म के लक्षण", "ऑटिज्म")
        ]

        for text, expected_term in hindi_violations:
            is_safe, reason = compliance_agent.check_text(text)
            self.assertFalse(is_safe, f"Expected '{text}' to fail compliance check.")
            self.assertIsNotNone(reason)

    def test_compliance_agent_passes_clean_hindi_pedagogy(self):
        """Test that cheerful, playful, non-clinical Hindi sentences pass compliance without false positives."""
        clean_hindi_samples = [
            "यह एक मजेदार पहेली खोज यात्रा है!",
            "तारों और रंगों के पैटर्न को ध्यान से देखें।",
            "शाबाश! आपने बहुत सुंदर प्रयास किया।",
            "आइए मिलकर इस पहेली को सुलझाते हैं और नए बैज जीतते हैं।",
            "इनमें से कौन सा जानवर तालाब में टर्र-टर्र करता है?"
        ]

        for text in clean_hindi_samples:
            is_safe, reason = compliance_agent.check_text(text)
            self.assertTrue(is_safe, f"Expected clean Hindi text '{text}' to pass, but got: {reason}")
            self.assertIsNone(reason)

    def test_compliance_agent_check_activity_translations(self):
        """Test the check_activity_translations helper with valid and invalid translation dictionaries."""
        clean_translations = {
            'hi': {
                'title': 'रोमांचक खोज यात्रा',
                'description': 'बच्चों के लिए मजेदार पहेलियां',
                'questions': [
                    {
                        'question_text': '2 और 2 कितने होते हैं?',
                        'options': ['4', '3', '5', '6'],
                        'correct_answer': '4',
                        'hint': 'उंगलियों पर गिनें।'
                    }
                ]
            }
        }
        is_safe, reason = compliance_agent.check_activity_translations(clean_translations)
        self.assertTrue(is_safe)
        self.assertIsNone(reason)

        dirty_translations = {
            'hi': {
                'title': 'मानसिक विकार परीक्षण',
                'description': 'आईक्यू मापने की गतिविधि',
                'questions': []
            }
        }
        is_safe, reason = compliance_agent.check_activity_translations(dirty_translations)
        self.assertFalse(is_safe)
        self.assertIsNotNone(reason)

    def test_compliance_agent_enforce_compliance_fallback_in_hindi(self):
        """Test enforce_compliance provides Hindi fallback when non-compliant Devanagari text is checked."""
        result = compliance_agent.enforce_compliance("यह बच्चा गंभीर विकार से ग्रसित है")
        self.assertEqual(result, compliance_agent.DEFAULT_FALLBACK_TEXT_HI)

    # -------------------------------------------------------------------------
    # 2. Content Integrity Agent Tests (Incomplete Translation Detection)
    # -------------------------------------------------------------------------
    def test_content_integrity_agent_detects_incomplete_translations(self):
        """Verify ContentIntegrityAgent audits activities and flags partial or broken Hindi translations."""
        # Activity 1: Title translated, but no question translations
        act1 = Activity(
            category_id=self.cat_logic.id,
            title='Mystery Clues',
            description='A logic puzzle',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True,
            translations_json=json.dumps({'hi': {'title': 'रहस्यमयी सुराग', 'description': 'तर्क पहेली'}}, ensure_ascii=False)
        )
        db.session.add(act1)
        db.session.flush()

        q1 = ActivityQuestion(
            activity_id=act1.id,
            question_text='What is the clue?',
            options_json=json.dumps(['A', 'B', 'C', 'D']),
            correct_answer='A',
            order_num=1
        )
        db.session.add(q1)

        # Activity 2: Question option count mismatch (English 4, Hindi 3)
        act2 = Activity(
            category_id=self.cat_numbers.id,
            title='Number Safari',
            description='Counting numbers',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True,
            translations_json=json.dumps({'hi': {'title': 'संख्या सफारी', 'description': 'संख्या गिनना'}}, ensure_ascii=False)
        )
        db.session.add(act2)
        db.session.flush()

        q2 = ActivityQuestion(
            activity_id=act2.id,
            question_text='How many lions?',
            options_json=json.dumps(['2', '3', '4', '5']),
            correct_answer='2',
            translations_json=json.dumps({
                'hi': {
                    'question_text': 'कितने शेर हैं?',
                    'options': ['२', '३', '४'],  # only 3 options! Mismatch with English (4)
                    'correct_answer': '२'
                }
            }, ensure_ascii=False),
            order_num=1
        )
        db.session.add(q2)
        db.session.commit()

        # Run integrity audit
        issues = content_integrity_agent.run_audit()
        trans_issues = [i for i in issues if i.get('issue_type') == 'incomplete_translation']

        # Both activities should be flagged
        flagged_ids = [i.get('activity_id') for i in trans_issues]
        self.assertIn(act1.id, flagged_ids)
        self.assertIn(act2.id, flagged_ids)

        # Verify exact details reported
        act1_issue = next(i for i in trans_issues if i.get('activity_id') == act1.id)
        self.assertIn("lack Hindi translations", act1_issue['description'])

        act2_issue = next(i for i in trans_issues if i.get('activity_id') == act2.id)
        self.assertIn("count mismatch", act2_issue['description'])

    # -------------------------------------------------------------------------
    # 3. Content Suggestion Agent Tests (Translation Gap Heuristic)
    # -------------------------------------------------------------------------
    def test_content_suggestion_agent_detects_translation_gap(self):
        """Verify ContentSuggestionAgent detects translation gaps with real child counts."""
        # Create 2 Hindi-preferring children aged 5 (age band 4-6)
        c1 = Child(name='Aarav', age=5, preferred_language='hi', parent_id=self.parent.id)
        c2 = Child(name='Ishaan', age=5, preferred_language='hi', parent_id=self.parent.id)
        db.session.add_all([c1, c2])

        # Create 1 English activity in Logic for age 4-6 without Hindi translation
        act = Activity(
            category_id=self.cat_logic.id,
            title='Early Shapes Adventure',
            description='Shapes for young learners',
            difficulty='Easy',
            min_age=4,
            max_age=6,
            is_active=True,
            translations_json=None
        )
        db.session.add(act)
        db.session.commit()

        suggestions = content_suggestion_agent.generate_suggestions()
        trans_gaps = [s for s in suggestions if s.suggestion_type == ContentSuggestion.TYPE_TRANSLATION_GAP]

        self.assertTrue(len(trans_gaps) >= 1)
        logic_gap = next((s for s in trans_gaps if s.category_id == self.cat_logic.id), None)
        self.assertIsNotNone(logic_gap)
        self.assertEqual(logic_gap.age_band, '4-6')
        self.assertEqual(logic_gap.status, ContentSuggestion.STATUS_PENDING)

        # Verify evidence-dense reason contains real computed values
        self.assertIn("2 registered learner(s) in age band 4-6", logic_gap.reason)
        self.assertIn("prefer Hindi", logic_gap.reason)
        self.assertIn("0 translated Hindi activity(ies) out of 1 total activities (0% translated)", logic_gap.reason)

    # -------------------------------------------------------------------------
    # 4. Content Draft Agent Tests (Dual-Language Draft Generation)
    # -------------------------------------------------------------------------
    def test_content_draft_agent_generates_dual_language_draft(self):
        """Verify ContentDraftAgent generates dual-language drafts for translation gaps."""
        # Create a suggestion for a translation gap
        sugg = ContentSuggestion(
            category_id=self.cat_logic.id,
            suggestion_type=ContentSuggestion.TYPE_TRANSLATION_GAP,
            age_band='4-6',
            target_difficulty='Easy',
            reason='2 Hindi-preferring learner(s) aged 4-6 in Logic with 0/1 translated activities.',
            suggested_title='तर्क खोज Quest',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sugg)
        db.session.commit()

        draft = content_draft_agent.generate_draft_activity(
            category_id=self.cat_logic.id,
            age_band='4-6',
            difficulty='Easy',
            suggestion_id=sugg.id
        )

        # Must have dual-language indicators
        self.assertTrue(draft.get('has_hindi'))
        self.assertIsNotNone(draft.get('translations'))
        self.assertIn('hi', draft['translations'])

        hi_data = draft['translations']['hi']
        self.assertTrue(bool(hi_data.get('title')))
        self.assertTrue(bool(hi_data.get('description')))
        self.assertTrue(len(hi_data.get('questions', [])) >= 5)

        # English questions must also exist and match question count
        en_questions = draft.get('questions', [])
        hi_questions = hi_data.get('questions', [])
        self.assertEqual(len(en_questions), len(hi_questions))

        # Check compliance on both English and Hindi strings
        for q in en_questions:
            is_safe, _ = compliance_agent.check_text(q['question_text'])
            self.assertTrue(is_safe)
            is_safe, _ = compliance_agent.check_text(q['correct_answer'])
            self.assertTrue(is_safe)

        for hq in hi_questions:
            is_safe, reason = compliance_agent.check_text(hq['question_text'])
            self.assertTrue(is_safe, f"Hindi question failed compliance: {reason}")
            is_safe, reason = compliance_agent.check_text(hq['correct_answer'])
            self.assertTrue(is_safe, f"Hindi correct answer failed compliance: {reason}")
            for hopt in hq['options']:
                is_safe, reason = compliance_agent.check_text(hopt)
                self.assertTrue(is_safe, f"Hindi option failed compliance: {reason}")

    # -------------------------------------------------------------------------
    # 5. Human-in-the-Loop Review & Publishing Test
    # -------------------------------------------------------------------------
    def test_admin_review_and_publish_persists_both_languages(self):
        """Verify that admin publishing persists both English and Hindi versions to the database."""
        self.login_as(self.admin)

        sugg = ContentSuggestion(
            category_id=self.cat_numbers.id,
            suggestion_type=ContentSuggestion.TYPE_TRANSLATION_GAP,
            age_band='6-9',
            target_difficulty='Easy',
            reason='1 Hindi-preferring learner with 0 translated activities.',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sugg)
        db.session.commit()

        # Submit dual-language draft to publish endpoint
        questions_payload = [
            {
                'order_num': 1,
                'question_text': 'What is 5 + 5?',
                'options': ['10', '9', '11', '12'],
                'correct_answer': '10',
                'hint': 'Count with fingers.',
                'translations': {
                    'hi': {
                        'question_text': '5 + 5 कितना होता है?',
                        'options': ['10', '9', '11', '12'],
                        'correct_answer': '10',
                        'hint': 'उंगलियों से गिनें।'
                    }
                }
            }
        ]

        resp = self.client.post('/admin/activities/ai-draft/publish', data={
            'category_id': self.cat_numbers.id,
            'title': 'Fun With Tens',
            'description': 'Exploring addition with tens.',
            'hi_title': 'दस के साथ मस्ती',
            'hi_description': 'जोड़ सीखने की मजेदार गतिविधि।',
            'difficulty': 'Easy',
            'min_age': 6,
            'max_age': 9,
            'estimated_duration': 6,
            'suggestion_id': sugg.id,
            'questions_json': json.dumps(questions_payload)
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)

        # Verify activity was committed with Hindi translations
        published_act = Activity.query.filter_by(title='Fun With Tens').first()
        self.assertIsNotNone(published_act)
        self.assertIsNotNone(published_act.translations_json)
        act_trans = json.loads(published_act.translations_json)
        self.assertEqual(act_trans['hi']['title'], 'दस के साथ मस्ती')
        self.assertEqual(act_trans['hi']['description'], 'जोड़ सीखने की मजेदार गतिविधि।')

        # Verify question was committed with Hindi translations
        published_q = ActivityQuestion.query.filter_by(activity_id=published_act.id).first()
        self.assertIsNotNone(published_q)
        self.assertIsNotNone(published_q.translations_json)
        q_trans = json.loads(published_q.translations_json)
        self.assertEqual(q_trans['hi']['question_text'], '5 + 5 कितना होता है?')
        self.assertEqual(q_trans['hi']['hint'], 'उंगलियों से गिनें।')

        # Verify suggestion status updated to approved
        db.session.refresh(sugg)
        self.assertEqual(sugg.status, ContentSuggestion.STATUS_APPROVED)

    # -------------------------------------------------------------------------
    # 6. Strict Numerical Accuracy Test (DB vs Agent Verification)
    # -------------------------------------------------------------------------
    def test_agent_reported_numbers_match_database_directly(self):
        """
        Verify every number and statistic reported by agents strictly matches
        a direct query from the database, preventing estimated or fabricated numbers.
        """
        # Create test children with known language distributions
        # Age band 4-6: 3 children (2 hi, 1 en)
        # Age band 6-9: 2 children (1 hi, 1 en)
        # Age band 9-12: 1 child (0 hi, 1 en)
        children_data = [
            ('Child A', 4, 'hi'),
            ('Child B', 5, 'hi'),
            ('Child C', 6, 'en'),
            ('Child D', 7, 'hi'),
            ('Child E', 8, 'en'),
            ('Child F', 10, 'en'),
        ]
        for name, age, lang in children_data:
            c = Child(name=name, age=age, preferred_language=lang, parent_id=self.parent.id)
            db.session.add(c)

        # Create activities in Logic:
        # Age 4-5: 2 total, 1 translated to Hindi (does not overlap with age 6-9)
        # Age 6-9: 3 total, 0 translated to Hindi
        act_4_5_trans = Activity(
            category_id=self.cat_logic.id,
            title='Shapes Logic 1',
            difficulty='Easy',
            min_age=4,
            max_age=5,
            is_active=True,
            translations_json=json.dumps({'hi': {'title': 'आकार तर्क १'}}, ensure_ascii=False)
        )
        act_4_5_untrans = Activity(
            category_id=self.cat_logic.id,
            title='Shapes Logic 2',
            difficulty='Easy',
            min_age=4,
            max_age=5,
            is_active=True,
            translations_json=None
        )
        act_6_9_a = Activity(
            category_id=self.cat_logic.id,
            title='Patterns 1',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True,
            translations_json=None
        )
        act_6_9_b = Activity(
            category_id=self.cat_logic.id,
            title='Patterns 2',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True,
            translations_json=None
        )
        act_6_9_c = Activity(
            category_id=self.cat_logic.id,
            title='Patterns 3',
            difficulty='Easy',
            min_age=6,
            max_age=9,
            is_active=True,
            translations_json=None
        )
        db.session.add_all([act_4_5_trans, act_4_5_untrans, act_6_9_a, act_6_9_b, act_6_9_c])
        db.session.commit()

        # 1. Direct DB Query for Hindi children in age band 4-6
        direct_db_hi_4_6 = db.session.query(db.func.count(Child.id)).filter(
            Child.preferred_language == 'hi',
            Child.age >= 4,
            Child.age <= 6
        ).scalar()
        self.assertEqual(direct_db_hi_4_6, 2)

        # Direct DB Query for Hindi children in age band 6-9
        direct_db_hi_6_9 = db.session.query(db.func.count(Child.id)).filter(
            Child.preferred_language == 'hi',
            Child.age >= 6,
            Child.age <= 9
        ).scalar()
        self.assertEqual(direct_db_hi_6_9, 1)

        # 2. Direct DB Query for translated activities in Logic for age band 6-9
        direct_db_trans_logic_6_9 = db.session.query(db.func.count(Activity.id)).filter(
            Activity.category_id == self.cat_logic.id,
            Activity.min_age <= 9,
            Activity.max_age >= 6,
            Activity.translations_json.isnot(None)
        ).scalar()
        self.assertEqual(direct_db_trans_logic_6_9, 0)

        # Direct DB Query for total activities in Logic for age band 6-9
        direct_db_total_logic_6_9 = db.session.query(db.func.count(Activity.id)).filter(
            Activity.category_id == self.cat_logic.id,
            Activity.min_age <= 9,
            Activity.max_age >= 6
        ).scalar()
        self.assertEqual(direct_db_total_logic_6_9, 3)

        # 3. Collect platform data via ContentSuggestionAgent
        platform_data = content_suggestion_agent.analyze_platform_data()

        # Verify platform_data exact count matches
        self.assertEqual(len(platform_data['hindi_children_by_band']['4-6']), direct_db_hi_4_6)
        self.assertEqual(len(platform_data['hindi_children_by_band']['6-9']), direct_db_hi_6_9)

        # 4. Detect gaps and inspect translation gap reasoning string
        suggestions = content_suggestion_agent.generate_suggestions()
        trans_suggestions = [s for s in suggestions if s.suggestion_type == ContentSuggestion.TYPE_TRANSLATION_GAP]

        # Find suggestion for Logic in band 6-9
        sugg_logic_6_9 = next((s for s in trans_suggestions if s.category_id == self.cat_logic.id and s.age_band == '6-9'), None)
        self.assertIsNotNone(sugg_logic_6_9)

        # Check that the numbers in the reason string match the direct database query results exactly
        expected_reason_snippet = f"{direct_db_hi_6_9} registered learner(s) in age band 6-9"
        self.assertIn(expected_reason_snippet, sugg_logic_6_9.reason)

        expected_trans_count_snippet = f"{direct_db_trans_logic_6_9} translated Hindi activity(ies) out of {direct_db_total_logic_6_9} total activities"
        self.assertIn(expected_trans_count_snippet, sugg_logic_6_9.reason)

        pct = round((direct_db_trans_logic_6_9 / direct_db_total_logic_6_9) * 100)
        expected_pct_snippet = f"({pct}% translated)"
        self.assertIn(expected_pct_snippet, sugg_logic_6_9.reason)


if __name__ == '__main__':
    unittest.main()
