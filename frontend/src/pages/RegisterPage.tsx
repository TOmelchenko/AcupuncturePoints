import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate } from 'react-router'
import { useAuth } from '@/auth/context'
import { authErrorMessage, registerSchema, type RegisterValues } from '@/auth/schemas'
import { FormField } from '@/components/FormField'
import { FormMessage } from '@/components/FormMessage'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { AuthLayout } from './AuthLayout'

export function RegisterPage() {
  const { session } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [checkEmail, setCheckEmail] = useState(false)
  const { register, handleSubmit, formState } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) })

  if (session) return <Navigate to="/" replace />

  const onSubmit = async ({ email, password }: RegisterValues) => {
    setError(null)
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/` },
    })
    if (error) setError(authErrorMessage(error))
    else if (!data.session) setCheckEmail(true) // email confirmation required
  }

  return (
    <AuthLayout title="Create your account" intro="An account keeps your feedback private and helps improve suggestions.">
      <h2 className="font-display text-2xl font-medium">Register</h2>
      {checkEmail ? (
        <div className="mt-6 space-y-4">
          <FormMessage kind="success">
            Check your email: we sent you a link to confirm your address. After confirming, you can sign in.
          </FormMessage>
          <Link to="/login" className="text-sm text-primary hover:underline">Back to sign in</Link>
        </div>
      ) : (
        <>
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
            {error && <FormMessage kind="error">{error}</FormMessage>}
            <FormField id="email" label="Email" type="email" autoComplete="email" error={formState.errors.email?.message} {...register('email')} />
            <FormField id="password" label="Password" type="password" autoComplete="new-password" error={formState.errors.password?.message} {...register('password')} />
            <FormField id="confirm" label="Confirm password" type="password" autoComplete="new-password" error={formState.errors.confirm?.message} {...register('confirm')} />
            <Button type="submit" disabled={formState.isSubmitting} className="h-11 w-full rounded-full">
              {formState.isSubmitting ? 'Creating account…' : 'Create account'}
            </Button>
          </form>
          <p className="mt-6 text-sm text-muted-foreground">
            Already have an account? <Link to="/login" className="text-primary hover:underline">Sign in</Link>
          </p>
        </>
      )}
    </AuthLayout>
  )
}
