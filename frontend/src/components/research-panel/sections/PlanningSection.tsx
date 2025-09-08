import React from 'react';
import { ProcessedResearchData } from '@/utils/dataTransformer';
import { getStatusIcon } from '../ui';

interface PlanningSectionProps {
  planning: ProcessedResearchData['planning'];
}

export const PlanningSection: React.FC<PlanningSectionProps> = ({ planning }) => {
  if (!planning) return null;

  return (
    <div className="border-b border-gray-300 p-6">
      <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
        <div className="h-2 w-2 bg-purple-400 rounded-full"></div>
        Research Planning Strategy
      </h3>
      
      <div className="bg-gray-100 rounded-lg p-4">
        <PlanningStats planning={planning} />
        <PlanningTasks planning={planning} />
      </div>
    </div>
  );
};

interface PlanningStatsProps {
  planning: NonNullable<ProcessedResearchData['planning']>;
}

const PlanningStats: React.FC<PlanningStatsProps> = ({ planning }) => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
    <div className="text-center">
      <div className="text-2xl font-bold text-purple-400">{planning.totalTasks}</div>
      <div className="text-sm text-gray-600">Total Tasks</div>
    </div>
    <div className="text-center">
      <div className="text-2xl font-bold text-blue-400">{planning.currentTaskIndex + 1}</div>
      <div className="text-sm text-gray-600">Current Task</div>
    </div>
    <div className="text-center">
      <div className="text-2xl font-bold text-green-400">
        {planning.tasks.filter(t => t.status === 'completed').length}
      </div>
      <div className="text-sm text-gray-600">Completed</div>
    </div>
  </div>
);

interface PlanningTasksProps {
  planning: NonNullable<ProcessedResearchData['planning']>;
}

const PlanningTasks: React.FC<PlanningTasksProps> = ({ planning }) => (
  <div className="space-y-2">
    {planning.tasks.map((task, index) => (
      <div
        key={task.id}
        className={`flex items-center gap-3 p-3 rounded-lg ${
          index === planning.currentTaskIndex
            ? 'bg-blue-900/30 border border-blue-800'
            : 'bg-gray-200/50'
        }`}
      >
        <div className="text-sm font-mono text-gray-600 w-8">
          #{index + 1}
        </div>
        {getStatusIcon(task.status)}
        <div className="flex-1 text-sm text-white">{task.description}</div>
      </div>
    ))}
  </div>
);