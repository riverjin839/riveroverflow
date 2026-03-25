import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response error interceptor
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Token expired or invalid - clear auth and redirect
      localStorage.removeItem('riveroverflow-auth')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
