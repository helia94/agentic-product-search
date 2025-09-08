import React from 'react';
import { ProcessedResearchData } from '@/utils/dataTransformer';

interface UseExpansionStateReturn {
  expandedTasks: Set<string>;
  expandedSteps: Set<string>;
  toggleTaskExpansion: (taskId: string) => void;
  toggleStepExpansion: (stepKey: string) => void;
}

export const useExpansionState = (
  researchData: ProcessedResearchData | null
): UseExpansionStateReturn => {
  const [expandedTasks, setExpandedTasks] = React.useState<Set<string>>(new Set());
  const [expandedSteps, setExpandedSteps] = React.useState<Set<string>>(new Set());

  // Auto-expansion logic when research data changes
  React.useEffect(() => {
    if (researchData) {
      console.log("🎯 Think Panel: Auto-expand logic triggered", {
        currentTaskId: researchData.currentTaskId,
        overallStatus: researchData.overallStatus,
        tasksCount: researchData.tasks.length
      });

      // Auto-expand current task and all tasks with steps
      const tasksWithSteps = researchData.tasks.filter(t => t.steps.length > 0);
      console.log("🎯 Think Panel: Tasks with steps:", tasksWithSteps.map(t => ({ id: t.taskId, stepsCount: t.steps.length })));
      
      if (tasksWithSteps.length > 0) {
        const taskIdsToExpand = tasksWithSteps.map(t => t.taskId);
        setExpandedTasks(new Set(taskIdsToExpand));
        
        // Auto-expand all steps of these tasks
        const stepKeysToExpand = tasksWithSteps.flatMap(task => 
          task.steps.map((_, index) => `${task.taskId}-${index}`)
        );
        setExpandedSteps(new Set(stepKeysToExpand));
        
        console.log("🎯 Think Panel: Auto-expanding", {
          expandedTasks: taskIdsToExpand,
          expandedSteps: stepKeysToExpand.length
        });
      }
      
      // When research is complete, expand all tasks and steps to show complete process
      if (researchData.overallStatus === 'completed') {
        const allTaskIds = researchData.tasks.map(t => t.taskId);
        setExpandedTasks(new Set(allTaskIds));
        
        const allStepKeys = researchData.tasks.flatMap(task => 
          task.steps.map((_, index) => `${task.taskId}-${index}`)
        );
        setExpandedSteps(new Set(allStepKeys));
        
        console.log("🎯 Think Panel: Research complete, expanding all", {
          allTasks: allTaskIds.length,
          allSteps: allStepKeys.length
        });
      }
    }
  }, [researchData?.currentTaskId, researchData?.overallStatus, researchData?.tasks?.length]);

  const toggleTaskExpansion = React.useCallback((taskId: string) => {
    setExpandedTasks(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(taskId)) {
        newExpanded.delete(taskId);
      } else {
        newExpanded.add(taskId);
      }
      return newExpanded;
    });
  }, []);

  const toggleStepExpansion = React.useCallback((stepKey: string) => {
    setExpandedSteps(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(stepKey)) {
        newExpanded.delete(stepKey);
      } else {
        newExpanded.add(stepKey);
      }
      return newExpanded;
    });
  }, []);

  return {
    expandedTasks,
    expandedSteps,
    toggleTaskExpansion,
    toggleStepExpansion,
  };
};