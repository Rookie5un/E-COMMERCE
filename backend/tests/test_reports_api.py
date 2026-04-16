from datetime import datetime
import tempfile
import unittest
from uuid import uuid4

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Product, Review, ReviewBatch, User
from app.models.analysis import AnalysisRun, AspectMention, IssueTopic, ReviewSentiment


class ReportsApiTestCase(unittest.TestCase):
    def setUp(self):
        self.report_dir = tempfile.TemporaryDirectory()
        self.app = create_app('testing')
        self.app.config['REPORT_FOLDER'] = self.report_dir.name

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
        self.report_dir.cleanup()

    def _next_id(self):
        self.id_seed += 1
        return self.id_seed

    def _seed_user(self):
        user = User(
            id=self.user_id,
            username='report_tester',
            password=generate_password_hash('test123456'),
            role='analyst',
            status='active',
        )
        db.session.add(user)
        db.session.commit()

    def _seed_completed_run_with_results(self):
        product = Product(
            id=self._next_id(),
            name='测试手机',
            category='手机数码',
            platform='京东',
            created_by=self.user_id,
        )
        db.session.add(product)
        db.session.commit()

        batch = ReviewBatch(
            id=self._next_id(),
            product_id=product.id,
            source_type='csv_import',
            status='completed',
            created_by=self.user_id,
            file_name='test.csv',
            row_count=2,
            imported_count=2,
        )
        db.session.add(batch)
        db.session.commit()

        review_1 = Review(
            id=self._next_id(),
            product_id=product.id,
            batch_id=batch.id,
            external_id='r1',
            raw_content='续航很好，拍照清晰',
            cleaned_content='续航很好 拍照清晰',
            content_hash=uuid4().hex,
            rating=5,
            is_valid=True,
        )
        review_2 = Review(
            id=self._next_id(),
            product_id=product.id,
            batch_id=batch.id,
            external_id='r2',
            raw_content='手机发热，电池掉电快',
            cleaned_content='手机发热 电池掉电快',
            content_hash=uuid4().hex,
            rating=2,
            is_valid=True,
        )
        db.session.add_all([review_1, review_2])
        db.session.commit()

        run = AnalysisRun(
            id=self._next_id(),
            product_id=product.id,
            batch_id=batch.id,
            status='completed',
            model_name='roberta-sentiment',
            model_version='tri-class-v1',
            started_by=self.user_id,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()

        sentiments = [
            ReviewSentiment(
                id=self._next_id(),
                run_id=run.id,
                review_id=review_1.id,
                label='positive',
                confidence=0.95,
                positive_prob=0.95,
                neutral_prob=0.03,
                negative_prob=0.02,
            ),
            ReviewSentiment(
                id=self._next_id(),
                run_id=run.id,
                review_id=review_2.id,
                label='negative',
                confidence=0.92,
                positive_prob=0.04,
                neutral_prob=0.04,
                negative_prob=0.92,
            ),
        ]
        db.session.add_all(sentiments)

        aspects = [
            AspectMention(
                id=self._next_id(),
                run_id=run.id,
                review_id=review_1.id,
                aspect_name='续航',
                normalized_aspect='电池',
                linked_sentiment='positive',
                confidence=0.87,
            ),
            AspectMention(
                id=self._next_id(),
                run_id=run.id,
                review_id=review_2.id,
                aspect_name='发热',
                normalized_aspect='发热',
                linked_sentiment='negative',
                confidence=0.91,
            ),
        ]
        db.session.add_all(aspects)

        issue = IssueTopic(
            id=self._next_id(),
            run_id=run.id,
            keyword='发热',
            normalized_keyword='发热',
            score=1.23,
            frequency=3,
            representative_review_id=review_2.id,
        )
        db.session.add(issue)
        db.session.commit()

        return run

    def test_create_report_generates_pdf_path(self):
        run = self._seed_completed_run_with_results()

        response = self.client.post(
            '/api/reports',
            headers=self.headers,
            json={'run_id': run.id},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        report = payload['report']
        self.assertTrue(report.get('pdf_path'))

        pdf_path = report['pdf_path']
        with open(pdf_path, 'rb') as pdf_file:
            self.assertEqual(pdf_file.read(4), b'%PDF')

    def test_download_report_returns_pdf_file(self):
        run = self._seed_completed_run_with_results()
        create_resp = self.client.post(
            '/api/reports',
            headers=self.headers,
            json={'run_id': run.id},
        )
        self.assertEqual(create_resp.status_code, 201)
        report_id = create_resp.get_json()['report']['id']

        response = self.client.get(
            f'/api/reports/{report_id}/download',
            headers=self.headers,
        )

        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/pdf')
            self.assertTrue(response.data.startswith(b'%PDF'))
        finally:
            response.close()


if __name__ == '__main__':
    unittest.main()
