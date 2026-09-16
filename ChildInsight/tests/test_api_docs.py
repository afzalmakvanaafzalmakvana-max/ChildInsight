"""
Automated tests for ChildInsight REST API Documentation and Explorer.
Validates /api/openapi.json specification and /api/docs Swagger UI explorer.
"""
import unittest
from app import create_app, db
from app.models.user import User


class ApiDocsTestCase(unittest.TestCase):
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

    def test_openapi_json_returns_valid_spec(self):
        """GET /api/openapi.json should return 200 and valid OpenAPI 3.0.3 schema."""
        response = self.client.get('/api/openapi.json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

        data = response.get_json()
        self.assertEqual(data.get('openapi'), '3.0.3')
        self.assertIn('info', data)
        self.assertEqual(data['info'].get('title'), 'ChildInsight REST API')
        self.assertIn('paths', data)

        # Verify all key routes are represented in the OpenAPI spec
        paths = data['paths']
        expected_paths = [
            '/health',
            '/auth/status',
            '/children',
            '/children/{child_id}',
            '/activities',
            '/activities/{activity_id}',
            '/sessions',
            '/sessions/{session_id}',
            '/analytics/{child_id}',
            '/progress/{child_id}',
            '/recommendations/{child_id}',
            '/notifications',
            '/notifications/{notification_id}/read',
            '/notifications/mark-all-read'
        ]
        for path in expected_paths:
            self.assertIn(path, paths, f"Expected {path} to be documented in OpenAPI spec")

    def test_api_docs_ui_returns_swagger_html(self):
        """GET /api/docs should return 200 OK with Swagger UI embedded page."""
        response = self.client.get('/api/docs')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn('ChildInsight REST API Explorer', html)
        self.assertIn('swagger-ui', html)
        self.assertIn('swagger-ui-bundle.js', html)
        self.assertIn('/api/openapi.json', html)

    def test_existing_api_health_endpoint_intact(self):
        """Verify /api/health still functions normally."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('service'), 'ChildInsight API')


if __name__ == '__main__':
    unittest.main()
