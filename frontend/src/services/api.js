import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export const createSurvey = (topic) =>
  api.post('/surveys/', { topic }).then((r) => r.data)

export const listSurveys = () =>
  api.get('/surveys/').then((r) => r.data)

export const getSurvey = (id) =>
  api.get(`/surveys/${id}`).then((r) => r.data)

export const deleteSurvey = (id) =>
  api.delete(`/surveys/${id}`)
