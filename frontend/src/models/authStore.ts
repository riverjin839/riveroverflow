import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../presenters/api'

interface AuthState {
  token: string | null
  username: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,

      login: async (username, password) => {
        const res = await api.post('/api/auth/login', { username, password })
        const { token } = res.data
        set({ token, username })
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      },

      logout: () => {
        set({ token: null, username: null })
        delete api.defaults.headers.common['Authorization']
      },
    }),
    {
      name: 'riveroverflow-auth',
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        }
      },
    }
  )
)
