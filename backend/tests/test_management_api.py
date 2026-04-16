from datetime import datetime
import unittest
from uuid import uuid4

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User, Product, ReviewBatch, Review
from app.models.analysis import AnalysisRun


class ManagementApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.client = self.app.test_client()
        self.id_seed = 100
        self.user_id = 1
        self._seed_user()
        self.token = create_access_token(identity=str(self.user_id))
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _next_id(self):
        self.id_seed += 1
        return self.id_seed

    def _seed_user(self):
        user = User(
            id=self.user_id,
            username='tester',
            password=generate_password_hash('test123456'),
            role='analyst',
            status='active',
        )
        db.session.add(user)
        db.session.commit()

    def _create_product(self):
        product = Product(
            id=self._next_id(),
            name='测试商品',
            category='手机数码',
            platform='京东',
            created_by=self.user_id,
        )
        db.session.add(product)
        db.session.commit()
        return product.id

    def _seed_reviews(self):
        product_id = self._create_product()
        batch = ReviewBatch(
            id=self._next_id(),
            product_id=product_id,
            source_type='csv_import',
            status='completed',
            created_by=self.user_id,
            file_name='seed.csv',
            row_count=3,
            imported_count=3,
        )
        db.session.add(batch)
        db.session.commit()

        review_1 = Review(
            id=self._next_id(),
            product_id=product_id,
            batch_id=batch.id,
            external_id='r1',
            raw_content='这个商品很好，物流很快',
            cleaned_content='这个商品很好 物流很快',
            content_hash=uuid4().hex,
            rating=5,
            is_valid=True,
        )
        review_2 = Review(
            id=self._next_id(),
            product_id=product_id,
            batch_id=batch.id,
            external_id='r2',
            raw_content='包装破损，体验很差',
            cleaned_content='包装破损 体验很差',
            content_hash=uuid4().hex,
            rating=1,
            is_valid=False,
        )
        review_3 = Review(
            id=self._next_id(),
            product_id=product_id,
            batch_id=batch.id,
            external_id='r3',
            raw_content='性价比不错，值得购买',
            cleaned_content='性价比不错 值得购买',
            content_hash=uuid4().hex,
            rating=4,
            is_valid=True,
        )

        db.session.add_all([review_1, review_2, review_3])
        db.session.commit()

        return product_id, batch.id, review_1, review_2, review_3

    def _create_run(self, product_id, batch_id, status='pending'):
        run = AnalysisRun(
            id=self._next_id(),
            product_id=product_id,
            batch_id=batch_id,
            status=status,
            model_name='roberta-sentiment',
            model_version='tri-class-v1',
            started_by=self.user_id,
            started_at=datetime.utcnow() if status in {'running', 'completed', 'failed', 'canceled'} else None,
            finished_at=datetime.utcnow() if status in {'completed', 'failed', 'canceled'} else None,
        )
        db.session.add(run)
        db.session.commit()
        return run

    def test_get_reviews_supports_status_and_keyword_filters(self):
        _, _, review_1, review_2, _ = self._seed_reviews()

        default_resp = self.client.get('/api/reviews', headers=self.headers)
        self.assertEqual(default_resp.status_code, 200)
        default_payload = default_resp.get_json()
        self.assertEqual(default_payload['total'], 2)
        self.assertTrue(all(item['is_valid'] for item in default_payload['reviews']))

        deleted_resp = self.client.get('/api/reviews?status=deleted', headers=self.headers)
        self.assertEqual(deleted_resp.status_code, 200)
        deleted_payload = deleted_resp.get_json()
        self.assertEqual(deleted_payload['total'], 1)
        self.assertEqual(deleted_payload['reviews'][0]['id'], review_2.id)

        keyword_resp = self.client.get('/api/reviews?status=all&keyword=物流', headers=self.headers)
        self.assertEqual(keyword_resp.status_code, 200)
        keyword_payload = keyword_resp.get_json()
        self.assertEqual(keyword_payload['total'], 1)
        self.assertEqual(keyword_payload['reviews'][0]['id'], review_1.id)

    def test_update_review_validity_single_and_bulk(self):
        _, _, review_1, _, review_3 = self._seed_reviews()

        single_resp = self.client.patch(
            f'/api/reviews/{review_1.id}/validity',
            headers=self.headers,
            json={'is_valid': False},
        )
        self.assertEqual(single_resp.status_code, 200)
        self.assertFalse(Review.query.get(review_1.id).is_valid)

        bulk_resp = self.client.post(
            '/api/reviews/bulk-validity',
            headers=self.headers,
            json={
                'review_ids': [review_1.id, review_3.id],
                'is_valid': True,
            },
        )
        self.assertEqual(bulk_resp.status_code, 200)
        bulk_payload = bulk_resp.get_json()
        self.assertEqual(bulk_payload['updated_count'], 2)
        self.assertEqual(bulk_payload['missing_ids'], [])
        self.assertTrue(Review.query.get(review_1.id).is_valid)
        self.assertTrue(Review.query.get(review_3.id).is_valid)

    def test_cancel_and_retry_analysis_run(self):
        product_id, batch_id, *_ = self._seed_reviews()
        run = self._create_run(product_id, batch_id, status='pending')

        cancel_resp = self.client.post(
            f'/api/analysis/runs/{run.id}/cancel',
            headers=self.headers,
        )
        self.assertEqual(cancel_resp.status_code, 200)
        canceled_payload = cancel_resp.get_json()['run']
        self.assertEqual(canceled_payload['status'], 'canceled')

        retry_resp = self.client.post(
            f'/api/analysis/runs/{run.id}/retry',
            headers=self.headers,
        )
        self.assertEqual(retry_resp.status_code, 201)
        retry_payload = retry_resp.get_json()
        self.assertEqual(retry_payload['source_run_id'], run.id)
        self.assertEqual(retry_payload['run']['status'], 'pending')
        self.assertNotEqual(retry_payload['run']['id'], run.id)

    def test_get_analysis_runs_supports_status_filter(self):
        product_id, batch_id, *_ = self._seed_reviews()
        self._create_run(product_id, batch_id, status='pending')
        canceled_run = self._create_run(product_id, batch_id, status='canceled')

        runs_resp = self.client.get('/api/analysis/runs?status=canceled', headers=self.headers)
        self.assertEqual(runs_resp.status_code, 200)
        payload = runs_resp.get_json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['runs'][0]['id'], canceled_run.id)
        self.assertEqual(payload['runs'][0]['status'], 'canceled')


if __name__ == '__main__':
    unittest.main()
