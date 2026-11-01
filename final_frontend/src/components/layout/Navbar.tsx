import { NavLink } from 'react-router-dom';
import { PageContainer } from './PageContainer';

const LINKS = [
  { to: '/', label: 'Planner' },
  { to: '/daa', label: 'Algorithms' },
  { to: '/ai', label: 'AI' },
];
const cls = ({ isActive }: { isActive: boolean }) =>
  `inline-flex min-h-10 items-center rounded-lg px-3 text-sm font-medium transition-colors ${isActive ? 'text-accent' : 'text-ink-2 hover:text-ink'}`;

export function Navbar() {
  return (
    <header className="border-b border-divider bg-surface">
      <PageContainer className="flex h-14 items-center justify-between gap-4">
        <NavLink
          to="/"
          aria-label="Pathwise home"
          className="flex items-center gap-2 text-[1.0625rem] font-semibold tracking-tight text-ink hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded-lg"
        >
          <img
            src="/favicon.svg"
            alt=""
            width={26}
            height={26}
            aria-hidden="true"
            className="h-[26px] w-[26px] shrink-0 aspect-square"
          />
          <span>Pathwise</span>
        </NavLink>
        <nav aria-label="Primary" className="flex items-center">
          {LINKS.map((l) => <NavLink key={l.to} to={l.to} end={l.to === '/'} className={cls}>{l.label}</NavLink>)}
        </nav>
      </PageContainer>
    </header>
  );
}
