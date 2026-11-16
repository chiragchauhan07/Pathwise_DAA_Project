import { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { CURATED_COURSES, type CatalogCourse } from '../data/coursesCatalog';
import { useRoadmap } from '../hooks/useRoadmap';
import { Button } from '../components/common/Button';

interface BenchmarkTopology {
  name: string;
  category: string;
  vertices: number;
  edges: number;
  expectedOrder: string;
  cycleExpected: boolean;
  courses: string[];
  description: string;
  mathematicalProperties: string;
}

const BENCHMARK_TOPOLOGIES: BenchmarkTopology[] = [
  {
    name: 'Linear Dependency Chain',
    category: 'Strict Sequential Path',
    vertices: 5,
    edges: 4,
    expectedOrder: 'Unique single topological order: V₁ → V₂ → V₃ → V₄ → V₅',
    cycleExpected: false,
    courses: [
      'Programming Fundamentals',
      'Data Structures',
      'Design and Analysis of Algorithms',
      'Advanced Algorithms and Complexity',
      'Computational Geometry',
    ],
    description: 'A continuous linear chain where every course strictly depends on its immediate predecessor. Represents strict vertical specialization.',
    mathematicalProperties: 'In-degree = 1, Out-degree = 1 for interior nodes. Exactly 1 valid topological ordering. Longest path equals |V| - 1 semesters.',
  },
  {
    name: 'Diamond / Fork-Join Network',
    category: 'Parallel Branches & Convergence',
    vertices: 6,
    edges: 6,
    expectedOrder: 'Foundation first, parallel tracks in middle waves, Capstone last',
    cycleExpected: false,
    courses: [
      'Programming Fundamentals',
      'Python Programming',
      'Linear Algebra',
      'Probability and Statistics',
      'Machine Learning',
      'Deep Learning',
    ],
    description: 'Foundational programming and math branch out into concurrent tracks and later converge into advanced applied courses.',
    mathematicalProperties: 'Tests simultaneous parallel wave resolution and multi-predecessor prerequisite convergence at the join node.',
  },
  {
    name: 'Wide Independent Forest',
    category: 'Zero Inter-Dependency',
    vertices: 5,
    edges: 0,
    expectedOrder: 'Deterministic alphabetical tie-breaking via min-heap',
    cycleExpected: false,
    courses: [
      'Calculus I',
      'Discrete Mathematics',
      'Linear Algebra',
      'Programming Fundamentals',
      'Technical Communication and Academic Writing',
    ],
    description: 'A set of independent entry-level courses with zero prerequisite edges between them. Tests workload leveling under semester capacity limits.',
    mathematicalProperties: 'In-degree = 0 for all nodes. Wave scheduler places all in Semester 1 if unconstrained; packs them evenly under capacity limits.',
  },
  {
    name: 'Dense Hierarchical Core',
    category: 'Multi-Tier Precedence',
    vertices: 8,
    edges: 11,
    expectedOrder: 'Wave 1 (Basics) → Wave 2 (Core CS) → Wave 3 (Systems & Algorithms)',
    cycleExpected: false,
    courses: [
      'Programming Fundamentals',
      'Discrete Mathematics',
      'Computer Organization and Architecture',
      'Data Structures',
      'Operating Systems',
      'Design and Analysis of Algorithms',
      'Database Management Systems',
      'Computer Networks',
    ],
    description: 'A realistic accredited computer science core curriculum exhibiting multiple overlapping prerequisites and depth-3 critical paths.',
    mathematicalProperties: 'Multiple shared prerequisites (e.g. Data Structures and Discrete Math both feeding DAA). Verifies DAG consistency.',
  },
  {
    name: 'Cyclic Conflict Benchmark',
    category: 'Circular Deadlock Verification',
    vertices: 3,
    edges: 3,
    expectedOrder: 'Rejected before scheduling (Cycle Conflict Detected)',
    cycleExpected: true,
    courses: [
      'Data Structures',
      'Design and Analysis of Algorithms',
      'Advanced Algorithms and Complexity',
    ],
    description: 'Synthetically introduces or simulates an impossible circular requirement (e.g. A requires B requires C requires A).',
    mathematicalProperties: 'Directed graph contains at least one back-edge (v_k, v_0). Iterative 3-state DFS identifies the exact cycle path.',
  },
];

export default function CurriculumPage() {
  const { setDraft } = useRoadmap();
  const navigate = useNavigate();

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

  const loadPreset = (presetCourses: string[], goal: string) => {
    setDraft((d) => ({
      ...d,
      courses: presetCourses,
      goal,
    }));
    navigate('/');
  };

  return (
    <PageContainer className="pt-10 pb-20">
      <header className="max-w-3xl">
        <div className="flex items-center gap-2">
          <span className="badge badge-curated">Knowledge Base & Curriculum</span>
          <span className="badge badge-neutral">Graph Theory</span>
        </div>
        <h1 className="h-page mt-3">Curriculum Knowledge Base & Graph Modeling</h1>
        <p className="mt-3 text-base text-ink-2 leading-relaxed">
          The foundation of the <strong>Dependency-Aware Course Registration Assistant</strong> is a verified,
          mathematically consistent directed graph representation of academic curricula. Explore the curated catalog,
          formal graph definitions, and synthetic benchmark curricula below.
        </p>
      </header>

      {/* Section 1: Formal Graph Modeling */}
      <section className="mt-12 space-y-6">
        <div className="flex items-baseline justify-between border-b border-divider pb-3">
          <h2 className="text-xl font-bold tracking-tight text-ink">1. Formal Graph-Theoretic Formulation</h2>
          <Link to="/daa" className="text-sm font-semibold text-accent hover:underline">
            View DAA Algorithm Details →
          </Link>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2 font-semibold text-ink">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-info-bg font-mono text-sm text-accent">V</span>
              Vertices (Courses)
            </div>
            <p className="text-sm text-ink-2 leading-relaxed">
              Every course is a distinct vertex <code className="font-mono text-xs">v ∈ V</code> with canonical attributes including unique ID, credit value, academic difficulty tier, and thematic specialization domain.
            </p>
          </div>

          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2 font-semibold text-ink">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-info-bg font-mono text-sm text-accent">E</span>
              Directed Edges (Prerequisites)
            </div>
            <p className="text-sm text-ink-2 leading-relaxed">
              A directed edge <code className="font-mono text-xs">(u, v) ∈ E</code> asserts that course <code className="font-mono text-xs">u</code> must be completed strictly prior to registering for course <code className="font-mono text-xs">v</code>.
            </p>
          </div>

          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2 font-semibold text-ink">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-info-bg font-mono text-sm text-accent">DAG</span>
              Topological Invariant
            </div>
            <p className="text-sm text-ink-2 leading-relaxed">
              Registration planning is valid if and only if <code className="font-mono text-xs">G = (V, E)</code> is a <strong>Directed Acyclic Graph</strong>. Any directed cycle introduces an unsolvable circular deadlock.
            </p>
          </div>
        </div>
      </section>

      {/* Section 2: Synthetic Benchmark Topologies */}
      <section className="mt-16 space-y-6">
        <div className="flex items-baseline justify-between border-b border-divider pb-3">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-ink">2. Synthetic Curriculum Benchmarks</h2>
            <p className="text-sm text-ink-2 mt-1">Evaluated topologies demonstrating topological sort performance and constraint boundaries.</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {BENCHMARK_TOPOLOGIES.map((topo) => (
            <div key={topo.name} className="card p-5 flex flex-col justify-between space-y-4 hover:border-accent transition-colors">
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-ink text-base">{topo.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${topo.cycleExpected ? 'bg-error-bg text-error border border-error' : 'bg-subtle text-ink-2'}`}>
                    {topo.category}
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-3 text-xs text-support font-mono">
                  <span>|V| = {topo.vertices} courses</span>
                  <span>·</span>
                  <span>|E| = {topo.edges} edges</span>
                </div>
                <p className="mt-3 text-sm text-ink-2 leading-relaxed">{topo.description}</p>
                <div className="mt-3 rounded-lg bg-subtle p-2.5 text-xs text-ink-2">
                  <strong className="text-ink">DAA Analysis:</strong> {topo.mathematicalProperties}
                </div>
              </div>

              <div className="pt-2">
                <Button
                  small
                  className="w-full"
                  onClick={() => loadPreset(topo.courses, topo.name)}
                >
                  Load in Planner →
                </Button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Section 3: Interactive Knowledge Base Catalog */}
      <section className="mt-16 space-y-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between border-b border-divider pb-3">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-ink">3. Academic Knowledge Base Catalog</h2>
            <p className="text-sm text-ink-2 mt-1">
              Browse the {CURATED_COURSES.length} curated computer science and engineering courses. All input queries are validated strictly against this catalog.
            </p>
          </div>
          <span className="text-sm font-semibold text-accent font-mono">
            {filteredCourses.length} of {CURATED_COURSES.length} courses
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
                  <h4 className="font-semibold text-ink text-sm leading-snug">{c.name}</h4>
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
