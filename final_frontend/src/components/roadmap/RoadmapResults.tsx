import { useState } from 'react';
import type { RoadmapModel } from '../../types/roadmap';
import { friendlyWarning } from '../../utils/warnings';
import { Alert } from '../common/ErrorState';
import { Tabs } from '../common/Tabs';
import { CourseRoadmap } from './CourseRoadmap';
import { RationalePanel } from './RationalePanel';
import { RelationshipExplorer } from './RelationshipExplorer';
import { SemesterSchedule } from './SemesterSchedule';
import { Summary } from './Summary';

export function RoadmapResults({ roadmap }: { roadmap: RoadmapModel }) {
  const [tab, setTab] = useState('journey');

  return (
    <div className="space-y-6">
      <div>
        <p className="text-support">Learning goal</p>
        <h2 className="h-section mt-0.5">{roadmap.goal}</h2>
      </div>

      <Summary roadmap={roadmap} />

      {roadmap.warnings.length > 0 && (
        <Alert
          tone="warning"
          role="note"
          title={roadmap.warnings.length === 1 ? 'Note about this path' : `${roadmap.warnings.length} notes about this path`}
        >
          <ul className="list-disc space-y-1 pl-4">
            {roadmap.warnings.map((w, i) => (
              <li key={i}>{friendlyWarning(w)}</li>
            ))}
          </ul>
        </Alert>
      )}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: 'journey', label: 'Journey', content: <CourseRoadmap roadmap={roadmap} /> },
          { id: 'semesters', label: 'Semesters', content: <SemesterSchedule roadmap={roadmap} /> },
          { id: 'prerequisites', label: 'Prerequisites', content: <RelationshipExplorer roadmap={roadmap} /> },
          { id: 'explanations', label: 'Explanations', content: <RationalePanel roadmap={roadmap} /> },
        ]}
      />
    </div>
  );
}
