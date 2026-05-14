import { NavLink, Outlet } from 'react-router-dom';
import { useI18n } from './i18n';

const navItems = [
  { to: '/', labelKey: 'nav_dashboard', end: true },
  { to: '/upload', labelKey: 'nav_upload' },
  { to: '/documents', labelKey: 'nav_documents' },
  { to: '/search', labelKey: 'nav_search' },
  { to: '/settings', labelKey: 'nav_settings' },
];

export default function App() {
  const { t, lang, setLang } = useI18n();

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
                {t('dashboard_title')}
              </div>
              <div className="text-xs text-forest-100/80">
                {t('dashboard_subtitle')}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
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
                  {t(it.labelKey as any)}
                </NavLink>
              ))}
            </nav>
            <button
              onClick={() => setLang(lang === 'en' ? 'zh' : 'en')}
              className="px-3 py-1.5 rounded border border-forest-400 text-sm hover:bg-forest-700 transition"
            >
              {lang === 'en' ? '中文' : 'EN'}
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1">
        <div className="max-w-[1400px] mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>
      <footer className="text-xs text-stone-500 text-center py-3">
        BioLitEvidence Finder · Page-level Evidence Discovery · Research Prototype
      </footer>
    </div>
  );
}
