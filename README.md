# 电商评论多维可视化分析平台（ECommerce Insight）

基于 Flask + Vue 3 的电商评论分析系统，围绕评论数据提供：
- 情感分析（正向 / 中性 / 负向）
- 功能点提取（Aspect）
- 负面问题挖掘（Issue）
- 可视化看板（图表 + 关键词词云）
- 分析报告管理与 PDF 导出

---

## 功能概览

### 1. 基础业务
- 用户认证（登录/注册/JWT）
- 商品管理（新增、编辑、删除、详情）
- 评论导入（CSV 批次导入）
- 评论管理（列表、软删除/恢复、批量操作）

### 2. 分析任务
- 任务创建、状态跟踪
- 任务取消、重试
- 任务详情与分析结果联动

### 3. 分析总览
- 情感分布环图
- 功能点 Top 10 柱状图
- 负面问题 Top 10 柱状图
- 关键词词云（与问题图并排展示）

### 4. 报告中心
- 报告生成
- 报告历史查看
- PDF 导出（中文模板）

---

## 技术栈

### 后端（`backend/`）
- Flask 3.x
- SQLAlchemy 2.x + PyMySQL
- Flask-JWT-Extended
- Flask-Migrate
- jieba / Transformers / PyTorch（可选）
- reportlab（PDF 导出）

### 前端（`frontend/`）
- Vue 3
- Element Plus
- ECharts + Vue-ECharts
- echarts-wordcloud
- Pinia
- Vite

---

## 项目结构

```text
E-commerce/
├── backend/
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # ORM 模型
│   │   ├── services/       # 业务服务（分析、报告等）
│   │   ├── nlp/            # NLP 能力模块
│   │   └── utils/
│   ├── config.py
│   ├── run.py              # 后端启动入口
│   ├── requirements*.txt
│   ├── environment.yml     # conda 环境文件
│   ├── migrations/         # SQL 变更脚本
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── router/
│   │   ├── store/
│   │   ├── utils/
│   │   └── views/
│   └── package.json
├── docs/
└── data/
```

---

## 快速开始（推荐 Conda）

> 以下命令默认在仓库根目录执行。

### 1) 创建并激活 Conda 环境

```bash
conda env create -f backend/environment.yml
conda activate ecommerce-nlp
```

### 2) 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

可选依赖：

```bash
# 深度学习推理/训练相关
pip install -r requirements-ml.txt

# 其他扩展依赖
pip install -r requirements-extras.txt
```

### 3) 配置环境变量

```bash
cp .env.example .env
```

重点配置项（`backend/.env`）：
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS`
- `PORT`

### 4) 启动后端

```bash
python run.py
```

默认地址：
- `http://localhost:5000`（若 `.env` 配了 `PORT` 则以 `.env` 为准）

---

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认地址：
- `http://localhost:5173`

---

## 常用脚本

### 后端测试

```bash
cd backend
python -m unittest discover -s tests -v
```

### 前端构建

```bash
cd frontend
npm run build
```

---

## API 概览

### 认证
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`

### 商品
- `GET /api/products`
- `POST /api/products`
- `GET /api/products/:id`
- `PUT /api/products/:id`
- `DELETE /api/products/:id`

### 评论
- `POST /api/reviews/import`
- `GET /api/reviews/batches`
- `GET /api/reviews`
- `PATCH /api/reviews/:id/validity`
- `POST /api/reviews/bulk-validity`

### 分析
- `POST /api/analysis/run`
- `GET /api/analysis/runs`
- `GET /api/analysis/runs/:id`
- `POST /api/analysis/runs/:id/cancel`
- `POST /api/analysis/runs/:id/retry`
- `GET /api/analysis/summary`
- `GET /api/analysis/sentiment`
- `GET /api/analysis/aspects`
- `GET /api/analysis/issues`

### 报告
- `POST /api/reports`
- `GET /api/reports`
- `GET /api/reports/:id`
- `GET /api/reports/:id/download`

---

## CSV 导入格式

支持中英文列名，核心字段如下：

| 列名 | 必填 | 说明 |
| --- | --- | --- |
| `content` / `评论内容` | 是 | 评论文本 |
| `id` / `评论ID` | 否 | 平台评论 ID |
| `rating` / `评分` | 否 | 1~5 星 |
| `time` / `评论时间` | 否 | 评论时间 |

示例：

```csv
content,rating,time
这个手机很好用，拍照清晰，续航给力！,5,2024-01-01 10:00:00
屏幕不错但是有点卡顿,3,2024-01-02 15:30:00
```

---

## 常见问题

### 1) 前端请求失败 / 跨域
- 检查后端是否启动
- 检查 `CORS_ORIGINS` 是否包含前端地址

### 2) 报告导出不是中文样式
- 确认后端环境安装了 `reportlab`
- 重启后端后重新生成报告再下载（旧 PDF 不会自动更新）

### 3) 词云未显示
- 先确认分析任务已完成且有问题词或功能点数据
- 确认前端依赖已安装：`echarts-wordcloud`

### 4) 数据库连接失败
- 检查 `.env` 中 `DATABASE_URL`
- 检查 MySQL 服务和数据库权限

---

## License

MIT
