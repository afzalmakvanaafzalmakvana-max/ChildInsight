"""
Automated Test Suite for Orchestrator Agent & Action Center (tests/test_orchestrator_agent.py)

Validates:
1. Multi-age-band grouping: multiple warnings for the same category across different
   age bands are consolidated into one grouped entry showing 'affects ages X-Y, ...'.
2. Priority tier assignment: Critical, Important, and Minor tiers are assigned
   consistently and match the documented rules on sample data.
3. Grounded summaries: summary texts trace strictly to real underlying numbers.
4. Read-only guarantee: zero database writes/mutations to activities, categories,
   questions, suggestions, or user tables.
5. Dismissal behavior: dismissing an action item declutters the view without modifying
   underlying database records.
6. RBAC security: non-admin roles (parent, child, guest) cannot access the Action Center.
7. Scheduler integration: Step 7 runs cleanly in the maintenance pipeline with fault isolation.
"""

import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.agent import orchestrator_agent, compliance_agent, scheduler
from app.utils.seed_data import seed_activities


class OrchestratorAgentTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        orchestrator_agent.clear_dismissed_items()
        compliance_agent.reset_incident_history()

        # Seed users
        self.admin = User(name='Admin User', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent User', email='parent@example.com', role='parent')
        self.parent.set_password('ParentPass123!')

        self.child_user = User(name='Child User', email='child@example.com', role='child')
        self.child_user.set_password('ChildPass123!')

        db.session.add_all([self.admin, self.parent, self.child_user])
        db.session.commit()

        self.child = Child(parent_id=self.parent.id, name='Charlie', age=7, grade='2nd Grade', preferred_language='English')
        db.session.add(self.child)
        db.session.commit()

        # Seed standard activities catalog
        seed_activities()

    def tearDown(self):
        orchestrator_agent.clear_dismissed_items()
        compliance_agent.reset_incident_history()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Multi-Age-Band Grouping & Deduplication
    # -------------------------------------------------------------------------
    def test_multi_age_band_grouping(self):
        """Verify multiple warnings for the same category across different age bands become ONE grouped entry."""
        cat = Category.query.filter_by(slug='logic').first()

        # Create 3 suggestions for the same category across distinct age bands
        sug1 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat.id,
            age_band='4-6',
            target_difficulty='Easy',
            suggested_title='Logic Adventures for Ages 4-6',
            reason='4 children aged 4-6 achieved 82% accuracy in Beginner Logic with only 1 Easy activity available.',
            priority_score=15.0,
            persistence_count=1,
            status=ContentSuggestion.STATUS_PENDING
        )
        sug2 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=cat.id,
            age_band='9-12',
            target_difficulty='Medium',
            suggested_title='Logic Puzzles for Ages 9-12',
            reason='9 registered learners in age band 9-12 have only 1 activity available in Logic & Reasoning.',
            priority_score=22.0,
            persistence_count=2,
            status=ContentSuggestion.STATUS_PENDING
        )
        sug3 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat.id,
            age_band='12-14',
            target_difficulty='Advanced',
            suggested_title='Advanced Logic Deductions',
            reason='14 children aged 12-14 achieved 85% accuracy in Medium Logic with steady engagement.',
            priority_score=38.0,
            persistence_count=3,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add_all([sug1, sug2, sug3])
        db.session.commit()

        action_items = orchestrator_agent.get_action_items()

        # Filter items for Logic category suggestions
        logic_items = [i for i in action_items if i.get('source') == 'Content Suggestions' and i.get('meta', {}).get('category_id') == cat.id]

        # Must be EXACTLY ONE grouped entry instead of 3 separate rows
        self.assertEqual(len(logic_items), 1, "Expected exactly 1 consolidated item for Logic category across 3 age bands")

        grouped_item = logic_items[0]
        subtitle = grouped_item['subtitle']

        # Verifies 'affects ages 4-6, 9-12, 12-14'
        self.assertIn('4-6', subtitle)
        self.assertIn('9-12', subtitle)
        self.assertIn('12-14', subtitle)
        self.assertIn('affects ages', subtitle)

        # Meta attributes verify consolidation
        meta = grouped_item['meta']
        self.assertEqual(len(meta['suggestion_ids']), 3)
        self.assertEqual(meta['persistence_count'], 3)
        self.assertEqual(meta['priority_score'], 38.0)

    # -------------------------------------------------------------------------
    # 2. Priority Tier Assignment Rules
    # -------------------------------------------------------------------------
    def test_priority_tier_assignment_consistency(self):
        """Verifies Critical, Important, and Minor tiers are assigned consistently based on real numbers."""
        cat_visual = Category.query.filter_by(slug='visual').first()
        cat_numbers = Category.query.filter_by(slug='numbers').first()
        cat_memory = Category.query.filter_by(slug='memory').first()

        # 1. Critical Suggestion: priority_score >= 25.0 and persistence >= 3
        sug_crit = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat_visual.id,
            age_band='9-12',
            target_difficulty='Advanced',
            suggested_title='Visual Challenge',
            reason='12 children aged 9-12 have only 1 activity available.',
            priority_score=29.0,
            persistence_count=3,
            status=ContentSuggestion.STATUS_PENDING
        )
        # 2. Important Suggestion: 10.0 <= priority_score < 25.0
        sug_imp = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=cat_numbers.id,
            age_band='6-9',
            target_difficulty='Easy',
            suggested_title='Number Patterns',
            reason='4 children aged 6-9 need additional exercises.',
            priority_score=13.0,
            persistence_count=1,
            status=ContentSuggestion.STATUS_PENDING
        )
        # 3. Minor Suggestion: 0 affected children, priority_score < 10.0
        sug_min = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_CONTENT_IMBALANCE,
            category_id=cat_memory.id,
            age_band='4-6',
            target_difficulty='Beginner',
            suggested_title='Memory Foundations',
            reason='General category offering expansion for Memory.',
            priority_score=5.0,
            persistence_count=1,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add_all([sug_crit, sug_imp, sug_min])
        db.session.commit()

        action_items = orchestrator_agent.get_action_items()

        crit_item = next(i for i in action_items if i.get('meta', {}).get('category_id') == cat_visual.id)
        imp_item = next(i for i in action_items if i.get('meta', {}).get('category_id') == cat_numbers.id)
        min_item = next(i for i in action_items if i.get('meta', {}).get('category_id') == cat_memory.id)

        self.assertEqual(crit_item['priority_tier'], orchestrator_agent.TIER_CRITICAL)
        self.assertEqual(imp_item['priority_tier'], orchestrator_agent.TIER_IMPORTANT)
        self.assertEqual(min_item['priority_tier'], orchestrator_agent.TIER_MINOR)

        # Confirm sort order: Critical appears before Important, which appears before Minor
        crit_index = action_items.index(crit_item)
        imp_index = action_items.index(imp_item)
        min_index = action_items.index(min_item)

        self.assertLess(crit_index, imp_index)
        self.assertLess(imp_index, min_index)

    def test_compliance_incidents_trigger_critical_tier(self):
        """Active compliance incidents in the last 24h must produce a Critical tier alert."""
        # Enforce compliance incident
        compliance_agent.enforce_compliance(
            text="Student shows severe mental deficit and diagnosis",
            context={'source': 'recommendation', 'child_id': self.child.id},
            fallback_text="Practice activity"
        )
        self.assertGreater(compliance_agent.get_recent_incident_count(since_hours=24), 0)

        action_items = orchestrator_agent.get_action_items()
        comp_items = [i for i in action_items if i.get('key') == 'compliance_incidents_alert']

        self.assertEqual(len(comp_items), 1)
        self.assertEqual(comp_items[0]['priority_tier'], orchestrator_agent.TIER_CRITICAL)
        self.assertIn("1 non-compliant clinical/diagnostic term(s)", comp_items[0]['summary'])

    # -------------------------------------------------------------------------
    # 3. Grounded Summaries & Numeric Traceability
    # -------------------------------------------------------------------------
    def test_summary_text_traceable_to_real_numbers(self):
        """Summary text must only reference numbers present in the underlying data."""
        cat = Category.query.filter_by(slug='language').first()
        sug = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat.id,
            age_band='6-9',
            target_difficulty='Medium',
            suggested_title='Language Builders',
            reason='7 children aged 6-9 achieved 78% accuracy in Easy Language.',
            priority_score=19.0,
            persistence_count=2,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sug)
        db.session.commit()

        action_items = orchestrator_agent.get_action_items()
        item = next(i for i in action_items if i.get('meta', {}).get('category_id') == cat.id)

        summary = item['summary']
        # 7 children, 19.0 priority score, 2 runs
        self.assertIn('7', summary)
        self.assertIn('19.0', summary)
        self.assertIn('2', summary)
        self.assertIn(cat.name, summary)

    # -------------------------------------------------------------------------
    # 4. Strict Read-Only Enforcement
    # -------------------------------------------------------------------------
    def test_orchestrator_is_strictly_read_only(self):
        """Calling the orchestrator makes zero database row changes."""
        act_count_before = Activity.query.count()
        cat_count_before = Category.query.count()
        q_count_before = ActivityQuestion.query.count()
        sug_count_before = ContentSuggestion.query.count()
        user_count_before = User.query.count()
        child_count_before = Child.query.count()

        # Run orchestrator
        action_items = orchestrator_agent.get_action_items()
        self.assertIsInstance(action_items, list)

        # Verify zero row changes
        self.assertEqual(Activity.query.count(), act_count_before)
        self.assertEqual(Category.query.count(), cat_count_before)
        self.assertEqual(ActivityQuestion.query.count(), q_count_before)
        self.assertEqual(ContentSuggestion.query.count(), sug_count_before)
        self.assertEqual(User.query.count(), user_count_before)
        self.assertEqual(Child.query.count(), child_count_before)

    # -------------------------------------------------------------------------
    # 5. Dismissal & Decluttering (Without Database Mutation)
    # -------------------------------------------------------------------------
    def test_dismiss_declutters_view_without_db_mutation(self):
        """Dismissing hides an item from the view but does not delete or change database rows."""
        cat = Category.query.filter_by(slug='visual').first()
        sug = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_CONTENT_IMBALANCE,
            category_id=cat.id,
            age_band='4-6',
            target_difficulty='Beginner',
            suggested_title='Visual Fun',
            reason='Minor visual content opportunity.',
            priority_score=4.0,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sug)
        db.session.commit()

        initial_items = orchestrator_agent.get_action_items()
        target_item = next(i for i in initial_items if i.get('meta', {}).get('category_id') == cat.id)
        target_key = target_item['key']

        # Dismiss the item
        orchestrator_agent.dismiss_action_item(target_key)

        active_items = orchestrator_agent.get_active_action_items()
        active_keys = [i['key'] for i in active_items]
        self.assertNotIn(target_key, active_keys)

        # Verify underlying database record was NOT mutated
        refreshed_sug = db.session.get(ContentSuggestion, sug.id)
        self.assertIsNotNone(refreshed_sug)
        self.assertEqual(refreshed_sug.status, ContentSuggestion.STATUS_PENDING)

        # Restore items
        orchestrator_agent.clear_dismissed_items()
        restored_active = orchestrator_agent.get_active_action_items()
        restored_keys = [i['key'] for i in restored_active]
        self.assertIn(target_key, restored_keys)

    # -------------------------------------------------------------------------
    # 6. Admin UI & RBAC Security
    # -------------------------------------------------------------------------
    def test_admin_access_action_center(self):
        """Admin can view the Action Center on /admin/agents and /admin/action-center."""
        self._login('admin@example.com', 'AdminPass123!')

        # 1. GET /admin/action-center redirects to /admin/agents#action-center
        res_alias = self.client.get('/admin/action-center', follow_redirects=False)
        self.assertEqual(res_alias.status_code, 302)
        self.assertIn('/admin/agents#action-center', res_alias.headers['Location'])

        # 2. GET /admin/agents renders Action Center section
        res_agents = self.client.get('/admin/agents')
        self.assertEqual(res_agents.status_code, 200)
        html = res_agents.data.decode('utf-8')
        self.assertIn('Action Center: Prioritized Attention List', html)
        self.assertIn('id="action-center"', html)

        # 3. POST /admin/action-center/dismiss
        res_dismiss = self.client.post(
            '/admin/action-center/dismiss',
            data={'item_key': 'test_dismiss_key'},
            follow_redirects=True
        )
        self.assertEqual(res_dismiss.status_code, 200)

        # 4. POST /admin/action-center/restore
        res_restore = self.client.post(
            '/admin/action-center/restore',
            follow_redirects=True
        )
        self.assertEqual(res_restore.status_code, 200)

    def test_non_admin_rbac_denied(self):
        """Parent, child, and guest users cannot access the Action Center or dismiss endpoints."""
        # Unauthenticated
        res = self.client.get('/admin/action-center')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # Parent user -> 403
        self._login('parent@example.com', 'ParentPass123!')
        res_parent = self.client.get('/admin/action-center')
        self.assertEqual(res_parent.status_code, 403)

        res_parent_dismiss = self.client.post('/admin/action-center/dismiss', data={'item_key': 'abc'})
        self.assertEqual(res_parent_dismiss.status_code, 403)

        # Child user -> 403
        self._login('child@example.com', 'ChildPass123!')
        res_child = self.client.get('/admin/action-center')
        self.assertEqual(res_child.status_code, 403)

    # -------------------------------------------------------------------------
    # 7. Scheduler Maintenance Pipeline Integration
    # -------------------------------------------------------------------------
    def test_scheduler_maintenance_pipeline_step_7_orchestrator(self):
        """Step 7 runs in the scheduler maintenance pipeline and outputs item counts."""
        res = scheduler.run_maintenance_pipeline(triggered_by='test')
        self.assertIn(res['status'], ('success', 'partial_failure'))

        steps = res.get('steps', [])
        step7 = next((s for s in steps if s['name'] == 'Consolidate Orchestrator Action Items'), None)
        self.assertIsNotNone(step7, "Expected Step 7 'Consolidate Orchestrator Action Items' in scheduler results")
        self.assertEqual(step7['status'], 'success')
        self.assertIn('Synthesized', step7['message'])
        self.assertIn('Critical', step7['message'])
        self.assertIn('Important', step7['message'])
        self.assertIn('Minor', step7['message'])


if __name__ == '__main__':
    unittest.main()
