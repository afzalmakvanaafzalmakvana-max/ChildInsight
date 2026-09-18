import os
import unittest
from unittest.mock import patch
from flask import Flask

from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Activity
from app.models.session import ActivitySession
from app.models.recommendation import Recommendation
from app.utils.seed_data import seed_demo_data
from config import ProductionConfig, DevelopmentConfig, config


class Phase10DeploymentTestCase(unittest.TestCase):
    """Automated tests for Phase 10: Production Configuration, Deployment, and Demo Data."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_production_config_security_flags(self):
        """Verify that ProductionConfig enforces strict production security flags."""
        self.assertFalse(ProductionConfig.DEBUG)
        self.assertFalse(ProductionConfig.TESTING)
        self.assertTrue(ProductionConfig.SESSION_COOKIE_SECURE)
        self.assertTrue(ProductionConfig.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(ProductionConfig.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertTrue(ProductionConfig.REMEMBER_COOKIE_SECURE)
        self.assertTrue(ProductionConfig.REMEMBER_COOKIE_HTTPONLY)
        self.assertEqual(ProductionConfig.REMEMBER_COOKIE_SAMESITE, 'Lax')

    def test_production_config_postgres_url_normalization(self):
        """Verify that legacy postgres:// URLs are normalized to postgresql://."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgres://user:pass@host:5432/childinsight_prod'
        }):
            # Dynamically reload or check url replacement
            raw = os.environ.get('DATABASE_URL')
            normalized = raw.replace('postgres://', 'postgresql://', 1)
            self.assertEqual(normalized, 'postgresql://user:pass@host:5432/childinsight_prod')

    def test_production_config_validation_requires_secret_key(self):
        """Verify that ProductionConfig.init_app raises ValueError when SECRET_KEY is missing."""
        mock_app = Flask(__name__)
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///tmp.db'}, clear=True):
            if 'SECRET_KEY' in os.environ:
                del os.environ['SECRET_KEY']
            with self.assertRaises(ValueError) as ctx:
                ProductionConfig.init_app(mock_app)
            self.assertIn("SECRET_KEY", str(ctx.exception))

    def test_production_config_validation_requires_database_url(self):
        """Verify that ProductionConfig.init_app raises ValueError when DATABASE_URL is missing."""
        mock_app = Flask(__name__)
        with patch.dict(os.environ, {'SECRET_KEY': 'super-secure-production-key'}, clear=True):
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
            with self.assertRaises(ValueError) as ctx:
                ProductionConfig.init_app(mock_app)
            self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_env_example_documentation(self):
        """Verify that .env.example contains all required production configuration keys."""
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        env_example_path = os.path.join(basedir, '.env.example')
        self.assertTrue(os.path.exists(env_example_path), ".env.example file must exist")

        with open(env_example_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('FLASK_CONFIG', content)
        self.assertIn('SECRET_KEY', content)
        self.assertIn('DATABASE_URL', content)
        self.assertIn('SESSION_COOKIE_SECURE', content)
        self.assertIn('LOG_FILE', content)
        self.assertIn('postgresql://', content)
        self.assertIn('mysql+pymysql://', content)

    def test_seed_demo_data_creation_and_labelling(self):
        """Verify that seed_demo_data successfully seeds tagged entities and trained models."""
        res = seed_demo_data()

        # Check demo user accounts
        admin = User.query.filter_by(email='admin@childinsight.demo').first()
        teacher = User.query.filter_by(email='teacher@childinsight.demo').first()
        parent = User.query.filter_by(email='parent@childinsight.demo').first()

        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.check_password('DemoPass123!'))

        self.assertIsNotNone(teacher)
        self.assertEqual(teacher.role, 'teacher')
        self.assertTrue(teacher.check_password('DemoPass123!'))

        self.assertIsNotNone(parent)
        self.assertEqual(parent.role, 'parent')
        self.assertTrue(parent.check_password('DemoPass123!'))

        # Check children
        children = Child.query.filter_by(parent_id=parent.id).all()
        self.assertEqual(len(children), 3)
        for child in children:
            self.assertIn('[Demo Data]', child.name)

        # Check teacher assignments
        for child in children:
            teacher_ids = [a.teacher_id for a in child.assigned_teachers]
            self.assertIn(teacher.id, teacher_ids)

        # Check demo activities
        demo_acts = Activity.query.filter(Activity.title.contains('[Demo Data]')).all()
        self.assertGreaterEqual(len(demo_acts), 10)

        # Check sessions
        sessions = ActivitySession.query.all()
        self.assertGreaterEqual(len(sessions), 10)

        # Check recommendations exist
        recs = Recommendation.query.all()
        self.assertGreaterEqual(len(recs), 3)

        # Check Hindi translation coverage reporting
        self.assertIn('hindi_translated_activities', res)
        self.assertIn('english_fallback_activities', res)
        self.assertIn('category_translation_stats', res)
        self.assertEqual(res['hindi_translated_activities'], 115)
        self.assertEqual(res['english_fallback_activities'], 0)
        self.assertEqual(len(res['category_translation_stats']), 5)
        for cat_name, stats in res['category_translation_stats'].items():
            self.assertEqual(stats['hindi'], 23, f"{cat_name} must have 23 Hindi translated activities")
            self.assertEqual(stats['fallback'], 0, f"{cat_name} must have 0 English fallback activities")

    def test_ui_displays_demo_data_badge(self):
        """Verify that UI templates display the Demo Data badge for tagged activities and children."""
        # Seed demo environment
        seed_demo_data()

        parent = User.query.filter_by(email='parent@childinsight.demo').first()
        child = Child.query.filter_by(parent_id=parent.id).first()

        # 1. Check parent dashboard
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(parent.id)
            sess['_fresh'] = True

        res = self.client.get(f'/parent/dashboard?child_id={child.id}')
        self.assertEqual(res.status_code, 200)
        content = res.get_data(as_text=True)
        # Should contain styled Demo Data or Demo badge
        self.assertIn('Demo Data', content)

        # 2. Check child activity listing
        cat = child.parent.children[0]
        act_res = self.client.get(f'/child/{child.id}/categories/visual/activities')
        if act_res.status_code == 200:
            act_content = act_res.get_data(as_text=True)
            self.assertIn('Demo Data', act_content)


if __name__ == '__main__':
    unittest.main()
