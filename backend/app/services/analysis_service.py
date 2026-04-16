"""
分析服务 - 执行NLP分析任务
"""

from datetime import datetime
import logging

from flask import current_app

from app import db
from app.models import Review
from app.models.analysis import (
    AnalysisRun,
    ReviewSentiment,
    AspectMention,
    IssueTopic,
    IssueTopicReview,
)
from app.nlp.analyzer import SentimentAnalyzer, AspectExtractor, IssueExtractor
from app.nlp.model_registry import resolve_sentiment_model_path
from app.nlp.text_processor import TextProcessor

logger = logging.getLogger(__name__)


class AnalysisCanceledError(Exception):
    """分析任务被取消。"""


class AnalysisService:
    """分析服务"""

    SENTIMENT_CHUNK_SIZE = 128
    SENTIMENT_BATCH_SIZE = 32
    ASPECT_COMMIT_INTERVAL = 100
    ISSUE_COMMIT_INTERVAL = 10

    def __init__(self):
        self.text_processor = TextProcessor()
        self.sentiment_analyzer = None
        self.aspect_extractor = AspectExtractor()
        self.issue_extractor = IssueExtractor()

    def run_analysis(self, run_id: int):
        """
        执行分析任务

        Args:
            run_id: 分析任务ID
        """
        run = AnalysisRun.query.get(run_id)
        if not run:
            raise ValueError(f'分析任务 {run_id} 不存在')

        if run.status == 'canceled':
            if not run.finished_at:
                run.finished_at = datetime.utcnow()
            self._set_progress(
                run,
                stage='canceled',
                message='任务已取消',
                commit=True,
            )
            logger.info(f'分析任务 {run_id} 已取消，跳过执行')
            return

        if run.status not in {'pending', 'running'}:
            raise ValueError(f'分析任务 {run_id} 状态为 {run.status}，不允许重复执行')

        try:
            # 更新状态
            run.status = 'running'
            run.started_at = run.started_at or datetime.utcnow()
            run.error_message = None
            self._set_progress(
                run,
                stage='starting',
                message='正在初始化分析任务',
                commit=False,
            )
            db.session.commit()

            logger.info(f'开始分析任务 {run_id}')

            # 初始化情感分析器
            if not self.sentiment_analyzer:
                model_path = resolve_sentiment_model_path(
                    model_name=run.model_name,
                    model_folder=current_app.config.get('MODEL_FOLDER'),
                    fallback_model_name=current_app.config.get('SENTIMENT_MODEL_FALLBACK'),
                    explicit_model_path=(run.config_json or {}).get('model_path'),
                )
                logger.info(f'情感分析模型解析为: {model_path}')
                self.sentiment_analyzer = SentimentAnalyzer(model_path)

            # 获取待分析评论
            query = Review.query.filter_by(
                product_id=run.product_id,
                is_valid=True
            )
            if run.batch_id:
                query = query.filter_by(batch_id=run.batch_id)

            reviews = query.all()
            logger.info(f'找到 {len(reviews)} 条评论待分析')

            if not reviews:
                raise ValueError('没有找到待分析的评论')

            self._raise_if_canceled(run_id)

            # 1. 情感分析
            self._set_progress_by_id(run_id, 'sentiment', '正在进行情感分析')
            self._analyze_sentiment(run_id, reviews)

            # 2. 功能点提取
            self._set_progress_by_id(run_id, 'aspects', '正在提取功能点')
            self._extract_aspects(run_id, reviews)

            # 3. 问题挖掘
            self._set_progress_by_id(run_id, 'issues', '正在挖掘负面问题')
            self._extract_issues(run_id, reviews)

            self._raise_if_canceled(run_id)

            # 更新状态
            run = AnalysisRun.query.get(run_id)
            if not run:
                raise ValueError(f'分析任务 {run_id} 不存在')

            run.status = 'completed'
            run.finished_at = datetime.utcnow()
            run.error_message = None
            self._set_progress(
                run,
                stage='completed',
                message='分析任务已完成',
                commit=False,
            )
            db.session.commit()

            logger.info(f'分析任务 {run_id} 完成')

        except AnalysisCanceledError:
            self._mark_run_canceled(run_id)
            logger.info(f'分析任务 {run_id} 已协作式取消')

        except Exception as e:
            logger.error(f'分析任务 {run_id} 失败: {str(e)}')
            run = AnalysisRun.query.get(run_id)
            if run and run.status == 'canceled':
                if not run.finished_at:
                    run.finished_at = datetime.utcnow()
                self._set_progress(
                    run,
                    stage='canceled',
                    message='任务已取消',
                    commit=False,
                )
                db.session.commit()
                logger.info(f'分析任务 {run_id} 在异常处理中保持取消状态')
                return

            if run:
                run.status = 'failed'
                run.error_message = str(e)
                run.finished_at = datetime.utcnow()
                self._set_progress(
                    run,
                    stage='failed',
                    message=f'任务失败: {str(e)}',
                    commit=False,
                )
                db.session.commit()
            raise

    def _set_progress(self, run: AnalysisRun, stage: str, message: str, commit: bool = False):
        run.progress_stage = stage
        run.progress_message = message
        run.progress_updated_at = datetime.utcnow()
        if commit:
            db.session.commit()

    def _set_progress_by_id(self, run_id: int, stage: str, message: str):
        run = AnalysisRun.query.get(run_id)
        if not run:
            return
        self._set_progress(run, stage=stage, message=message, commit=False)
        db.session.commit()

    def _raise_if_canceled(self, run_id: int):
        run = AnalysisRun.query.get(run_id)
        if not run:
            raise ValueError(f'分析任务 {run_id} 不存在')
        if run.status == 'canceled':
            raise AnalysisCanceledError(f'分析任务 {run_id} 已被取消')
        return run

    def _mark_run_canceled(self, run_id: int):
        run = AnalysisRun.query.get(run_id)
        if not run:
            return
        run.status = 'canceled'
        if not run.finished_at:
            run.finished_at = datetime.utcnow()
        if not run.error_message:
            run.error_message = '任务已取消'
        self._set_progress(
            run,
            stage='canceled',
            message='任务已取消',
            commit=False,
        )
        db.session.commit()

    def _analyze_sentiment(self, run_id: int, reviews: list):
        """情感分析"""
        logger.info('开始情感分析...')

        for start in range(0, len(reviews), self.SENTIMENT_CHUNK_SIZE):
            self._raise_if_canceled(run_id)

            chunk_reviews = reviews[start:start + self.SENTIMENT_CHUNK_SIZE]
            texts = [review.cleaned_content or review.raw_content for review in chunk_reviews]
            results = self.sentiment_analyzer.batch_predict(texts, batch_size=self.SENTIMENT_BATCH_SIZE)

            for review, result in zip(chunk_reviews, results):
                sentiment = ReviewSentiment(
                    run_id=run_id,
                    review_id=review.id,
                    label=result['label'],
                    confidence=result['confidence'],
                    positive_prob=result['probabilities']['positive'],
                    neutral_prob=result['probabilities']['neutral'],
                    negative_prob=result['probabilities']['negative']
                )
                db.session.add(sentiment)

            db.session.commit()

        logger.info(f'情感分析完成，处理 {len(reviews)} 条评论')

    def _extract_aspects(self, run_id: int, reviews: list):
        """功能点提取"""
        logger.info('开始功能点提取...')

        for idx, review in enumerate(reviews, start=1):
            text = review.cleaned_content or review.raw_content

            # 分词
            tokens = self.text_processor.tokenize(text)

            # 提取功能点
            aspects = self.aspect_extractor.extract(text, tokens)

            # 获取该评论的情感
            sentiment = ReviewSentiment.query.filter_by(
                run_id=run_id,
                review_id=review.id
            ).first()

            # 保存结果
            for aspect in aspects:
                mention = AspectMention(
                    run_id=run_id,
                    review_id=review.id,
                    aspect_name=aspect['aspect'],
                    normalized_aspect=aspect['normalized_aspect'],
                    start_offset=aspect['start'],
                    end_offset=aspect['end'],
                    confidence=aspect['confidence'],
                    linked_sentiment=sentiment.label if sentiment else None
                )
                db.session.add(mention)

            if idx % self.ASPECT_COMMIT_INTERVAL == 0:
                db.session.commit()
                self._raise_if_canceled(run_id)

        db.session.commit()
        self._raise_if_canceled(run_id)

        logger.info('功能点提取完成')

    def _extract_issues(self, run_id: int, reviews: list):
        """问题挖掘"""
        logger.info('开始问题挖掘...')

        self._raise_if_canceled(run_id)

        # 筛选负面评论
        negative_sentiments = ReviewSentiment.query.filter_by(
            run_id=run_id,
            label='negative'
        ).all()

        if not negative_sentiments:
            logger.info('没有负面评论，跳过问题挖掘')
            return

        # 获取负面评论文本
        negative_review_ids = [sentiment.review_id for sentiment in negative_sentiments]
        negative_reviews = Review.query.filter(
            Review.id.in_(negative_review_ids)
        ).all()

        negative_texts = [
            review.cleaned_content or review.raw_content
            for review in negative_reviews
        ]

        # 提取问题关键词
        issues = self.issue_extractor.extract_keywords(negative_texts, top_k=20)

        # 保存结果
        for idx, issue in enumerate(issues, start=1):
            self._raise_if_canceled(run_id)

            related_reviews = [
                review for review in negative_reviews
                if issue['keyword'] in (review.cleaned_content or review.raw_content)
            ]

            if not related_reviews:
                continue

            topic = IssueTopic(
                run_id=run_id,
                keyword=issue['keyword'],
                normalized_keyword=issue['keyword'],
                score=issue['score'],
                frequency=issue['frequency'],
                representative_review_id=related_reviews[0].id
            )
            db.session.add(topic)
            db.session.flush()

            for review in related_reviews[:10]:
                link = IssueTopicReview(
                    issue_topic_id=topic.id,
                    review_id=review.id,
                    evidence_text=(review.cleaned_content or review.raw_content)[:500]
                )
                db.session.add(link)

            if idx % self.ISSUE_COMMIT_INTERVAL == 0:
                db.session.commit()

        db.session.commit()
        self._raise_if_canceled(run_id)

        logger.info(f'问题挖掘完成，提取 {len(issues)} 个问题关键词')
