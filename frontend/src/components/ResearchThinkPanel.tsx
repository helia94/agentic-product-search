import React from 'react';
import { AlertCircle } from 'lucide-react';
import { ProcessedResearchData } from '@/utils/dataTransformer';
import { StatusBadge, LoadingSpinner } from './research-panel/ui';
import { PlanningSection, TaskExecutionSection } from './research-panel/sections';
import { useExpansionState } from './research-panel/hooks';

interface ResearchThinkPanelProps {
  researchData: ProcessedResearchData | null;
  isLoading: boolean;
}

export const ResearchThinkPanel: React.FC<ResearchThinkPanelProps> = ({
  researchData,
  isLoading
}) => {
  const {
    expandedTasks,
    expandedSteps,
    toggleTaskExpansion,
    toggleStepExpansion,
  } = useExpansionState(researchData);

  if (!researchData) {
    return <EmptyState />;
  }

  const getOverallStatusLabel = (status: string) => {
    switch (status) {
      case 'planning': return 'Planning';
      case 'researching': return 'Researching';
      case 'completed': return 'Completed';
      default: return status;
    }
  };

  return (
    <div className="bg-gray-50 rounded-lg h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-300 p-6">
        <h2 className="text-xl font-semibold text-white mb-2">Research Think Panel</h2>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <StatusBadge status={researchData.overallStatus} size="md">
            {getOverallStatusLabel(researchData.overallStatus)}
          </StatusBadge>
          {isLoading && <LoadingSpinner />}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <PlanningSection planning={researchData.planning} />
        <TaskExecutionSection
          tasks={researchData.tasks}
          expandedTasks={expandedTasks}
          expandedSteps={expandedSteps}
          onToggleTaskExpansion={toggleTaskExpansion}
          onToggleStepExpansion={toggleStepExpansion}
        />
      </div>
    </div>
  );
};

const EmptyState: React.FC = () => (
  <div className="bg-gray-50 rounded-lg p-6 h-full">
    <div className="flex items-center justify-center h-full text-gray-600">
      <div className="text-center">
        <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>Waiting for research to start...</p>
      </div>
    </div>
  </div>
);