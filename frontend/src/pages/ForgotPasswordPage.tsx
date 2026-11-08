import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { authErrorMessage, emailSchema, type EmailValues } from '@/auth/schemas'
import { FormField } from '@/components/FormField'
import { FormMessage } from '@/components/FormMessage'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { AuthLayout } from './AuthLayout'

export function ForgotPasswordPage() {
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const { register, handleSubmit, formState } = useForm<EmailValues>({ resolver: zodResolver(emailSchema) })

  const onSubmit = async ({ email }: EmailValues) => {
    setError(null)
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    if (error) setError(authErrorMessage(error))
    else setSent(true)
  }

  return (
    <AuthLayout title="Reset your password" intro="We'll email you a secure link to choose a new password.">
      <h2 className="font-display text-2xl font-medium">Forgot password</h2>
      {sent ? (
        <div className="mt-6 space-y-4">
          <FormMessage kind="success">If an account exists for that address, a reset link is on its way.</FormMessage>
          <Link to="/login" className="text-sm text-primary hover:underline">Back to sign in</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <FormField id="email" label="Email" type="email" autoComplete="email" error={formState.errors.email?.message} {...register('email')} />
          <Button type="submit" disabled={formState.isSubmitting} className="h-11 w-full rounded-full">
            {formState.isSubmitting ? 'Sending…' : 'Send reset link'}
          </Button>
          <Link to="/login" className="block text-sm text-primary hover:underline">Back to sign in</Link>
        </form>
      )}
    </AuthLayout>
  )
}
