import request from '@/utils/request'

export const createAnalysisRun = (data) => {
  return request.post('/analysis/run', data)
}

export const getAnalysisRuns = (params) => {
  return request.get('/analysis/runs', { params })
}

export const getAnalysisRun = (id) => {
  return request.get(`/analysis/runs/${id}`)
}

export const getAnalysisSummary = (params) => {
  return request.get('/analysis/summary', { params })
}

export const getSentimentAnalysis = (params) => {
  return request.get('/analysis/sentiment', { params })
}

export const getAspectAnalysis = (params) => {
  return request.get('/analysis/aspects', { params })
}

export const getIssueAnalysis = (params) => {
  return request.get('/analysis/issues', { params })
}

export const cancelAnalysisRun = (id) => {
  return request.post(`/analysis/runs/${id}/cancel`)
}

export const retryAnalysisRun = (id) => {
  return request.post(`/analysis/runs/${id}/retry`)
}
