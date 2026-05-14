import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/upload', label: '上传 PDF' },
  { to: '/documents', label: '文献列表' },
  { to: '/search', label: '检索' },
  { to: '/settings', label: '设置' },
];

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-forest-800 text-white shadow">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-forest-500/90 flex items-center justify-center font-bold">
              B
            </div>
            <div>
              <div className="text-lg font-semibold tracking-wide">
                BioLitEvidence Finder
              </div>
              <div className="text-xs text-forest-100/80">
                生物多样性文献页级证据发现
              </div>
            </div>
          </div>
          <nav className="flex gap-1 text-sm">
            {navItems.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.end}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded transition ${
                    isActive
                      ? 'bg-forest-600 text-white'
                      : 'text-forest-100 hover:bg-forest-700'
                  }`
                }
              >
                {it.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <div className="max-w-[1400px] mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>
      <footer className="text-xs text-stone-500 text-center py-3">
        BioLitEvidence Finder · 页级证据发现 · 仅作研究原型展示
      </footer>
    </div>
  );
}
