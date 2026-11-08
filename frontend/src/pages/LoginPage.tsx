import { SplitLayout } from '@/components/SplitLayout'

export function LoginPage() {
  return (
    <SplitLayout aside={<h1 className="font-display text-4xl font-medium">Welcome back</h1>}>
      <p className="text-muted-foreground">Sign in to continue.</p>
    </SplitLayout>
  )
}
