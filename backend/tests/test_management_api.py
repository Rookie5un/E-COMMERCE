from datetime import datetime
import unittest
from unittest.mock import patch
from uuid import uuid4

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User, Product, ReviewBatch, Review
from app.models.analysis import AnalysisRun
from app.services.analysis_dispatcher import AnalysisDispatchError


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
            role='admin',
            status='active',
        )
        db.session.add(user)
        db.session.commit()

    def _set_user_role(self, role):
        user = db.session.get(User, self.user_id)
        user.role = role
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

    def test_create_analysis_run_dispatches_queue(self):
        product_id, batch_id, *_ = self._seed_reviews()

        with patch('app.api.analysis.dispatch_analysis_run') as mock_dispatch:
            resp = self.client.post(
                '/api/analysis/run',
                headers=self.headers,
                json={'product_id': product_id, 'batch_id': batch_id},
            )

        self.assertEqual(resp.status_code, 201)
        payload = resp.get_json()
        self.assertEqual(payload['run']['status'], 'pending')
        mock_dispatch.assert_called_once_with(payload['run']['id'])

    def test_create_analysis_run_returns_error_when_dispatch_fails(self):
        product_id, batch_id, *_ = self._seed_reviews()

        def fail_dispatch(run_id):
            run = db.session.get(AnalysisRun, run_id)
            now = datetime.utcnow()
            run.status = 'failed'
            run.error_message = '任务投递失败: redis down'
            run.finished_at = now
            run.progress_stage = 'failed'
            run.progress_message = run.error_message
            run.progress_updated_at = now
            db.session.commit()
            raise AnalysisDispatchError('redis down')

        with patch('app.api.analysis.dispatch_analysis_run', side_effect=fail_dispatch):
            resp = self.client.post(
                '/api/analysis/run',
                headers=self.headers,
                json={'product_id': product_id, 'batch_id': batch_id},
            )

        self.assertEqual(resp.status_code, 503)
        payload = resp.get_json()
        self.assertEqual(payload['error'], '分析任务投递失败')
        self.assertEqual(payload['run']['status'], 'failed')

    def test_dispatcher_falls_back_to_thread_when_celery_fails(self):
        from app.services import analysis_dispatcher

        self.app.config.update(
            TESTING=False,
            ANALYSIS_TASK_BACKEND='celery',
            ANALYSIS_THREAD_FALLBACK=True,
            ANALYSIS_QUEUE_NAME='analysis',
        )

        with patch.object(
            analysis_dispatcher,
            '_enqueue_celery_run',
            side_effect=RuntimeError('redis down'),
        ), patch.object(analysis_dispatcher, '_start_analysis_thread') as mock_thread:
            result = analysis_dispatcher.dispatch_analysis_run(123)

        self.assertEqual(result.backend, 'thread')
        self.assertTrue(result.fallback_used)
        mock_thread.assert_called_once_with(123)

    def test_dispatcher_marks_failed_when_fallback_disabled(self):
        from app.services import analysis_dispatcher

        product_id, batch_id, *_ = self._seed_reviews()
        run = self._create_run(product_id, batch_id, status='pending')
        self.app.config.update(
            TESTING=False,
            ANALYSIS_TASK_BACKEND='celery',
            ANALYSIS_THREAD_FALLBACK=False,
            ANALYSIS_QUEUE_NAME='analysis',
        )

        with patch.object(
            analysis_dispatcher,
            '_enqueue_celery_run',
            side_effect=RuntimeError('redis down'),
        ):
            with self.assertRaises(AnalysisDispatchError):
                analysis_dispatcher.dispatch_analysis_run(run.id)

        db.session.expire_all()
        failed_run = db.session.get(AnalysisRun, run.id)
        self.assertEqual(failed_run.status, 'failed')
        self.assertEqual(failed_run.progress_stage, 'failed')
        self.assertIn('任务投递失败', failed_run.error_message)

    def test_analysis_service_claims_pending_and_skips_duplicate_runs(self):
        from app.services.analysis_service import AnalysisService

        product_id, batch_id, *_ = self._seed_reviews()
        pending_run = self._create_run(product_id, batch_id, status='pending')
        service = AnalysisService()
        observed_statuses = []

        def observe_running_status(run_id, reviews):
            db.session.expire_all()
            observed_statuses.append(db.session.get(AnalysisRun, pending_run.id).status)

        with patch(
            'app.services.analysis_service.resolve_sentiment_model_path',
            return_value='mock-model',
        ), patch('app.services.analysis_service.SentimentAnalyzer'), patch.object(
            service,
            '_analyze_sentiment',
            side_effect=observe_running_status,
        ) as mock_sentiment, patch.object(service, '_extract_aspects'), patch.object(
            service,
            '_extract_issues',
        ):
            service.run_analysis(pending_run.id)

        self.assertEqual(observed_statuses, ['running'])
        mock_sentiment.assert_called_once()
        db.session.expire_all()
        self.assertEqual(db.session.get(AnalysisRun, pending_run.id).status, 'completed')

        for status in ['running', 'completed', 'failed', 'canceled']:
            skipped_run = self._create_run(product_id, batch_id, status=status)
            service = AnalysisService()
            with patch.object(service, '_analyze_sentiment') as mock_sentiment:
                service.run_analysis(skipped_run.id)
            mock_sentiment.assert_not_called()

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

    def test_analyst_can_only_view_dashboard_support_data(self):
        product_id, batch_id, *_ = self._seed_reviews()
        pending_run = self._create_run(product_id, batch_id, status='pending')
        self._create_run(product_id, batch_id, status='completed')
        self._set_user_role('analyst')

        products_resp = self.client.get('/api/products', headers=self.headers)
        self.assertEqual(products_resp.status_code, 200)

        summary_resp = self.client.get(
            f'/api/analysis/summary?product_id={product_id}',
            headers=self.headers,
        )
        self.assertEqual(summary_resp.status_code, 200)

        pending_summary_resp = self.client.get(
            f'/api/analysis/summary?run_id={pending_run.id}',
            headers=self.headers,
        )
        self.assertEqual(pending_summary_resp.status_code, 403)

    def test_analyst_cannot_access_management_endpoints(self):
        product_id, batch_id, review_1, *_ = self._seed_reviews()
        run = self._create_run(product_id, batch_id, status='pending')
        self._set_user_role('analyst')

        blocked_responses = [
            self.client.post('/api/products', headers=self.headers, json={
                'name': '新商品',
                'category': '手机数码',
                'platform': '京东',
            }),
            self.client.get(f'/api/products/{product_id}', headers=self.headers),
            self.client.get('/api/reviews', headers=self.headers),
            self.client.patch(
                f'/api/reviews/{review_1.id}/validity',
                headers=self.headers,
                json={'is_valid': False},
            ),
            self.client.post(
                '/api/analysis/run',
                headers=self.headers,
                json={'product_id': product_id, 'batch_id': batch_id},
            ),
            self.client.get('/api/analysis/runs', headers=self.headers),
            self.client.post(
                f'/api/analysis/runs/{run.id}/cancel',
                headers=self.headers,
            ),
        ]

        for response in blocked_responses:
            self.assertEqual(response.status_code, 403)

    def test_public_register_cannot_create_admin_user(self):
        resp = self.client.post('/api/auth/register', json={
            'username': 'new_admin',
            'password': 'test123456',
            'role': 'admin',
        })

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()['user']['role'], 'analyst')
        self.assertEqual(User.query.filter_by(username='new_admin').one().role, 'analyst')


if __name__ == '__main__':
    unittest.main()
