import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import { authErrorMessage, newPasswordSchema, type NewPasswordValues } from '@/auth/schemas'
import { FormField } from '@/components/FormField'
import { FormMessage } from '@/components/FormMessage'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { AuthLayout } from './AuthLayout'

/** Landing page for the emailed reset link; Supabase signs the user in from the link. */
export function ResetPasswordPage() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState } = useForm<NewPasswordValues>({ resolver: zodResolver(newPasswordSchema) })

  const onSubmit = async ({ password }: NewPasswordValues) => {
    setError(null)
    const { error } = await supabase.auth.updateUser({ password })
    if (error) setError(authErrorMessage(error))
    else navigate('/', { replace: true })
  }

  return (
    <AuthLayout title="Choose a new password" intro="Pick a password you haven't used here before.">
      <h2 className="font-display text-2xl font-medium">New password</h2>
      {loading ? (
        <p role="status" className="mt-6 text-muted-foreground">Checking your link…</p>
      ) : !session ? (
        <div className="mt-6 space-y-4">
          <FormMessage kind="error">This reset link is invalid or has expired. Please request a new one.</FormMessage>
          <Link to="/forgot-password" className="text-sm text-primary hover:underline">Request a new link</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <FormField id="password" label="New password" type="password" autoComplete="new-password" error={formState.errors.password?.message} {...register('password')} />
          <FormField id="confirm" label="Confirm new password" type="password" autoComplete="new-password" error={formState.errors.confirm?.message} {...register('confirm')} />
          <Button type="submit" disabled={formState.isSubmitting} className="h-11 w-full rounded-full">
            {formState.isSubmitting ? 'Saving…' : 'Save new password'}
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
