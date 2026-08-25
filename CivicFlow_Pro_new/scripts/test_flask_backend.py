import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import unittest
import json

class CivicFlowBackendTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_pages_load(self):
        print("Testing page loads...")
        pages = ['/', '/login/citizen', '/login/staff']
        for page in pages:
            response = self.app.get(page)
            self.assertEqual(response.status_code, 200, f"Page {page} failed to load.")
            
    def test_protected_routes_redirect(self):
        print("Testing protected routes (should redirect)...")
        protected = ['/dashboard', '/admin_dashboard', '/submit', '/permission', '/analytics']
        for page in protected:
            response = self.app.get(page)
            self.assertEqual(response.status_code, 302, f"Protected route {page} did not redirect.")

    def test_chat_api(self):
        print("Testing AI Chatbot API...")
        response = self.app.post('/api/chat', 
                                 data=json.dumps({'message': 'pothole'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('response', data)
        self.assertTrue(len(data['response']) > 0)

    def test_ai_fallback_is_active(self):
        print("Testing AI Engine Backend Status...")
        from ai_model import analyze_complaint
        # If the environment error is active, it should return 'Heuristic (Fallback)'
        # If it's fixed, it should return 'Semantic (MPNet)'
        dept, urgency, engine, conf, alt = analyze_complaint("There is a large pothole")
        print(f"-> Active Engine: {engine}, Confidence: {conf}%")
        self.assertIsNotNone(engine)

if __name__ == '__main__':
    unittest.main(verbosity=2)
