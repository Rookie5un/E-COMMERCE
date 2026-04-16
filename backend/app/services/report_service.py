import os
from datetime import datetime

from flask import current_app
from sqlalchemy import desc, func

from app import db
from app.models.analysis import AnalysisRun, AspectMention, IssueTopic, Report, ReviewSentiment
from app.services.summary_utils import build_sentiment_distribution

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


class WordCloudFlowable(Flowable):
    """简化版词云：使用不同字号与颜色在固定画布内自适应排布。"""

    def __init__(self, words, font_name, width, height=68 * mm):
        super().__init__()
        self.words = words
        self.font_name = font_name
        self._width = width
        self._height = height
        self.palette = [
            colors.HexColor('#1d4ed8'),
            colors.HexColor('#0f766e'),
            colors.HexColor('#7c3aed'),
            colors.HexColor('#c2410c'),
            colors.HexColor('#be185d'),
            colors.HexColor('#0369a1'),
            colors.HexColor('#0e7490'),
            colors.HexColor('#4338ca'),
        ]

    def wrap(self, avail_width, avail_height):
        self._width = min(self._width, avail_width)
        return self._width, self._height

    def draw(self):
        canvas = self.canv
        canvas.saveState()

        canvas.setStrokeColor(colors.HexColor('#dbe5ef'))
        canvas.setLineWidth(0.8)
        canvas.roundRect(0, 0, self._width, self._height, 6, stroke=1, fill=0)

        if not self.words:
            canvas.setFillColor(colors.HexColor('#64748b'))
            canvas.setFont(self.font_name, 10)
            canvas.drawString(10, self._height / 2, '暂无词云数据')
            canvas.restoreState()
            return

        padding_x = 10
        cursor_x = padding_x
        cursor_y = self._height - 24
        line_height = 20
        min_y = 10

        for idx, item in enumerate(self.words):
            word = str(item.get('word') or '-')
            font_size = float(item.get('font_size') or 12)
            text_width = pdfmetrics.stringWidth(word, self.font_name, font_size)

            if cursor_x + text_width > self._width - padding_x:
                cursor_x = padding_x
                cursor_y -= line_height

            if cursor_y < min_y:
                break

            canvas.setFont(self.font_name, font_size)
            canvas.setFillColor(self.palette[idx % len(self.palette)])
            canvas.drawString(cursor_x, cursor_y, word)

            cursor_x += text_width + 14
            line_height = max(line_height, font_size + 8)

        canvas.restoreState()


