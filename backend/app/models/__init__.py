from datetime import datetime
from app import db


class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), index=True)
    real_name = db.Column(db.String(50))
    role = db.Column(db.Enum('admin', 'analyst'), nullable=False, default='analyst')
    status = db.Column(db.Enum('active', 'inactive'), nullable=False, default='active')
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    products = db.relationship('Product', back_populates='creator', foreign_keys='Product.created_by')
    review_batches = db.relationship('ReviewBatch', back_populates='creator')
    analysis_runs = db.relationship('AnalysisRun', back_populates='starter')
    reports = db.relationship('Report', back_populates='creator')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'role': self.role,
            'status': self.status,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Product(db.Model):
    """商品模型"""
    __tablename__ = 'products'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False, index=True)
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_by = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    creator = db.relationship('User', back_populates='products', foreign_keys=[created_by])
    review_batches = db.relationship('ReviewBatch', back_populates='product', cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='product', cascade='all, delete-orphan')
    analysis_runs = db.relationship('AnalysisRun', back_populates='product', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'platform': self.platform,
            'url': self.url,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ReviewBatch(db.Model):
    """评论导入批次模型"""
    __tablename__ = 'review_batches'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    source_type = db.Column(db.Enum('csv_import', 'crawler', 'api', 'manual'), nullable=False, default='csv_import')
    file_name = db.Column(db.String(255))
    row_count = db.Column(db.Integer, default=0)
    imported_count = db.Column(db.Integer, default=0)
    duplicate_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum('pending', 'processing', 'completed', 'failed'), nullable=False, default='pending', index=True)
    error_message = db.Column(db.Text)
    created_by = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    finished_at = db.Column(db.DateTime)

    # 关系
    product = db.relationship('Product', back_populates='review_batches')
    creator = db.relationship('User', back_populates='review_batches')
    reviews = db.relationship('Review', back_populates='batch', cascade='all, delete-orphan')
    analysis_runs = db.relationship('AnalysisRun', back_populates='batch')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'source_type': self.source_type,
            'file_name': self.file_name,
            'row_count': self.row_count,
            'imported_count': self.imported_count,
            'duplicate_count': self.duplicate_count,
            'failed_count': self.failed_count,
            'status': self.status,
            'error_message': self.error_message,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None
        }


class Review(db.Model):
    """评论模型"""
    __tablename__ = 'reviews'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_id = db.Column(db.BigInteger, db.ForeignKey('review_batches.id', ondelete='CASCADE'), nullable=False, index=True)
    external_id = db.Column(db.String(100), index=True)
    raw_content = db.Column(db.Text, nullable=False)
    cleaned_content = db.Column(db.Text)
    content_hash = db.Column(db.String(64), nullable=False, unique=True)
    rating = db.Column(db.SmallInteger)
    review_time = db.Column(db.DateTime, index=True)
    is_valid = db.Column(db.Boolean, default=True, index=True)
    duplicate_of = db.Column(db.BigInteger)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    product = db.relationship('Product', back_populates='reviews')
    batch = db.relationship('ReviewBatch', back_populates='reviews')
    sentiments = db.relationship('ReviewSentiment', back_populates='review', cascade='all, delete-orphan')
    aspect_mentions = db.relationship('AspectMention', back_populates='review', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'batch_id': self.batch_id,
            'external_id': self.external_id,
            'raw_content': self.raw_content,
            'cleaned_content': self.cleaned_content,
            'rating': self.rating,
            'review_time': self.review_time.isoformat() if self.review_time else None,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
