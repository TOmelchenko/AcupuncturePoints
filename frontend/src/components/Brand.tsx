import { Link } from 'react-router'

export function Brand() {
  return (
    <Link to="/" className="font-display text-lg font-semibold tracking-tight">
      acupuncture<span className="text-primary">·</span>points
    </Link>
  )
}
