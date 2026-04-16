-- 迁移名称: 20260416_add_canceled_status_and_review_management
-- 目的: 扩展 analysis_runs.status 枚举，支持 canceled 状态。
-- 适用: MySQL 8.x

START TRANSACTION;

ALTER TABLE analysis_runs
  MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed', 'canceled')
  NOT NULL DEFAULT 'pending';

COMMIT;

-- 回滚参考（如需回滚请先处理已存在 canceled 数据）:
-- UPDATE analysis_runs SET status = 'failed' WHERE status = 'canceled';
-- ALTER TABLE analysis_runs
--   MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed')
--   NOT NULL DEFAULT 'pending';
