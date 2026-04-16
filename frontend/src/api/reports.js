import request from '@/utils/request'

export const createReport = (data) => {
  return request.post('/reports', data)
}

export const getReports = (params) => {
  return request.get('/reports', { params })
}

export const getReport = (id) => {
  return request.get(`/reports/${id}`)
}

export const downloadReport = (id) => {
  return request.get(`/reports/${id}/download`, {
    responseType: 'blob'
  })
}
