import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { TaskDetail } from '@/utils/dataTransformer';
import { getStatusIcon, StatusBadge } from '../ui';
import { StepCard } from './StepCard';

interface TaskCardProps {
  task: TaskDetail;
  isExpanded: boolean;
  onToggleExpansion: () => void;
  expandedSteps: Set<string>;
  onToggleStepExpansion: (stepKey: string) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  isExpanded,
  onToggleExpansion,
  expandedSteps,
  onToggleStepExpansion,
}) => {
  console.log(`📋 TaskCard rendering: ${task.taskId}`, {
    stepsCount: task.steps.length,
    isExpanded,
    steps: task.steps.map(s => ({ type: s.type, title: s.title, hasDetails: !!(s.details && s.details.length > 0) }))
  });

  const getTaskStatusLabel = (status: string) => {
    switch (status) {
      case 'pending': return 'Pending';
      case 'in_progress': return 'In Progress';
      case 'completed': return 'Completed';
      default: return status;
    }
  };

  return (
    <div className="bg-gray-100 rounded-lg border border-gray-300">
      {/* Task Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={onToggleExpansion}
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-600" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-600" />
          )}
          {getStatusIcon(task.status)}
          <div className="flex-1">
            <div className="font-medium text-white">{task.description}</div>
            <div className="text-sm text-gray-600 mt-1">
              {task.steps.length} execution steps
            </div>
          </div>
          <StatusBadge status={task.status}>
            {getTaskStatusLabel(task.status)}
          </StatusBadge>
        </div>
      </div>

      {/* Task Steps */}
      {isExpanded && (
        <div className="border-t border-gray-300 p-4 space-y-3">
          {task.steps.length === 0 ? (
            <div className="text-center py-4 text-gray-600 text-sm">
              No execution steps available
            </div>
          ) : (
            task.steps.map((step, stepIndex) => {
              const stepKey = `${task.taskId}-${stepIndex}`;
              return (
                <StepCard
                  key={stepKey}
                  step={step}
                  stepKey={stepKey}
                  isExpanded={expandedSteps.has(stepKey)}
                  onToggleExpansion={() => onToggleStepExpansion(stepKey)}
                />
              );
            })
          )}
        </div>
      )}
    </div>
  );
};