// Авторизация на собственном состоянии React (useState + useContext).
// Внешние стор-библиотеки не подключаем, пока нет боли (см. STACK.md).
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { TOKEN_KEY } from '../api/client'
import { login as apiLogin, me as apiMe } from '../api/endpoints'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    apiMe()
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  const signIn = async (email: string, password: string) => {
    const { access_token } = await apiLogin(email, password)
    localStorage.setItem(TOKEN_KEY, access_token)
    setUser(await apiMe())
  }

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth должен использоваться внутри AuthProvider')
  return ctx
}