class ReportService:
    """报告服务"""
    _registered_font_name = None

    def generate_report(self, run_id, user_id):
        """生成分析报告"""
        run = AnalysisRun.query.get(run_id)
        if not run or run.status != 'completed':
            raise ValueError('分析任务不存在或未完成')

        # 收集分析数据
        summary_data = self._collect_analysis_data(run_id)

        # 创建报告记录
        report = Report(
            run_id=run_id,
            title=f'{run.product.name} - 评论分析报告',
            summary_json=summary_data,
            created_by=user_id
        )

        try:
            self._ensure_report_id_for_testing(report)
            db.session.add(report)
            db.session.flush()

            pdf_path = self._generate_pdf(report, run, summary_data)
            report.pdf_path = pdf_path

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return report

    def _collect_analysis_data(self, run_id):
        """收集分析数据"""
        # 情感分布统计
        sentiment_stats = db.session.query(
            ReviewSentiment.label,
            func.count(ReviewSentiment.id).label('count'),
            func.avg(ReviewSentiment.confidence).label('avg_confidence')
        ).filter_by(run_id=run_id).group_by(ReviewSentiment.label).all()

        sentiment_data, total_reviews = build_sentiment_distribution(sentiment_stats)

        # 功能点统计
        aspect_stats = db.session.query(
            AspectMention.normalized_aspect,
            func.count(AspectMention.id).label('count'),
            AspectMention.linked_sentiment
        ).filter_by(run_id=run_id).group_by(
            AspectMention.normalized_aspect,
            AspectMention.linked_sentiment
        ).all()

        # 按功能点聚合
        aspect_data = {}
        for aspect, count, sentiment in aspect_stats:
            if aspect not in aspect_data:
                aspect_data[aspect] = {
                    'total': 0,
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0
                }
            aspect_data[aspect]['total'] += count
            if sentiment:
                aspect_data[aspect][sentiment] += count

        # 转换为列表并排序
        aspect_list = [
            {
                'aspect': aspect,
                'count': data['total'],
                'positive': data['positive'],
                'neutral': data['neutral'],
                'negative': data['negative'],
                'positive_rate': round(data['positive'] / data['total'] * 100, 2) if data['total'] > 0 else 0
            }
            for aspect, data in aspect_data.items()
        ]
        aspect_list.sort(key=lambda x: x['count'], reverse=True)

        # 问题关键词统计
        issue_stats = IssueTopic.query.filter_by(run_id=run_id).order_by(
            desc(IssueTopic.frequency)
        ).limit(20).all()

        issue_list = [
            {
                'keyword': issue.normalized_keyword,
                'frequency': issue.frequency,
                'score': float(issue.score) if issue.score else 0
            }
            for issue in issue_stats
        ]

        return {
            'total_reviews': total_reviews,
            'sentiment_distribution': sentiment_data,
            'top_aspects': aspect_list[:10],
            'top_issues': issue_list[:10],
            'generated_at': datetime.utcnow().isoformat()
        }

    def _ensure_report_id_for_testing(self, report):
        """
        SQLite 测试环境下，BigInteger 主键不会自动递增，需手动赋值。
        """
        if not current_app.config.get('TESTING'):
            return
        if db.engine.dialect.name != 'sqlite':
            return
        if report.id is not None:
            return

        max_id = db.session.query(func.max(Report.id)).scalar() or 0
        report.id = int(max_id) + 1

    def _generate_pdf(self, report, run, summary_data):
        """生成 PDF 报告文件并返回绝对路径。"""
        report_folder = current_app.config.get('REPORT_FOLDER')
        if not report_folder:
            report_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'reports')

        os.makedirs(report_folder, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f'report_{report.id}_{timestamp}.pdf'
        file_path = os.path.abspath(os.path.join(report_folder, filename))

        if not REPORTLAB_AVAILABLE:
            raise RuntimeError('报告导出依赖缺失：请先安装 reportlab')

        self._generate_pdf_with_reportlab(file_path, report, run, summary_data)

        return file_path

    def _build_plain_pdf_lines(self, report, run, summary_data):
        sentiment_distribution = summary_data.get('sentiment_distribution') or {}
        total_reviews = int(summary_data.get('total_reviews') or 0)

        positive_count, positive_pct = self._extract_sentiment_bucket(
            sentiment_distribution, total_reviews, 'positive'
        )
        neutral_count, neutral_pct = self._extract_sentiment_bucket(
            sentiment_distribution, total_reviews, 'neutral'
        )
        negative_count, negative_pct = self._extract_sentiment_bucket(
            sentiment_distribution, total_reviews, 'negative'
        )

        lines = [
            'E-Commerce Review Analysis Report',
            f'Report ID: {report.id}',
            f'Run ID: {run.id}',
            f'Product: {run.product.name}',
            f'Generated At: {datetime.utcnow().isoformat()}',
            f'Total Reviews: {total_reviews}',
            '',
            'Sentiment Distribution',
            f'- positive: {positive_count} ({positive_pct:.1f}%)',
            f'- neutral: {neutral_count} ({neutral_pct:.1f}%)',
            f'- negative: {negative_count} ({negative_pct:.1f}%)',
            '',
            'Top Aspects'
        ]

        top_aspects = summary_data.get('top_aspects') or []
        if top_aspects:
            for index, item in enumerate(top_aspects[:10], start=1):
                lines.append(
                    f"{index}. {item.get('aspect', '-')}"
                    f" | count={int(item.get('count', 0) or 0)}"
                    f" | positive_rate={float(item.get('positive_rate', 0) or 0):.1f}%"
                )
        else:
            lines.append('No aspect data')

        lines.append('')
        lines.append('Top Issues')

        top_issues = summary_data.get('top_issues') or []
        if top_issues:
            for index, item in enumerate(top_issues[:10], start=1):
                lines.append(
                    f"{index}. {item.get('keyword', '-')}"
                    f" | frequency={int(item.get('frequency', 0) or 0)}"
                    f" | score={float(item.get('score', 0) or 0):.2f}"
                )
        else:
            lines.append('No issue data')

        return lines

    def _generate_pdf_with_reportlab(self, file_path, report, run, summary_data):
        font_name = self._resolve_pdf_font_name()
        styles = self._build_report_styles(font_name)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=report.title,
            author='E-Commerce Review Analytics',
        )

        story = []
        story.append(Paragraph('电商评论分析报告', styles['title']))
        story.append(Paragraph(f'报告名称：{report.title}', styles['meta']))
        story.append(Spacer(1, 4 * mm))

        generated_at = summary_data.get('generated_at') or datetime.utcnow().isoformat()
        overview_data = [
            ['报告ID', str(report.id), '任务ID', str(run.id)],
            ['商品名称', run.product.name or '-', '生成时间', generated_at],
            ['评论总数', str(int(summary_data.get('total_reviews') or 0)), '模型', f"{run.model_name} / {run.model_version}"],
        ]
        overview_table = Table(overview_data, colWidths=[20 * mm, 62 * mm, 20 * mm, 72 * mm])
        overview_table.setStyle(self._overview_table_style())
        story.append(overview_table)
        story.append(Spacer(1, 5 * mm))

        story.append(Paragraph('一、情感分布', styles['section']))
        story.append(self._build_sentiment_table(summary_data, styles))
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph('二、功能点 Top 10', styles['section']))
        story.append(self._build_aspect_table(summary_data, styles))
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph('三、负面问题 Top 10', styles['section']))
        story.append(self._build_issue_table(summary_data, styles))
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph('四、问题词云', styles['section']))
        story.append(self._build_issue_word_cloud(summary_data, doc.width))

        doc.build(story, onFirstPage=self._build_page_decorator(font_name), onLaterPages=self._build_page_decorator(font_name))

    @classmethod
    def _resolve_pdf_font_name(cls):
        if cls._registered_font_name:
            return cls._registered_font_name

        for font_name, font_path in (
            ('ReportCNArialUnicode', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
            ('ReportCNSTHeiti', '/System/Library/Fonts/STHeiti Medium.ttc'),
            ('ReportCNSongti', '/System/Library/Fonts/Supplemental/Songti.ttc'),
        ):
            if not os.path.exists(font_path):
                continue
            try:
                if font_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                cls._registered_font_name = font_name
                return font_name
            except Exception:
                continue

        try:
            fallback_name = 'STSong-Light'
            if fallback_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(UnicodeCIDFont(fallback_name))
            cls._registered_font_name = fallback_name
            return fallback_name
        except Exception:
            cls._registered_font_name = 'Helvetica'
            return cls._registered_font_name

    @staticmethod
    def _build_report_styles(font_name):
        base = getSampleStyleSheet()
        styles = {
            'title': ParagraphStyle(
                'ReportTitle',
                parent=base['Title'],
                fontName=font_name,
                fontSize=22,
                leading=28,
                textColor=colors.HexColor('#111827'),
                spaceAfter=6 * mm,
            ),
            'meta': ParagraphStyle(
                'ReportMeta',
                parent=base['Normal'],
                fontName=font_name,
                fontSize=10.5,
                leading=16,
                textColor=colors.HexColor('#334155'),
                wordWrap='CJK',
            ),
            'section': ParagraphStyle(
                'ReportSection',
                parent=base['Heading2'],
                fontName=font_name,
                fontSize=13.5,
                leading=18,
                textColor=colors.HexColor('#0f172a'),
                spaceAfter=3 * mm,
                wordWrap='CJK',
            ),
            'cell': ParagraphStyle(
                'ReportCell',
                parent=base['Normal'],
                fontName=font_name,
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#1e293b'),
                wordWrap='CJK',
            ),
            'small': ParagraphStyle(
                'ReportSmall',
                parent=base['Normal'],
                fontName=font_name,
                fontSize=9,
                leading=12,
                textColor=colors.HexColor('#64748b'),
                wordWrap='CJK',
            ),
        }
        return styles

    @staticmethod
    def _overview_table_style():
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('LINEABOVE', (0, 0), (-1, 0), 0.8, colors.HexColor('#e2e8f0')),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (0, 0), (-1, -1), ReportService._resolve_pdf_font_name()),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ])

    def _build_sentiment_table(self, summary_data, styles):
        total = int(summary_data.get('total_reviews') or 0)
        distribution = summary_data.get('sentiment_distribution') or {}
        rows = [
            ['情感类型', '数量', '占比']
        ]
        for label, text in (('positive', '正向'), ('neutral', '中性'), ('negative', '负向')):
            count, pct = self._extract_sentiment_bucket(distribution, total, label)
            rows.append([text, str(count), f'{pct:.1f}%'])

        table = Table(rows, colWidths=[50 * mm, 35 * mm, 35 * mm])
        table.setStyle(self._standard_table_style(styles['cell'].fontName, header_bg='#eff6ff'))
        return table

    def _build_aspect_table(self, summary_data, styles):
        top_aspects = summary_data.get('top_aspects') or []
        rows = [['序号', '功能点', '提及次数', '正向率', '正/中/负']]

        for idx, item in enumerate(top_aspects[:10], start=1):
            aspect_name = str(item.get('aspect') or '-')
            count = int(item.get('count') or 0)
            positive_rate = float(item.get('positive_rate') or 0)
            positive = int(item.get('positive') or 0)
            neutral = int(item.get('neutral') or 0)
            negative = int(item.get('negative') or 0)
            rows.append([
                str(idx),
                aspect_name,
                str(count),
                f'{positive_rate:.1f}%',
                f'{positive}/{neutral}/{negative}',
            ])

        if len(rows) == 1:
            rows.append(['-', '暂无数据', '-', '-', '-'])

        table = Table(rows, colWidths=[16 * mm, 64 * mm, 28 * mm, 24 * mm, 35 * mm])
        table.setStyle(self._standard_table_style(styles['cell'].fontName, header_bg='#ecfeff'))
        return table

    def _build_issue_table(self, summary_data, styles):
        top_issues = summary_data.get('top_issues') or []
        rows = [['序号', '问题关键词', '出现频次', '权重得分']]

        for idx, item in enumerate(top_issues[:10], start=1):
            keyword = str(item.get('keyword') or '-')
            frequency = int(item.get('frequency') or 0)
            score = float(item.get('score') or 0)
            rows.append([str(idx), keyword, str(frequency), f'{score:.2f}'])

        if len(rows) == 1:
            rows.append(['-', '暂无数据', '-', '-'])

        table = Table(rows, colWidths=[16 * mm, 74 * mm, 32 * mm, 36 * mm])
        table.setStyle(self._standard_table_style(styles['cell'].fontName, header_bg='#fff7ed'))
        return table

    def _build_issue_word_cloud(self, summary_data, width):
        words_source = summary_data.get('top_issues') or []
        if not words_source:
            words_source = [
                {'keyword': item.get('aspect'), 'frequency': item.get('count')}
                for item in (summary_data.get('top_aspects') or [])
            ]

        if not words_source:
            return WordCloudFlowable([], self._resolve_pdf_font_name(), width)

        max_frequency = max(int(item.get('frequency') or 0) for item in words_source) or 1
        prepared_words = []
        for item in words_source[:20]:
            word = str(item.get('keyword') or '-')
            frequency = int(item.get('frequency') or 0)
            ratio = frequency / max_frequency if max_frequency else 0
            font_size = 11 + ratio * 14
            prepared_words.append({
                'word': word,
                'font_size': round(font_size, 1),
            })

        prepared_words.sort(key=lambda item: item['font_size'], reverse=True)
        return WordCloudFlowable(prepared_words, self._resolve_pdf_font_name(), width)

    @staticmethod
    def _standard_table_style(font_name, header_bg='#f8fafc'):
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9.8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#dbe5ef')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])

    @staticmethod
    def _build_page_decorator(font_name):
        def decorate(canvas, doc):
            canvas.saveState()
            canvas.setFont(font_name, 9)
            canvas.setFillColor(colors.HexColor('#94a3b8'))
            page_label = f'第 {canvas.getPageNumber()} 页'
            canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, page_label)
            canvas.restoreState()

        return decorate

    @staticmethod
    def _extract_sentiment_bucket(distribution, total, label):
        bucket = distribution.get(label)
        if isinstance(bucket, dict):
            return int(bucket.get('count', 0) or 0), float(bucket.get('percentage', 0) or 0)

        count = int(bucket or 0)
        percentage = (count / total * 100) if total else 0
        return count, percentage

    @staticmethod
    def _escape_pdf_text(text):
        safe = str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        return safe.encode('latin-1', 'replace').decode('latin-1')

    def _build_minimal_pdf(self, lines):
        safe_lines = lines[:42]
        stream_lines = [
            'BT',
            '/F1 11 Tf',
            '15 TL',
            '50 800 Td'
        ]

        for index, line in enumerate(safe_lines):
            if index > 0:
                stream_lines.append('T*')
            stream_lines.append(f'({self._escape_pdf_text(line)}) Tj')
        stream_lines.append('ET')

        content_stream = ('\n'.join(stream_lines) + '\n').encode('latin-1')

        objects = [
            b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
            b'2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n',
            (
                b'3 0 obj\n'
                b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n'
                b'endobj\n'
            ),
            b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n',
            (
                f'5 0 obj\n<< /Length {len(content_stream)} >>\nstream\n'.encode('ascii')
                + content_stream
                + b'endstream\nendobj\n'
            )
        ]

        pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = [0]

        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)

        xref_start = len(pdf)
        pdf.extend(f'xref\n0 {len(offsets)}\n'.encode('ascii'))
        pdf.extend(b'0000000000 65535 f \n')

        for offset in offsets[1:]:
            pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))

        pdf.extend(
            (
                f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n'
                f'startxref\n{xref_start}\n%%EOF\n'
            ).encode('ascii')
        )

        return bytes(pdf)
