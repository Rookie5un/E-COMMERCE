import csv
import hashlib
from datetime import datetime
from app import db
from app.models import Review, ReviewBatch
from app.nlp.text_processor import TextProcessor


class ReviewService:
    """评论服务"""

    def __init__(self):
        self.text_processor = TextProcessor()

    def import_from_csv(self, filepath, batch_id):
        """从CSV文件导入评论"""
        batch = ReviewBatch.query.get(batch_id)
        if not batch:
            raise ValueError('批次不存在')

        batch.status = 'processing'
        db.session.commit()

        imported_count = 0
        duplicate_count = 0
        failed_count = 0
        row_count = 0

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    row_count += 1

                    try:
                        # 获取评论内容
                        raw_content = row.get('content') or row.get('评论内容') or row.get('comment')
                        if not raw_content or not raw_content.strip():
                            failed_count += 1
                            continue

                        # 清洗文本
                        cleaned_content = self.text_processor.clean_text(raw_content)

                        # 计算哈希值用于去重
                        content_hash = hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()

                        # 检查是否重复
                        existing = Review.query.filter_by(content_hash=content_hash).first()
                        if existing:
                            duplicate_count += 1
                            continue

                        # 创建评论记录
                        review = Review(
                            product_id=batch.product_id,
                            batch_id=batch_id,
                            external_id=row.get('id') or row.get('评论ID'),
                            raw_content=raw_content,
                            cleaned_content=cleaned_content,
                            content_hash=content_hash,
                            rating=self._parse_rating(row.get('rating') or row.get('评分')),
                            review_time=self._parse_datetime(row.get('time') or row.get('评论时间')),
                            is_valid=True
                        )

                        db.session.add(review)
                        imported_count += 1

                        # 每100条提交一次
                        if imported_count % 100 == 0:
                            db.session.commit()

                    except Exception as e:
                        print(f'处理行 {row_count} 失败: {str(e)}')
                        failed_count += 1
                        continue

            # 最终提交
            db.session.commit()

            # 更新批次状态
            batch.row_count = row_count
            batch.imported_count = imported_count
            batch.duplicate_count = duplicate_count
            batch.failed_count = failed_count
            batch.status = 'completed'
            batch.finished_at = datetime.utcnow()
            db.session.commit()

            return {
                'row_count': row_count,
                'imported_count': imported_count,
                'duplicate_count': duplicate_count,
                'failed_count': failed_count
            }

        except Exception as e:
            batch.status = 'failed'
            batch.error_message = str(e)
            db.session.commit()
            raise

    def _parse_rating(self, rating_str):
        """解析评分"""
        if not rating_str:
            return None
        try:
            rating = int(rating_str)
            return rating if 1 <= rating <= 5 else None
        except:
            return None

    def _parse_datetime(self, datetime_str):
        """解析时间"""
        if not datetime_str:
            return None
        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d'
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except:
                    continue
            return None
        except:
            return None
