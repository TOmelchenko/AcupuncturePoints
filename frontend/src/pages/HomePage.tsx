import { AppNav } from '@/components/AppNav'
import { SplitLayout } from '@/components/SplitLayout'

export function HomePage() {
  return (
    <SplitLayout
      nav={<AppNav />}
      aside={<h1 className="font-display text-4xl font-medium">How are you feeling today?</h1>}
    >
      <p className="text-muted-foreground">Recommendations will appear here.</p>
    </SplitLayout>
  )
}
