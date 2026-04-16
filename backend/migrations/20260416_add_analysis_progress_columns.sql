-- 迁移名称: 20260416_add_analysis_progress_columns
-- 目的: 增加分析任务阶段跟踪字段，用于前端阶段提示
-- 适用: MySQL 8.x

START TRANSACTION;

ALTER TABLE analysis_runs
  ADD COLUMN progress_stage VARCHAR(50) NULL AFTER status,
  ADD COLUMN progress_message TEXT NULL AFTER progress_stage,
  ADD COLUMN progress_updated_at DATETIME NULL AFTER progress_message;

-- 初始化历史数据，避免前端出现空值
UPDATE analysis_runs
SET
  progress_stage = CASE
    WHEN progress_stage IS NOT NULL THEN progress_stage
    ELSE status
  END,
  progress_message = CASE
    WHEN progress_message IS NOT NULL THEN progress_message
    WHEN status = 'pending' THEN '任务排队中'
    WHEN status = 'running' THEN '任务执行中'
    WHEN status = 'completed' THEN '分析任务已完成'
    WHEN status = 'failed' THEN COALESCE(error_message, '任务失败')
    WHEN status = 'canceled' THEN '任务已取消'
    ELSE NULL
  END,
  progress_updated_at = COALESCE(progress_updated_at, finished_at, started_at, created_at)
WHERE progress_stage IS NULL OR progress_message IS NULL OR progress_updated_at IS NULL;

COMMIT;

-- 回滚参考:
-- ALTER TABLE analysis_runs
--   DROP COLUMN progress_updated_at,
--   DROP COLUMN progress_message,
--   DROP COLUMN progress_stage;
