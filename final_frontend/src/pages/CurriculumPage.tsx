import { useState, useMemo } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { CURATED_COURSES, type CatalogCourse } from '../data/coursesCatalog';
import { Button } from '../components/common/Button';

export default function CurriculumPage() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');

  const categories = useMemo(() => {
    const set = new Set(CURATED_COURSES.map((c) => c.category));
    return ['all', ...Array.from(set).sort()];
  }, []);

  const filteredCourses = useMemo(() => {
    const q = search.trim().toLowerCase();
    return CURATED_COURSES.filter((c) => {
      const matchSearch =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        c.aliases.some((a) => a.toLowerCase().includes(q));
      const matchCategory = selectedCategory === 'all' || c.category === selectedCategory;
      const matchDifficulty = selectedDifficulty === 'all' || c.difficulty === selectedDifficulty;
      return matchSearch && matchCategory && matchDifficulty;
    });
  }, [search, selectedCategory, selectedDifficulty]);

  return (
    <PageContainer className="pt-10 pb-20">
      <header className="max-w-2xl">
        <h1 className="h-page">Academic Course Catalog</h1>
        <p className="mt-3 text-base text-ink-2 leading-relaxed">
          The knowledge base contains {CURATED_COURSES.length} curated Computer Science courses and 115 prerequisite dependencies. Search or filter courses below to explore available subjects and their topics.
        </p>
      </header>

      <section className="mt-8 space-y-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between border-b border-divider pb-3">
          <h2 className="text-lg font-semibold text-ink">Catalog Explorer</h2>
          <span className="text-sm font-medium text-accent font-mono">
            Showing {filteredCourses.length} of {CURATED_COURSES.length} courses
          </span>
        </div>

        {/* Filter controls */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <input
              type="text"
              className="field"
              placeholder="Search courses by title, topic, or alias..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                className="absolute right-3 top-2.5 text-xs text-muted hover:text-ink"
                onClick={() => setSearch('')}
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <select
              className="field text-sm"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              aria-label="Filter by category"
            >
              <option value="all">All Categories</option>
              {categories.filter((c) => c !== 'all').map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>

            <select
              className="field text-sm"
              value={selectedDifficulty}
              onChange={(e) => setSelectedDifficulty(e.target.value)}
              aria-label="Filter by difficulty"
            >
              <option value="all">All Difficulties</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>

        {/* Course cards grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((c: CatalogCourse) => (
            <div key={c.id} className="card p-4 flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-ink text-sm leading-snug">{c.name}</h3>
                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded ${
                    c.difficulty === 'beginner' ? 'bg-success-bg text-success' :
                    c.difficulty === 'intermediate' ? 'bg-info-bg text-accent' :
                    'bg-warning-bg text-warning'
                  }`}>
                    {c.difficulty}
                  </span>
                </div>
                <p className="mt-1 text-xs text-support font-medium">{c.category}</p>
                <p className="mt-2 text-xs text-ink-2 line-clamp-3 leading-relaxed">{c.description}</p>
              </div>

              <div className="pt-2 border-t border-divider">
                <div className="text-[11px] text-support">
                  <span className="font-semibold text-ink">Aliases:</span> {c.aliases.slice(0, 3).join(', ')}
                  {c.aliases.length > 3 && ` +${c.aliases.length - 3} more`}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredCourses.length === 0 && (
          <div className="card p-12 text-center space-y-2">
            <p className="font-medium text-ink">No courses match your filter criteria.</p>
            <p className="text-sm text-ink-2">Try clearing the search query or resetting the category filter.</p>
            <Button small onClick={() => { setSearch(''); setSelectedCategory('all'); setSelectedDifficulty('all'); }}>
              Reset Filters
            </Button>
          </div>
        )}
      </section>
    </PageContainer>
  );
}
