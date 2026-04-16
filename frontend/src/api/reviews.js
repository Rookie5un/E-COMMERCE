import request from '@/utils/request'

export const importReviews = (formData) => {
  return request.post('/reviews/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const getBatches = (params) => {
  return request.get('/reviews/batches', { params })
}

export const getBatch = (id) => {
  return request.get(`/reviews/batches/${id}`)
}

export const getReviews = (params) => {
  return request.get('/reviews', { params })
}

export const getReview = (id) => {
  return request.get(`/reviews/${id}`)
}

export const setReviewValidity = (id, is_valid) => {
  return request.patch(`/reviews/${id}/validity`, { is_valid })
}

export const bulkSetReviewValidity = (review_ids, is_valid) => {
  return request.post('/reviews/bulk-validity', { review_ids, is_valid })
}
