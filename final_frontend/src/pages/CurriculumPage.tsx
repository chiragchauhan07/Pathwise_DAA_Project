import { useState, useMemo } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { CURATED_COURSES, type CatalogCourse } from '../data/coursesCatalog';
import { Button } from '../components/common/Button';

export default function CurriculumPage() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [selectedSemester, setSelectedSemester] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('sem-asc');
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const categories = useMemo(() => {
    const set = new Set(CURATED_COURSES.map((c) => c.category));
    return ['all', ...Array.from(set).sort()];
  }, []);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (selectedCategory !== 'all') count++;
    if (selectedDifficulty !== 'all') count++;
    if (selectedSemester !== 'all') count++;
    if (sortBy !== 'sem-asc') count++;
    return count;
  }, [selectedCategory, selectedDifficulty, selectedSemester, sortBy]);

  const resetAllFilters = () => {
    setSelectedCategory('all');
    setSelectedDifficulty('all');
    setSelectedSemester('all');
    setSortBy('sem-asc');
    setSearch('');
  };

  const difficultyWeight: Record<string, number> = {
    beginner: 1,
    intermediate: 2,
    advanced: 3,
  };

  const filteredAndSortedCourses = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = CURATED_COURSES.filter((c) => {
      const matchSearch =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        c.aliases.some((a) => a.toLowerCase().includes(q));
      const matchCategory = selectedCategory === 'all' || c.category === selectedCategory;
      const matchDifficulty = selectedDifficulty === 'all' || c.difficulty === selectedDifficulty;
      const matchSemester = selectedSemester === 'all' || String(c.semester) === selectedSemester;
      return matchSearch && matchCategory && matchDifficulty && matchSemester;
    });

    return filtered.sort((a, b) => {
      if (sortBy === 'sem-asc') {
        if (a.semester !== b.semester) return a.semester - b.semester;
        return a.name.localeCompare(b.name);
      }
      if (sortBy === 'sem-desc') {
        if (a.semester !== b.semester) return b.semester - a.semester;
        return a.name.localeCompare(b.name);
      }
      if (sortBy === 'name-asc') {
        return a.name.localeCompare(b.name);
      }
      if (sortBy === 'name-desc') {
        return b.name.localeCompare(a.name);
      }
      if (sortBy === 'diff-asc') {
        const dDiff = (difficultyWeight[a.difficulty] || 0) - (difficultyWeight[b.difficulty] || 0);
        if (dDiff !== 0) return dDiff;
        return a.name.localeCompare(b.name);
      }
      if (sortBy === 'diff-desc') {
        const dDiff = (difficultyWeight[b.difficulty] || 0) - (difficultyWeight[a.difficulty] || 0);
        if (dDiff !== 0) return dDiff;
        return a.name.localeCompare(b.name);
      }
      return 0;
    });
  }, [search, selectedCategory, selectedDifficulty, selectedSemester, sortBy]);

  return (
    <PageContainer className="pt-10 pb-20">
      <header className="max-w-2xl">
        <h1 className="h-page">Academic Course Catalog</h1>
        <p className="mt-3 text-base text-ink-2 leading-relaxed">
          The knowledge base contains {CURATED_COURSES.length} curated Computer Science courses and 136 prerequisite dependencies across Semesters 1 through 8. Search or filter courses below to explore available subjects and their topics.
        </p>
      </header>

      <section className="mt-8 space-y-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between border-b border-divider pb-3">
          <h2 className="text-lg font-semibold text-ink">Catalog Explorer</h2>
          <span className="text-sm font-medium text-accent font-mono">
            Showing {filteredAndSortedCourses.length} of {CURATED_COURSES.length} courses
          </span>
        </div>

        {/* Search Bar & Filter and Sort Toggle */}
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

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-all ${
                isFilterOpen || activeFiltersCount > 0
                  ? 'bg-accent/10 border-accent text-accent'
                  : 'bg-surface border-divider text-ink hover:border-accent/40'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
              <span>Filter and Sort</span>
              {activeFiltersCount > 0 && (
                <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-accent rounded-full">
                  {activeFiltersCount}
                </span>
              )}
              <svg
                className={`w-3.5 h-3.5 transition-transform duration-200 ${isFilterOpen ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {activeFiltersCount > 0 && (
              <button
                type="button"
                onClick={resetAllFilters}
                className="text-xs text-muted hover:text-accent underline px-2 py-1"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Expandable Filter and Sort Panel */}
        {isFilterOpen && (
          <div className="card p-5 border border-accent/20 bg-surface-alt/40 space-y-4 animate-in fade-in duration-200">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Semester Dropdown */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">
                  Semester
                </label>
                <select
                  className="field text-sm w-full"
                  value={selectedSemester}
                  onChange={(e) => setSelectedSemester(e.target.value)}
                >
                  <option value="all">All Semesters (1–8)</option>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
                    <option key={sem} value={String(sem)}>
                      Semester {sem}
                    </option>
                  ))}
                </select>
              </div>

              {/* Category Dropdown */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">
                  Category
                </label>
                <select
                  className="field text-sm w-full"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="all">All Categories</option>
                  {categories.filter((c) => c !== 'all').map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Difficulty Dropdown */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">
                  Difficulty
                </label>
                <select
                  className="field text-sm w-full"
                  value={selectedDifficulty}
                  onChange={(e) => setSelectedDifficulty(e.target.value)}
                >
                  <option value="all">All Difficulties</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>

              {/* Sort By Dropdown */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">
                  Sort Order
                </label>
                <select
                  className="field text-sm w-full"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                >
                  <option value="sem-asc">Semester: 1 to 8</option>
                  <option value="sem-desc">Semester: 8 to 1</option>
                  <option value="name-asc">Course Title: A to Z</option>
                  <option value="name-desc">Course Title: Z to A</option>
                  <option value="diff-asc">Difficulty: Easy to Hard</option>
                  <option value="diff-desc">Difficulty: Hard to Easy</option>
                </select>
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-divider/60 text-xs">
              <span className="text-support">
                Active filters: <strong className="text-ink">{filteredAndSortedCourses.length}</strong> matches found
              </span>
              <button
                type="button"
                onClick={resetAllFilters}
                className="text-xs text-accent hover:underline font-medium"
              >
                Clear All Filters &amp; Sorting
              </button>
            </div>
          </div>
        )}

        {/* Course cards grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredAndSortedCourses.map((c: CatalogCourse) => (
            <div key={c.id} className="card p-4 flex flex-col justify-between space-y-3 hover:border-accent/30 transition-colors">
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-ink text-sm leading-snug">{c.name}</h3>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-surface border border-divider text-ink-2">
                      Sem {c.semester}
                    </span>
                    <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded ${
                      c.difficulty === 'beginner' ? 'bg-success-bg text-success' :
                      c.difficulty === 'intermediate' ? 'bg-info-bg text-accent' :
                      'bg-warning-bg text-warning'
                    }`}>
                      {c.difficulty}
                    </span>
                  </div>
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

        {filteredAndSortedCourses.length === 0 && (
          <div className="card p-12 text-center space-y-2">
            <p className="font-medium text-ink">No courses match your filter criteria.</p>
            <p className="text-sm text-ink-2">Try clearing the search query or resetting the filter and sort options.</p>
            <Button small onClick={resetAllFilters}>
              Reset Filters
            </Button>
          </div>
        )}
      </section>
    </PageContainer>
  );
}
