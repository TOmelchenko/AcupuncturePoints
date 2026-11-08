import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import { authErrorMessage, newPasswordSchema, type NewPasswordValues } from '@/auth/schemas'
import { AppNav } from '@/components/AppNav'
import { FormField } from '@/components/FormField'
import { FormMessage } from '@/components/FormMessage'
import { SplitLayout } from '@/components/SplitLayout'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { supabase } from '@/lib/supabase'

const CARD = 'rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8'

function ChangePassword() {
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const { register, handleSubmit, formState, reset } = useForm<NewPasswordValues>({
    resolver: zodResolver(newPasswordSchema),
  })

  const onSubmit = async ({ password }: NewPasswordValues) => {
    setMessage(null)
    const { error } = await supabase.auth.updateUser({ password })
    if (error) {
      setMessage({ kind: 'error', text: authErrorMessage(error) })
    } else {
      reset()
      setMessage({ kind: 'success', text: 'Your password has been changed.' })
    }
  }

  return (
    <section aria-labelledby="password-heading" className={CARD}>
      <h2 id="password-heading" className="font-display text-xl font-medium">Change password</h2>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-5 space-y-4">
        {message && <FormMessage kind={message.kind}>{message.text}</FormMessage>}
        <FormField id="password" label="New password" type="password" autoComplete="new-password" error={formState.errors.password?.message} {...register('password')} />
        <FormField id="confirm" label="Confirm new password" type="password" autoComplete="new-password" error={formState.errors.confirm?.message} {...register('confirm')} />
        <Button type="submit" disabled={formState.isSubmitting} className="h-11 rounded-full px-6">
          {formState.isSubmitting ? 'Saving…' : 'Change password'}
        </Button>
      </form>
    </section>
  )
}

function DeleteAccount() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const deletion = useMutation({
    mutationFn: api.deleteAccount,
    onSuccess: async () => {
      await supabase.auth.signOut()
      queryClient.clear()
      navigate('/login', { replace: true })
    },
  })

  return (
    <section aria-labelledby="delete-heading" className={CARD}>
      <h2 id="delete-heading" className="font-display text-xl font-medium">Delete account</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        This permanently deletes your account, your symptom descriptions, recommendations and ratings.
        It cannot be undone.
      </p>
      {deletion.isError && (
        <div className="mt-4">
          <FormMessage kind="error">{deletion.error.message}</FormMessage>
        </div>
      )}
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="destructive" className="mt-5 h-11 rounded-full px-6" disabled={deletion.isPending}>
            {deletion.isPending ? 'Deleting…' : deletion.isError ? 'Try again' : 'Delete my account'}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete your account?</AlertDialogTitle>
            <AlertDialogDescription>
              All your data will be permanently removed. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deletion.mutate()}
            >
              Yes, delete everything
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  )
}

export function AccountPage() {
  const { session } = useAuth()
  return (
    <SplitLayout
      nav={<AppNav />}
      aside={
        <>
          <h1 className="font-display text-4xl font-medium leading-tight lg:text-5xl">Your account</h1>
          <p className="mt-3 text-muted-foreground">Signed in as {session?.user.email}</p>
        </>
      }
    >
      <div className="mx-auto max-w-xl space-y-6">
        <ChangePassword />
        <DeleteAccount />
      </div>
    </SplitLayout>
  )
}
