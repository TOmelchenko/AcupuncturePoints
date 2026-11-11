import { z } from 'zod'

const email = z.string().trim().min(1, 'Enter your email address.').pipe(z.email('Enter a valid email address.'))
const password = z.string().min(8, 'Use at least 8 characters.')

/** Shown under every field where a password is chosen; Supabase Auth enforces the same minimum. */
export const PASSWORD_HINT = 'At least 8 characters.'

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Enter your password.'),
})

export const newPasswordSchema = z
  .object({ password, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { message: 'Passwords do not match.', path: ['confirm'] })

export const registerSchema = z
  .object({ email, password, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { message: 'Passwords do not match.', path: ['confirm'] })

export const emailSchema = z.object({ email })

export type LoginValues = z.infer<typeof loginSchema>
export type RegisterValues = z.infer<typeof registerSchema>
export type NewPasswordValues = z.infer<typeof newPasswordSchema>
export type EmailValues = z.infer<typeof emailSchema>

const EMAIL_LIMIT_MESSAGE = 'Too many emails were requested. Please try again in an hour.'

/**
 * Supabase Auth messages are short and user-facing; fall back for anything unexpected.
 * The hourly email limit of the built-in email service gets a clearer message.
 */
export function authErrorMessage(error: { message?: string; code?: string } | null | undefined): string {
  if (error?.code === 'over_email_send_rate_limit' || /email rate limit exceeded/i.test(error?.message ?? '')) {
    return EMAIL_LIMIT_MESSAGE
  }
  return error?.message || 'Something went wrong. Please try again.'
}
