import { useId, useMemo } from 'react';
import type { RoadmapModel } from '../../types/roadmap';
import { capitalize } from '../../utils/formatters';
import { asStrength, byStrength, isAi, RelationBadge, SourceBadge, STRENGTH_LABEL } from '../common/relations';

interface RoadPoint {
  x: number;
  y: number;
}

export function RoadmapCanvas({
  roadmap,
  selectedId,
  onSelectCourse,
}: {
  roadmap: RoadmapModel;
  selectedId: string | null;
  onSelectCourse: (id: string | null) => void;
}) {
  const filterId = useId();
  const courses = roadmap.courses;
  const names = useMemo(() => new Map(courses.map((c) => [c.course_id, c.name])), [courses]);

  // Layout parameters for SVG road
  const SVG_WIDTH = 700;
  const START_Y = 60;
  const STEP_Y = 120;
  const LEFT_X = 200;
  const RIGHT_X = 500;

  // Calculate coordinates for each course milestone along the winding road
  const milestoneCoords = useMemo(() => {
    return courses.map((_, index) => {
      // Alternate left and right to form a winding snake road
      const isLeft = index % 2 === 0;
      const x = isLeft ? LEFT_X : RIGHT_X;
      const y = START_Y + (index + 1) * STEP_Y;
      return { x, y, isLeft };
    });
  }, [courses]);

  const startPoint: RoadPoint = {
    x: courses.length > 0 ? (milestoneCoords[0].isLeft ? LEFT_X : RIGHT_X) : SVG_WIDTH / 2,
    y: START_Y,
  };

  const endPoint: RoadPoint = {
    x: courses.length > 0 ? milestoneCoords[milestoneCoords.length - 1].x : SVG_WIDTH / 2,
    y: START_Y + (courses.length + 1) * STEP_Y,
  };

  const totalHeight = endPoint.y + 60;

  // Construct SVG cubic Bezier path string connecting start -> milestone 1 -> milestone 2 -> ... -> destination
  const roadPathD = useMemo(() => {
    if (courses.length === 0) return '';
    const points: RoadPoint[] = [startPoint, ...milestoneCoords.map((m) => ({ x: m.x, y: m.y })), endPoint];

    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p1 = points[i];
      const p2 = points[i + 1];
      const midY = (p1.y + p2.y) / 2;
      // Smooth S-curve control points
      d += ` C ${p1.x} ${midY}, ${p2.x} ${midY}, ${p2.x} ${p2.y}`;
    }
    return d;
  }, [courses, milestoneCoords, startPoint, endPoint]);

  const selectedCourse = useMemo(() => {
    return courses.find((c) => c.course_id === selectedId) ?? null;
  }, [courses, selectedId]);

  return (
    <div className="relative space-y-4">
      {/* Top Banner with Instructions */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-ink-2">
        <p className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-accent" aria-hidden />
          <span>Follow the road from <b>Start</b> to <b>Goal</b> in the computed prerequisite order.</span>
        </p>
        <p className="text-support">Click any milestone pin to inspect prerequisites & details.</p>
      </div>

      {/* Main Winding Road Canvas */}
      <div
        className="relative overflow-x-auto rounded-2xl border border-divider bg-surface p-2 sm:p-6"
        tabIndex={0}
        role="region"
        aria-label="Interactive winding learning road"
      >
        <svg
          viewBox={`0 0 ${SVG_WIDTH} ${totalHeight}`}
          className="mx-auto w-full max-w-4xl"
          style={{ minHeight: `${Math.min(totalHeight, 480)}px` }}
          role="img"
          aria-label={`Learning journey road containing ${courses.length} milestones`}
        >
          <defs>
            {/* Subtle drop shadow for road milestone cards */}
            <filter id={`${filterId}-shadow`} x="-10%" y="-10%" width="125%" height="125%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.06" />
            </filter>
            <filter id={`${filterId}-glow`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="var(--color-accent)" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* 1. Underlying Road Asphalt / Base */}
          <path
            d={roadPathD}
            fill="none"
            stroke="#e4e4e7"
            strokeWidth="38"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="transition-colors duration-200"
          />

          {/* 2. Road Border Edges */}
          <path
            d={roadPathD}
            fill="none"
            stroke="#d4d4d8"
            strokeWidth="38"
            strokeDasharray="1 0"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ strokeOpacity: 0.4 }}
          />

          {/* 3. Road Inner Center Stripe (Dashed Highway Marking) */}
          <path
            d={roadPathD}
            fill="none"
            stroke="#ffffff"
            strokeWidth="2.5"
            strokeDasharray="8 8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* 4. Starting Point Marker */}
          <g transform={`translate(${startPoint.x}, ${startPoint.y})`} className="cursor-default" aria-label="Start of Journey">
            <circle r="18" fill="var(--color-surface)" stroke="#248a3d" strokeWidth="2.5" />
            <path d="M-5 -6 L5 0 L-5 6 Z" fill="#248a3d" />
            <text x="0" y="-26" textAnchor="middle" fontSize="12" fontWeight="700" fill="#248a3d" letterSpacing="0.05em">
              START
            </text>
          </g>

          {/* 5. Destination Point Marker */}
          <g transform={`translate(${endPoint.x}, ${endPoint.y})`} className="cursor-default" aria-label="Goal Destination">
            <circle r="20" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="3" />
            {/* Target Flag / Star Icon */}
            <circle r="10" fill="var(--color-accent)" />
            <circle r="4" fill="#ffffff" />
            <text x="0" y="36" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--color-ink)" letterSpacing="0.05em">
              GOAL DESTINATION
            </text>
          </g>

          {/* 6. Course Milestones along the Road */}
          {courses.map((course, idx) => {
            const coord = milestoneCoords[idx];
            const isSelected = course.course_id === selectedId;
            const isLeft = coord.isLeft;

            // Milestone Pin is on the road center at (coord.x, coord.y)
            // Milestone Label Card sits off to the side so it NEVER overlaps the road
            const cardWidth = 220;
            const cardHeight = 60;
            const cardX = isLeft ? coord.x + 38 : coord.x - cardWidth - 38;
            const cardY = coord.y - cardHeight / 2;

            return (
              <g
                key={course.course_id}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                aria-label={`Milestone ${course.order}: ${course.name}. Semester ${course.semester ?? 'unassigned'}. Click to inspect details.`}
                className="group cursor-pointer focus:outline-none"
                onClick={() => onSelectCourse(isSelected ? null : course.course_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectCourse(isSelected ? null : course.course_id);
                  }
                }}
              >
                {/* Connecting Leader Line from road milestone circle to side card */}
                <line
                  x1={coord.x}
                  y1={coord.y}
                  x2={isLeft ? cardX : cardX + cardWidth}
                  y2={coord.y}
                  stroke={isSelected ? 'var(--color-accent)' : '#d4d4d8'}
                  strokeWidth={isSelected ? '2' : '1.5'}
                  strokeDasharray={isSelected ? 'none' : '3 3'}
                />

                {/* Milestone Node Pin on Road */}
                <circle
                  cx={coord.x}
                  cy={coord.y}
                  r={isSelected ? 18 : 15}
                  fill={isSelected ? 'var(--color-accent)' : 'var(--color-surface)'}
                  stroke={isSelected ? 'var(--color-accent)' : '#18181b'}
                  strokeWidth={isSelected ? 3 : 2}
                  filter={isSelected ? `url(#${filterId}-glow)` : `url(#${filterId}-shadow)`}
                  className="transition-all duration-150 group-hover:scale-110"
                />

                {/* Milestone Step Number */}
                <text
                  x={coord.x}
                  y={coord.y + 1}
                  dy="0.35em"
                  textAnchor="middle"
                  fontSize="12"
                  fontWeight="700"
                  fill={isSelected ? '#ffffff' : '#18181b'}
                  pointerEvents="none"
                >
                  {course.order}
                </text>

                {/* Milestone Side Card */}
                <g transform={`translate(${cardX}, ${cardY})`}>
                  <rect
                    width={cardWidth}
                    height={cardHeight}
                    rx="12"
                    fill="var(--color-surface)"
                    stroke={isSelected ? 'var(--color-accent)' : '#e4e4e7'}
                    strokeWidth={isSelected ? 2 : 1}
                    filter={`url(#${filterId}-shadow)`}
                    className="transition-all duration-150 group-hover:stroke-accent/60"
                  />

                  {/* Semester Tag or Provenance Badge inside Card */}
                  <rect
                    x="10"
                    y="8"
                    width={course.semester ? 64 : 54}
                    height="18"
                    rx="9"
                    fill={course.semester ? 'var(--color-subtle)' : 'var(--color-info-bg)'}
                  />
                  <text
                    x={10 + (course.semester ? 32 : 27)}
                    y="17"
                    dy="0.35em"
                    textAnchor="middle"
                    fontSize="9.5"
                    fontWeight="600"
                    fill={course.semester ? 'var(--color-ink-2)' : '#00539f'}
                  >
                    {course.semester ? `Sem ${course.semester}` : 'Core'}
                  </text>

                  {/* Difficulty Tag */}
                  {course.difficulty && (
                    <text
                      x={cardWidth - 10}
                      y="17"
                      dy="0.35em"
                      textAnchor="end"
                      fontSize="9.5"
                      fontWeight="500"
                      fill="var(--color-muted)"
                    >
                      {capitalize(String(course.difficulty))}
                    </text>
                  )}

                  {/* Course Name Truncated cleanly to two lines if needed */}
                  <text
                    x="10"
                    y="37"
                    fontSize="11.5"
                    fontWeight="600"
                    fill={isSelected ? 'var(--color-accent)' : 'var(--color-ink)'}
                  >
                    {course.name.length > 25 ? `${course.name.slice(0, 23)}…` : course.name}
                  </text>

                  {/* Category subtext */}
                  <text
                    x="10"
                    y="50"
                    fontSize="9"
                    fontWeight="400"
                    fill="var(--color-muted)"
                  >
                    {course.category.length > 30 ? `${course.category.slice(0, 28)}…` : course.category}
                  </text>
                </g>
              </g>
            );
          })}
        </svg>
      </div>

      {/* 7. Milestone Inspection Detail Panel (Shows when a milestone is clicked) */}
      {selectedCourse && (
        <aside
          role="region"
          aria-label={`Milestone Details: ${selectedCourse.name}`}
          className="card border-accent/40 bg-surface p-5 shadow-[var(--shadow-pop)] transition-all animate-in fade-in"
        >
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-divider pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-accent text-xs font-bold text-white">
                  {selectedCourse.order}
                </span>
                <h3 className="h-card text-ink">{selectedCourse.name}</h3>
                {selectedCourse.semester && (
                  <span className="badge badge-neutral">Semester {selectedCourse.semester}</span>
                )}
                {selectedCourse.is_ai_inferred && (
                  <span className="badge badge-ai">AI Inferred</span>
                )}
                {selectedCourse.provenance === 'ai_disambiguated' && (
                  <span className="badge badge-ai">Disambiguated</span>
                )}
              </div>
              <p className="text-support mt-1">
                {[
                  selectedCourse.difficulty && capitalize(String(selectedCourse.difficulty)),
                  selectedCourse.category,
                  selectedCourse.course_id,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </div>
            <button
              type="button"
              className="btn btn-sm btn-quiet"
              onClick={() => onSelectCourse(null)}
              aria-label="Close milestone details"
            >
              Close
            </button>
          </div>

          {/* Description */}
          {selectedCourse.description && (
            <p className="mt-3 text-sm leading-relaxed text-ink-2">{selectedCourse.description}</p>
          )}

          {/* Prerequisites Grid */}
          <div className="mt-4 grid gap-4 border-t border-divider pt-3 md:grid-cols-2">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">
                Prerequisites (Take Before)
              </h4>
              {selectedCourse.prerequisites.length === 0 ? (
                <p className="mt-1 text-sm text-ink-2">None required among your chosen courses.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {selectedCourse.prerequisites.sort(byStrength).map((p) => (
                    <li key={p.courseId} className="rounded-lg bg-surface-2 p-2.5 text-sm">
                      <div className="flex flex-wrap items-center gap-1.5 font-medium">
                        <RelationBadge type={p.type} />
                        <span>{names.get(p.courseId) ?? p.courseId}</span>
                        {isAi(p) && <SourceBadge ai />}
                      </div>
                      {p.explanation && (
                        <p className="mt-1 text-xs text-ink-2">{p.explanation}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">
                Unlocks (Prerequisite For)
              </h4>
              {selectedCourse.unlocks.length === 0 ? (
                <p className="mt-1 text-sm text-ink-2">Terminal course; unlocks no other selected courses.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {selectedCourse.unlocks.map((u) => (
                    <li key={u.courseId} className="rounded-lg bg-surface-2 p-2.5 text-sm">
                      <div className="flex flex-wrap items-center gap-1.5 font-medium">
                        <span className="font-semibold">{names.get(u.courseId) ?? u.courseId}</span>
                        <span className="text-xs text-muted">({STRENGTH_LABEL[asStrength(u.type) ?? 'optional']})</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
