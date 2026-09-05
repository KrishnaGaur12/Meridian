import React, { useState, useEffect } from 'react';

export const StickyCaseNav: React.FC = () => {
  const [activeSection, setActiveSection] = useState('case-overview');

  const navItems = [
    { id: 'case-overview', label: 'Overview' },
    { id: 'case-ai-recommendation', label: 'AI Recommendation' },
    { id: 'case-evidence', label: 'Evidence Workspace' },
    { id: 'case-final-review', label: 'Final Review' },
    { id: 'case-timeline', label: 'Timeline' },
  ];

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(id);
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 100;
      for (const item of navItems) {
        const el = document.getElementById(item.id);
        if (el) {
          const top = el.offsetTop;
          const height = el.offsetHeight;
          if (scrollPosition >= top && scrollPosition < top + height) {
            setActiveSection(item.id);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="sticky top-0 z-20 bg-slate-50/95 backdrop-blur-xs py-2 border-b border-slate-200/80 -mt-1 mb-2">
      <div className="w-full flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => scrollTo(item.id)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap cursor-pointer select-none ${
              activeSection === item.id
                ? 'bg-slate-900 text-white shadow-2xs font-bold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/70'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
};
