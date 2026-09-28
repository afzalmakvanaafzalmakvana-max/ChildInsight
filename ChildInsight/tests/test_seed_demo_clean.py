import unittest
from app import create_app, db
from app.models.user import User
from app.models.notification import Notification
from app.models.child_teacher_access import ChildTeacherAccess
from app.utils.seed_data import seed_demo_data
from run import app as cli_app, run_seed_demo


class SeedDemoCleanTestCase(unittest.TestCase):
    """
    Test suite for Bug #3: Legacy .local account cleanup and seed-demo safeguard.
    Verifies:
    1. Fresh seed-demo run creates only current .demo accounts and zero .local accounts.
    2. Detection and warning when legacy .local accounts exist in the database without --clean.
    3. Safe removal of legacy .local accounts and associated orphan records when --clean is passed.
    4. CLI seed-demo execution with and without --clean flag.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_fresh_seed_demo_creates_zero_local_accounts(self):
        """A fresh seed-demo execution must create current .demo accounts and zero .local accounts."""
        res = seed_demo_data(fresh=True, clean=True)

        # Confirm verified demo accounts exist
        admin = User.query.filter_by(email='admin@childinsight.demo').first()
        teacher = User.query.filter_by(email='teacher@childinsight.demo').first()
        parent = User.query.filter_by(email='parent@childinsight.demo').first()

        self.assertIsNotNone(admin)
        self.assertIsNotNone(teacher)
        self.assertIsNotNone(parent)

        # Confirm passwords work
        self.assertTrue(admin.check_password('DemoPass123!'))
        self.assertTrue(teacher.check_password('DemoPass123!'))
        self.assertTrue(parent.check_password('DemoPass123!'))

        # Confirm zero .local accounts exist
        local_count = User.query.filter(User.email.like('%.local')).count()
        self.assertEqual(local_count, 0, "No accounts with .local suffix should exist after seeding.")
        self.assertIsNone(res['legacy_warning'])

    def test_seed_demo_warns_when_legacy_local_account_found(self):
        """seed_demo_data logs a warning and returns legacy info when a .local account exists without clean=True."""
        # Inject a legacy account
        legacy_user = User(
            name='Legacy Admin',
            email='admin@childinsight.local',
            role='admin',
            is_active=True
        )
        legacy_user.set_password('AdminPass123!')
        db.session.add(legacy_user)
        db.session.commit()

        # Run seed without clean flag
        res = seed_demo_data(fresh=False, clean=False)

        self.assertIn('admin@childinsight.local', res['legacy_users_found'])
        self.assertIsNotNone(res['legacy_warning'])
        self.assertIn('admin@childinsight.local', res['legacy_warning'])
        self.assertIn('--clean', res['legacy_warning'])
        self.assertEqual(res['cleaned_legacy_users'], [])

        # Account should still exist since clean was False
        persisted = User.query.filter_by(email='admin@childinsight.local').first()
        self.assertIsNotNone(persisted)

    def test_seed_demo_clean_removes_legacy_local_accounts_safely(self):
        """seed_demo_data with clean=True safely purges legacy .local accounts and their orphan records."""
        # Inject legacy accounts and related test rows
        legacy_admin = User(
            name='Legacy Admin',
            email='admin@childinsight.local',
            role='admin',
            is_active=True
        )
        legacy_admin.set_password('AdminPass123!')

        legacy_parent = User(
            name='Legacy Parent',
            email='test@demo.local',
            role='parent',
            is_active=True
        )
        legacy_parent.set_password('TestPass123!')

        db.session.add_all([legacy_admin, legacy_parent])
        db.session.commit()

        # Add a notification referencing the legacy user
        notif = Notification(
            user_id=legacy_admin.id,
            message='Testing legacy cleanup cascade',
            notification_type=Notification.TYPE_GENERAL
        )
        db.session.add(notif)
        db.session.commit()

        # Run seed with clean=True
        res = seed_demo_data(fresh=False, clean=True)

        self.assertIn('admin@childinsight.local', res['cleaned_legacy_users'])
        self.assertIn('test@demo.local', res['cleaned_legacy_users'])
        self.assertIsNone(res['legacy_warning'])

        # Both legacy users must be gone
        local_users = User.query.filter(User.email.like('%.local')).all()
        self.assertEqual(len(local_users), 0)

        # Related notification must be removed
        notifs = Notification.query.filter_by(user_id=legacy_admin.id).all()
        self.assertEqual(len(notifs), 0)

        # Current .demo accounts must still be fully intact
        self.assertIsNotNone(User.query.filter_by(email='admin@childinsight.demo').first())
        self.assertIsNotNone(User.query.filter_by(email='teacher@childinsight.demo').first())
        self.assertIsNotNone(User.query.filter_by(email='parent@childinsight.demo').first())

    def test_run_seed_demo_output_with_clean_and_warn(self):
        """run_seed_demo outputs clear messages for warning and cleanup."""
        legacy = User(
            name='Old User',
            email='old@childinsight.local',
            role='admin',
            is_active=True
        )
        legacy.set_password('Pass123!')
        db.session.add(legacy)
        db.session.commit()

        # Test warning display
        res_warn = run_seed_demo(fresh=False, clean=False)
        self.assertIsNotNone(res_warn['legacy_warning'])

        # Test cleanup display
        res_clean = run_seed_demo(fresh=False, clean=True)
        self.assertIn('old@childinsight.local', res_clean['cleaned_legacy_users'])
        self.assertEqual(User.query.filter(User.email.like('%.local')).count(), 0)

    def test_cli_runner_seed_demo_clean(self):
        """Flask CLI runner invokes seed-demo with --clean flag without error."""
        legacy = User(
            name='CLI Legacy',
            email='cli_legacy@childinsight.local',
            role='admin',
            is_active=True
        )
        legacy.set_password('Pass123!')
        db.session.add(legacy)
        db.session.commit()

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli_app.cli.commands['seed-demo'], ['--clean'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Legacy Cleanup', result.output)
        self.assertEqual(User.query.filter(User.email.like('%.local')).count(), 0)


if __name__ == '__main__':
    unittest.main()
