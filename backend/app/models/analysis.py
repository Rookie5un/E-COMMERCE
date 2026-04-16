from datetime import datetime
from app import db


class AnalysisRun(db.Model):
    """分析任务模型"""
    __tablename__ = 'analysis_runs'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_id = db.Column(db.BigInteger, db.ForeignKey('review_batches.id', ondelete='SET NULL'), index=True)
    status = db.Column(
        db.Enum('pending', 'running', 'completed', 'failed', 'canceled'),
        nullable=False,
        default='pending',
        index=True
    )
    progress_stage = db.Column(db.String(50), index=True)
    progress_message = db.Column(db.Text)
    progress_updated_at = db.Column(db.DateTime, index=True)
    model_name = db.Column(db.String(100), nullable=False)
    model_version = db.Column(db.String(50), nullable=False)
    config_json = db.Column(db.JSON)
    started_by = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='SET NULL'))
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 关系
    product = db.relationship('Product', back_populates='analysis_runs')
    batch = db.relationship('ReviewBatch', back_populates='analysis_runs')
    starter = db.relationship('User', back_populates='analysis_runs')
    sentiments = db.relationship('ReviewSentiment', back_populates='run', cascade='all, delete-orphan')
    aspect_mentions = db.relationship('AspectMention', back_populates='run', cascade='all, delete-orphan')
    issue_topics = db.relationship('IssueTopic', back_populates='run', cascade='all, delete-orphan')
    reports = db.relationship('Report', back_populates='run', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'batch_id': self.batch_id,
            'status': self.status,
            'progress_stage': self.progress_stage,
            'progress_message': self.progress_message,
            'progress_updated_at': self.progress_updated_at.isoformat() if self.progress_updated_at else None,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'config_json': self.config_json,
            'started_by': self.started_by,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ReviewSentiment(db.Model):
    """情感分析结果模型"""
    __tablename__ = 'review_sentiments'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    run_id = db.Column(db.BigInteger, db.ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    review_id = db.Column(db.BigInteger, db.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, index=True)
    label = db.Column(db.Enum('positive', 'neutral', 'negative'), nullable=False, index=True)
    confidence = db.Column(db.Numeric(5, 4))
    positive_prob = db.Column(db.Numeric(5, 4))
    neutral_prob = db.Column(db.Numeric(5, 4))
    negative_prob = db.Column(db.Numeric(5, 4))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    run = db.relationship('AnalysisRun', back_populates='sentiments')
    review = db.relationship('Review', back_populates='sentiments')

    __table_args__ = (
        db.UniqueConstraint('run_id', 'review_id', name='uk_run_review'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'run_id': self.run_id,
            'review_id': self.review_id,
            'label': self.label,
            'confidence': float(self.confidence) if self.confidence else None,
            'positive_prob': float(self.positive_prob) if self.positive_prob else None,
            'neutral_prob': float(self.neutral_prob) if self.neutral_prob else None,
            'negative_prob': float(self.negative_prob) if self.negative_prob else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AspectMention(db.Model):
    """功能点提及模型"""
    __tablename__ = 'aspect_mentions'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    run_id = db.Column(db.BigInteger, db.ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    review_id = db.Column(db.BigInteger, db.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, index=True)
    aspect_name = db.Column(db.String(100), nullable=False)
    normalized_aspect = db.Column(db.String(100), nullable=False, index=True)
    start_offset = db.Column(db.Integer)
    end_offset = db.Column(db.Integer)
    confidence = db.Column(db.Numeric(5, 4))
    linked_sentiment = db.Column(db.Enum('positive', 'neutral', 'negative'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    run = db.relationship('AnalysisRun', back_populates='aspect_mentions')
    review = db.relationship('Review', back_populates='aspect_mentions')

    def to_dict(self):
        return {
            'id': self.id,
            'run_id': self.run_id,
            'review_id': self.review_id,
            'aspect_name': self.aspect_name,
            'normalized_aspect': self.normalized_aspect,
            'start_offset': self.start_offset,
            'end_offset': self.end_offset,
            'confidence': float(self.confidence) if self.confidence else None,
            'linked_sentiment': self.linked_sentiment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class IssueTopic(db.Model):
    """负面问题主题模型"""
    __tablename__ = 'issue_topics'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    run_id = db.Column(db.BigInteger, db.ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    keyword = db.Column(db.String(100), nullable=False)
    normalized_keyword = db.Column(db.String(100), nullable=False, index=True)
    score = db.Column(db.Numeric(8, 4))
    frequency = db.Column(db.Integer, default=0, index=True)
    representative_review_id = db.Column(db.BigInteger, db.ForeignKey('reviews.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    run = db.relationship('AnalysisRun', back_populates='issue_topics')
    representative_review = db.relationship('Review', foreign_keys=[representative_review_id])
    related_reviews = db.relationship('IssueTopicReview', back_populates='issue_topic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'run_id': self.run_id,
            'keyword': self.keyword,
            'normalized_keyword': self.normalized_keyword,
            'score': float(self.score) if self.score else None,
            'frequency': self.frequency,
            'representative_review_id': self.representative_review_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class IssueTopicReview(db.Model):
    """问题与评论关联模型"""
    __tablename__ = 'issue_topic_reviews'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    issue_topic_id = db.Column(db.BigInteger, db.ForeignKey('issue_topics.id', ondelete='CASCADE'), nullable=False, index=True)
    review_id = db.Column(db.BigInteger, db.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, index=True)
    evidence_text = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    issue_topic = db.relationship('IssueTopic', back_populates='related_reviews')
    review = db.relationship('Review')

    __table_args__ = (
        db.UniqueConstraint('issue_topic_id', 'review_id', name='uk_issue_review'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'issue_topic_id': self.issue_topic_id,
            'review_id': self.review_id,
            'evidence_text': self.evidence_text,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Report(db.Model):
    """报告产物模型"""
    __tablename__ = 'reports'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    run_id = db.Column(db.BigInteger, db.ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    summary_json = db.Column(db.JSON)
    pdf_path = db.Column(db.String(500))
    created_by = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 关系
    run = db.relationship('AnalysisRun', back_populates='reports')
    creator = db.relationship('User', back_populates='reports')

    def to_dict(self):
        return {
            'id': self.id,
            'run_id': self.run_id,
            'title': self.title,
            'summary_json': self.summary_json,
            'pdf_path': self.pdf_path,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
