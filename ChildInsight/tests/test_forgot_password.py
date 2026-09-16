import unittest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken


class ForgotPasswordTestCase(unittest.TestCase):
    """Automated test suite verifying the Forgot Password flow and security constraints."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create a test user
        self.user = User(
            name='Test Parent',
            email='parent.test@example.com',
            role='parent',
            is_active=True
        )
        self.user.set_password('OriginalPassword123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_page_has_forgot_password_link(self):
        """Verify the login page includes a clear link to the forgot password flow."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/forgot-password', response.data)
        self.assertIn(b'Forgot password?', response.data)

    def test_request_reset_nonexistent_email_does_not_leak_enumeration(self):
        """
        Zero user enumeration: Requesting a reset for an unknown email returns
        the exact same confirmation message and creates no tokens.
        """
        response = self.client.post('/forgot-password', data={
            'email': 'nobody@nonexistent-domain.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'If an account exists for this email address', response.data)
        # Verify no token record was created
        self.assertEqual(PasswordResetToken.query.count(), 0)
        # Verify demo mode link is NOT rendered
        self.assertNotIn(b'DEMO MODE: Simulated Email Delivery', response.data)

    def test_request_reset_inactive_user_does_not_generate_token(self):
        """Inactive accounts return the generic message but do not generate a token."""
        self.user.is_active = False
        db.session.commit()

        response = self.client.post('/forgot-password', data={
            'email': self.user.email
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'If an account exists for this email address', response.data)
        self.assertEqual(PasswordResetToken.query.count(), 0)
        self.assertNotIn(b'DEMO MODE: Simulated Email Delivery', response.data)

    def test_request_reset_valid_user_creates_token_and_displays_demo_link(self):
        """Valid active user receives generic message, token is created, and demo link is displayed."""
        response = self.client.post('/forgot-password', data={
            'email': self.user.email
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'If an account exists for this email address', response.data)
        self.assertIn(b'DEMO MODE: Simulated Email Delivery', response.data)
        self.assertIn(b'/reset-password/', response.data)

        # Confirm exactly 1 token created
        token_record = PasswordResetToken.query.filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(token_record)
        self.assertIsNone(token_record.used_at)
        self.assertFalse(token_record.is_used)
        self.assertFalse(token_record.is_expired)

    def test_multiple_reset_requests_invalidate_prior_tokens(self):
        """Requesting a reset a second time invalidates any previously pending tokens."""
        # First request
        self.client.post('/forgot-password', data={'email': self.user.email})
        first_token = PasswordResetToken.query.filter_by(user_id=self.user.id).first()
        self.assertIsNone(first_token.used_at)

        # Second request
        self.client.post('/forgot-password', data={'email': self.user.email})
        all_tokens = PasswordResetToken.query.filter_by(user_id=self.user.id).order_by(PasswordResetToken.id).all()
        self.assertEqual(len(all_tokens), 2)
        # First token should now be marked used/invalidated
        self.assertIsNotNone(all_tokens[0].used_at)
        # Second token should be active
        self.assertIsNone(all_tokens[1].used_at)

    def test_invalid_token_is_rejected(self):
        """An unrecognized token is rejected and redirected to forgot password."""
        response = self.client.get('/reset-password/totally-invalid-token-12345', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This password reset link is invalid or has expired', response.data)

    def test_expired_token_is_rejected(self):
        """Tokens older than the expiration window (30 minutes) are rejected."""
        token_record, raw_token = PasswordResetToken.create_token(self.user, expires_in_minutes=30)
        # Artificially expire the token
        token_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.session.commit()

        # Attempt to access reset page
        response = self.client.get(f'/reset-password/{raw_token}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This password reset link is invalid or has expired', response.data)

    def test_successful_password_reset_and_login(self):
        """Valid token resets password, updates hash, and allows login with new password."""
        token_record, raw_token = PasswordResetToken.create_token(self.user, expires_in_minutes=30)
        db.session.commit()

        # 1. View reset password form
        get_response = self.client.get(f'/reset-password/{raw_token}')
        self.assertEqual(get_response.status_code, 200)
        self.assertIn(b'Set New Password', get_response.data)

        # 2. Submit new valid password
        new_password = 'BrandNewSecurePassword123'
        post_response = self.client.post(f'/reset-password/{raw_token}', data={
            'password': new_password,
            'confirm_password': new_password
        }, follow_redirects=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertIn(b'Your password has been reset successfully', post_response.data)

        # 3. Verify user password was changed
        db.session.refresh(self.user)
        self.assertFalse(self.user.check_password('OriginalPassword123'))
        self.assertTrue(self.user.check_password(new_password))

        # 4. Verify token is marked used
        db.session.refresh(token_record)
        self.assertIsNotNone(token_record.used_at)
        self.assertTrue(token_record.is_used)

        # 5. Verify login with the new password works
        login_response = self.client.post('/login', data={
            'email': self.user.email,
            'password': new_password
        }, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b'Parent Portal', login_response.data)

        # 6. Verify old password no longer works
        self.client.get('/logout')
        bad_login_response = self.client.post('/login', data={
            'email': self.user.email,
            'password': 'OriginalPassword123'
        })
        self.assertEqual(bad_login_response.status_code, 200)
        self.assertIn(b'Invalid email address or password', bad_login_response.data)

    def test_single_use_token_cannot_be_reused(self):
        """Once used, the same token cannot be submitted or accessed again."""
        token_record, raw_token = PasswordResetToken.create_token(self.user, expires_in_minutes=30)
        db.session.commit()

        # First use succeeds
        self.client.post(f'/reset-password/{raw_token}', data={
            'password': 'FirstResetPassword123',
            'confirm_password': 'FirstResetPassword123'
        })

        # Second use attempt is rejected
        response = self.client.get(f'/reset-password/{raw_token}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This password reset link is invalid or has expired', response.data)

        # Attempt to submit POST again is rejected
        post_response = self.client.post(f'/reset-password/{raw_token}', data={
            'password': 'SecondResetPassword123',
            'confirm_password': 'SecondResetPassword123'
        }, follow_redirects=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertIn(b'This password reset link is invalid or has expired', post_response.data)

    def test_password_validation_enforced(self):
        """Passwords under 6 characters or mismatching confirmation are rejected."""
        token_record, raw_token = PasswordResetToken.create_token(self.user, expires_in_minutes=30)
        db.session.commit()

        # Too short (< 6 characters)
        response_short = self.client.post(f'/reset-password/{raw_token}', data={
            'password': '12345',
            'confirm_password': '12345'
        })
        self.assertEqual(response_short.status_code, 200)
        self.assertIn(b'Password must be at least 6 characters.', response_short.data)

        # Mismatch
        response_mismatch = self.client.post(f'/reset-password/{raw_token}', data={
            'password': 'ValidPassword123',
            'confirm_password': 'DifferentPassword123'
        })
        self.assertEqual(response_mismatch.status_code, 200)
        self.assertIn(b'Passwords must match', response_mismatch.data)

        # Verify password did not change
        db.session.refresh(self.user)
        self.assertTrue(self.user.check_password('OriginalPassword123'))
        # Token is still unused and valid
        db.session.refresh(token_record)
        self.assertIsNone(token_record.used_at)


if __name__ == '__main__':
    unittest.main()
