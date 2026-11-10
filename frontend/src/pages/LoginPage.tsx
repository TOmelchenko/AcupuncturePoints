import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import { authErrorMessage, loginSchema, type LoginValues } from '@/auth/schemas'
import { FormField } from '@/components/FormField'
import { FormMessage } from '@/components/FormMessage'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { AuthLayout } from './AuthLayout'

export function LoginPage() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/'
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) })

  if (session) return <Navigate to={from} replace />

  const onSubmit = async (values: LoginValues) => {
    setError(null)
    const { error } = await supabase.auth.signInWithPassword(values)
    if (error) setError(authErrorMessage(error))
    else navigate(from, { replace: true })
  }

  return (
    <AuthLayout
      title="Welcome back"
      intro="Sign in to find acupressure points for how you feel."
      about="An acupressure self-care guide: tell it what's bothering you — a headache, stress, poor sleep — and it finds matching points from a curated knowledge base, showing where they are and how to press them. Use it for quick, gentle relief at home, not as medical treatment."
    >
      <h2 className="font-display text-2xl font-medium">Sign in</h2>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <FormField id="email" label="Email" type="email" autoComplete="email" error={formState.errors.email?.message} {...register('email')} />
        <FormField id="password" label="Password" type="password" autoComplete="current-password" error={formState.errors.password?.message} {...register('password')} />
        <Button type="submit" disabled={formState.isSubmitting} className="h-11 w-full rounded-full">
          {formState.isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
      <div className="mt-6 flex flex-col gap-2 text-sm text-muted-foreground sm:flex-row sm:justify-between">
        <Link to="/forgot-password" className="text-primary hover:underline">Forgot password?</Link>
        <span>
          New here? <Link to="/register" className="text-primary hover:underline">Create an account</Link>
        </span>
      </div>
    </AuthLayout>
  )
}
