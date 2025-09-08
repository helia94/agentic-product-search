import React from 'react';
import { Clock } from 'lucide-react';
import { ProcessedResearchData } from '@/utils/dataTransformer';
import { TaskCard } from '../cards';

interface TaskExecutionSectionProps {
  tasks: ProcessedResearchData['tasks'];
  expandedTasks: Set<string>;
  expandedSteps: Set<string>;
  onToggleTaskExpansion: (taskId: string) => void;
  onToggleStepExpansion: (stepKey: string) => void;
}

export const TaskExecutionSection: React.FC<TaskExecutionSectionProps> = ({
  tasks,
  expandedTasks,
  expandedSteps,
  onToggleTaskExpansion,
  onToggleStepExpansion,
}) => {
  return (
    <div className="p-6">
      <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
        <div className="h-2 w-2 bg-green-400 rounded-full"></div>
        Task Execution Details
      </h3>
      
      {tasks.length === 0 ? (
        <EmptyTasksState />
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskCard
              key={task.taskId}
              task={task}
              isExpanded={expandedTasks.has(task.taskId)}
              onToggleExpansion={() => onToggleTaskExpansion(task.taskId)}
              expandedSteps={expandedSteps}
              onToggleStepExpansion={onToggleStepExpansion}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const EmptyTasksState: React.FC = () => (
  <div className="text-center py-8 text-gray-600">
    <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
    <p>No task details available</p>
  </div>
);