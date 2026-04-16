export const TASK_STATUS_META = {
  pending: { text: '待处理', type: 'info' },
  running: { text: '运行中', type: 'warning' },
  completed: { text: '已完成', type: 'success' },
  failed: { text: '失败', type: 'danger' },
  canceled: { text: '已取消', type: 'info' }
}

export const getTaskStatusText = (status) => {
  return TASK_STATUS_META[status]?.text || status || '-'
}

export const getTaskStatusType = (status) => {
  return TASK_STATUS_META[status]?.type || 'info'
}

export const isTaskCancelable = (status) => {
  return status === 'pending' || status === 'running'
}

export const isTaskRetryable = (status) => {
  return status === 'failed' || status === 'canceled'
}
