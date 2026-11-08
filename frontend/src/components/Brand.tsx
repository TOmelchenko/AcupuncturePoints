import { Link } from 'react-router'

export function Brand() {
  return (
    <Link to="/" className="font-display text-lg font-semibold tracking-tight">
      pressure<span className="text-primary">·</span>point
    </Link>
  )
}
