import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

const STORAGE_KEY = 'theme'

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'dark'
  } catch {
    return false
  }
}

/** Switches between the default light theme and the optional dark theme. */
export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark') || readStored())

  const toggle = () => {
    const next = !dark
    setDark(next)
    document.documentElement.classList.toggle('dark', next)
    try {
      localStorage.setItem(STORAGE_KEY, next ? 'dark' : 'light')
    } catch {
      // Storage unavailable (e.g. private mode): the choice lasts for this page only.
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="rounded-full"
      aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      onClick={toggle}
    >
      {dark ? <Sun /> : <Moon />}
    </Button>
  )
}
