/**
 * Data transformer: Convert flat event streams into hierarchical task structures
 */

// Add type definitions
export interface EventData {
  [key: string]: unknown;
}

export interface SourceData {
  title?: string;
  url?: string;
  label?: string;
  snippet?: string;
}

export interface TaskData {
  id: string;
  description: string;
  status?: string;
}

export interface StateData {
  plan?: TaskData[];
  ledger?: TaskData[];
  current_task_pointer?: number;
  [key: string]: unknown;
}

export interface TaskDetail {
  taskId: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  steps: TaskStep[];
}

export interface TaskStep {
  type: 'planning' | 'query_generation' | 'web_research' | 'reflection' | 'content_enhancement' | 'evaluation' | 'completion';
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'skipped';
  timestamp?: string;
  data?: EventData;
  details?: StepDetail[];
}

export interface StepDetail {
  type: 'search_queries' | 'sources' | 'analysis' | 'decision';
  content: string;
  metadata?: {
    count?: number;
    sources?: SourceData[];
    is_sufficient?: boolean;
    knowledge_gap?: string;
    follow_up_queries?: string[];
    status?: string;
    decision?: string;
    [key: string]: unknown;
  };
}

export interface PlanningInfo {
  totalTasks: number;
  currentTaskIndex: number;
  tasks: Array<{
    id: string;
    description: string;
    status: string;
  }>;
}

export interface ProcessedResearchData {
  planning: PlanningInfo | null;
  tasks: TaskDetail[];
  currentTaskId: string | null;
  overallStatus: 'planning' | 'researching' | 'completed';
}

/**
 * Main transformation function: Convert event streams to hierarchical structure
 */
export function transformEventsToHierarchy(
  events: EventData[],
  messages: EventData[]
): ProcessedResearchData {
  
  console.log(`🔄 Starting transformation of ${events.length} events`);
  
  // Count event types
  const eventTypes: Record<string, number> = {};
  events.forEach(event => {
    Object.keys(event).forEach(key => {
      eventTypes[key] = (eventTypes[key] || 0) + 1;
    });
  });
  
  console.log(`📊 Event type statistics:`, eventTypes);
  
  // Initialize result structure
  const result: ProcessedResearchData = {
    planning: null,
    tasks: [],
    currentTaskId: null,
    overallStatus: 'planning'
  };

  // Collect all state information
  let latestState: StateData = {};
  
  // Extract latest state from events
  events.forEach(event => {
    Object.keys(event).forEach(key => {
      if (event[key] && typeof event[key] === 'object') {
        latestState = { ...latestState, ...event[key] as StateData };
      }
    });
  });

  // If there are messages, extract state from the last AI message
  const lastAIMessage = [...messages].reverse().find(msg => 
    typeof msg === 'object' && msg !== null && 'type' in msg && msg.type === 'ai'
  );
  if (lastAIMessage && typeof lastAIMessage === 'object' && 'content' in lastAIMessage) {
    // Try to parse possible state information
    // State extraction logic can be extended here as needed
  }

  // 1. Process Planning information
  result.planning = extractPlanningInfo(events, latestState);
  
  // 2. Build task details
  result.tasks = buildTaskDetails(events, latestState);
  
  // 3. Determine current task and overall status
  result.currentTaskId = getCurrentTaskId(latestState);
  result.overallStatus = determineOverallStatus(events);

  return result;
}

/**
 * Extract Planning information
 */
function extractPlanningInfo(events: EventData[], state: StateData): PlanningInfo | null {
  // Look for planning-related events
  const planningEvent = events.find(event => 
    event.planner || event.planner_node || event.planning
  );
  
  if (!planningEvent && !state.plan) {
    return null;
  }

  const plan = state.plan || [];
  const currentPointer = state.current_task_pointer || 0;

  return {
    totalTasks: plan.length,
    currentTaskIndex: currentPointer,
    tasks: plan.map((task: TaskData) => ({
      id: task.id || 'unknown',
      description: task.description || 'Unknown task',
      status: task.status || 'pending'
    }))
  };
}

/**
 * Build task details
 */
function buildTaskDetails(events: EventData[], state: StateData): TaskDetail[] {
  const plan = state.plan || [];
  const currentPointer = state.current_task_pointer || 0;

  console.log(`🏗️ Building task details: Total tasks ${plan.length}, Current pointer ${currentPointer}`);

  return plan.map((task: TaskData, index: number) => {
    const taskId = task.id;
    console.log(`📋 Processing task ${index}: ${taskId} - ${task.description}`);
    
    // Determine task status
    let taskStatus: 'pending' | 'in_progress' | 'completed' = 'pending';
    if (index < currentPointer) {
      taskStatus = 'completed';
    } else if (index === currentPointer) {
      taskStatus = 'in_progress';
    }

    // Build task steps - build steps for all tasks, not just current task
    const shouldShowSteps = index <= currentPointer;
    console.log(`📋 Task ${index} status: ${taskStatus}, Should show steps: ${shouldShowSteps}`);
    const steps = buildTaskSteps(events, taskId, shouldShowSteps);
    console.log(`📋 Task ${index} built ${steps.length} steps`);

    return {
      taskId,
      description: task.description || 'Unknown task',
      status: taskStatus,
      steps
    };
  });
}

/**
 * Build task steps - improved version, supports showing historical steps for all tasks
 */
function buildTaskSteps(
  events: EventData[], 
  taskId: string, 
  shouldShowSteps: boolean // Show steps for current task or completed tasks
): TaskStep[] {
  const steps: TaskStep[] = [];

  console.log(`🔧 Building task steps for ${taskId}, shouldShowSteps: ${shouldShowSteps}`);
  console.log(`📊 Total events: ${events.length}`);

  // If current task or completed task, build steps based on events
  if (shouldShowSteps) {
    // 1. Query Generation
    const queryEvents = events.filter(event => event.generate_query);
    console.log(`🔍 Query事件数: ${queryEvents.length}`);
    if (queryEvents.length > 0) {
      const lastQueryEvent = queryEvents[queryEvents.length - 1];
      const queryData = lastQueryEvent.generate_query as { query_list?: string[] };
      steps.push({
        type: 'query_generation',
        title: 'Generating Search Queries',
        status: 'completed',
        data: lastQueryEvent.generate_query as EventData,
        details: [{
          type: 'search_queries',
          content: queryData.query_list?.join(', ') || 'No queries',
          metadata: { 
            count: queryData.query_list?.length || 0,
            queries: queryData.query_list || []
          }
        }]
      });
    }

    // 2. Web Research - 改进版本，显示更多详情
    const webResearchEvents = events.filter(event => event.web_research);
    console.log(`🔍 Web Research事件数: ${webResearchEvents.length}`);
    if (webResearchEvents.length > 0) {
      webResearchEvents.forEach((event) => {
        const researchData = event.web_research as { 
          sources_gathered?: SourceData[];
          executed_search_queries?: string[];
          search_query?: string;
          total_sources?: number;
        };
        
        // 从executed_search_queries或search_query中获取真实的查询
        let searchQuery = 'Unknown Query';
        if (researchData.executed_search_queries && researchData.executed_search_queries.length > 0) {
          searchQuery = researchData.executed_search_queries[0];
        } else if (researchData.search_query) {
          searchQuery = researchData.search_query;
        }
        
        const sources = researchData.sources_gathered || [];
        
        // 从sources中提取真实的信息，按照后端返回的实际结构
        const processedSources = sources.map((source: SourceData & { label?: string; short_url?: string; value?: string }) => {
          // 后端返回的sources结构：{label, short_url, value, title?, snippet?}
          return {
            title: source.title || source.label || 'Source',
            url: source.value || source.short_url || source.url || '',
            label: source.label || 'Web',
            snippet: source.snippet || 'No preview available'
          };
        });
        
        steps.push({
          type: 'web_research',
          title: `Web Research: ${searchQuery}`,
          status: 'completed',
          data: event.web_research as EventData,
          details: [
            {
              type: 'search_queries',
              content: `Query: "${searchQuery}"`,
              metadata: { query: searchQuery }
            },
            {
              type: 'sources',
              content: `Found ${sources.length} relevant sources`,
              metadata: { 
                count: sources.length,
                sources: processedSources,
                totalFound: sources.length
              }
            }
          ]
        });
      });
    }

    // 3. Reflection
    const reflectionEvents = events.filter(event => event.reflection);
    console.log(`🔍 Reflection事件数: ${reflectionEvents.length}`);
    if (reflectionEvents.length > 0) {
      const lastReflection = reflectionEvents[reflectionEvents.length - 1];
      console.log(`🤔 Reflection数据:`, lastReflection.reflection);
      const reflectionData = lastReflection.reflection as {
        reflection_is_sufficient?: boolean;
        reflection_knowledge_gap?: string;
        reflection_follow_up_queries?: string[];
      };
      
      const details = [];
      
      // 主要分析结果
      details.push({
        type: 'analysis' as const,
        content: reflectionData.reflection_is_sufficient 
          ? '✅ Research quality meets requirements - sufficient information gathered'
          : '⚠️ Additional research needed - quality requirements not met',
        metadata: {
          is_sufficient: reflectionData.reflection_is_sufficient,
          status: reflectionData.reflection_is_sufficient ? 'sufficient' : 'insufficient'
        }
      });
      
      // 知识差距分析
      if (reflectionData.reflection_knowledge_gap) {
        details.push({
          type: 'analysis' as const,
          content: `Knowledge Gap Identified: ${reflectionData.reflection_knowledge_gap}`,
          metadata: {
            knowledge_gap: reflectionData.reflection_knowledge_gap,
            gap_type: 'content_depth'
          }
        });
      }
      
      // Follow-up queries
      if (reflectionData.reflection_follow_up_queries && reflectionData.reflection_follow_up_queries.length > 0) {
        details.push({
          type: 'decision' as const,
          content: `Recommended follow-up research areas: ${reflectionData.reflection_follow_up_queries.length} queries identified`,
          metadata: {
            follow_up_queries: reflectionData.reflection_follow_up_queries,
            action_needed: !reflectionData.reflection_is_sufficient
          }
        });
      }
      
      console.log(`🤔 添加Reflection步骤，详情数量: ${details.length}`);
      steps.push({
        type: 'reflection',
        title: 'Reflection Analysis',
        status: 'completed',
        data: lastReflection.reflection as EventData,
        details: details
      });
    }

    // 4. Content Enhancement
    const enhancementEvents = events.filter(event => event.content_enhancement);
    console.log(`🔍 Content Enhancement事件数: ${enhancementEvents.length}`);
    if (enhancementEvents.length > 0) {
      const lastEnhancement = enhancementEvents[enhancementEvents.length - 1];
      console.log(`🔧 Content Enhancement数据:`, lastEnhancement.content_enhancement);
      const enhancementData = lastEnhancement.content_enhancement as {
        enhancement_status?: string;
        enhancement_decision?: string;
        enhancement_reasoning?: string;
      };
      const status = enhancementData.enhancement_status;
      
      const details = [];
      
      // Enhancement决策
      details.push({
        type: 'decision' as const,
        content: getEnhancementStatusMessage(status || 'unknown'),
        metadata: { 
          status,
          decision: enhancementData.enhancement_decision,
          automated: true
        }
      });
      
      // Enhancement reasoning如果存在
      if (enhancementData.enhancement_reasoning) {
        details.push({
          type: 'analysis' as const,
          content: `Reasoning: ${enhancementData.enhancement_reasoning}`,
          metadata: {
            reasoning_type: 'content_quality',
            reasoning: enhancementData.enhancement_reasoning
          }
        });
      }
      
      console.log(`🔧 添加Content Enhancement步骤，状态: ${status}, 详情数量: ${details.length}`);
      steps.push({
        type: 'content_enhancement',
        title: 'Content Enhancement Analysis',
        status: status === 'skipped' ? 'skipped' : 'completed',
        data: lastEnhancement.content_enhancement as EventData,
        details: details
      });
    }

    // 5. Research Evaluation
    const evaluationEvents = events.filter(event => event.evaluate_research_enhanced);
    console.log(`🔍 Research Evaluation事件数: ${evaluationEvents.length}`);
    if (evaluationEvents.length > 0) {
      const lastEvaluation = evaluationEvents[evaluationEvents.length - 1];
      console.log(`📊 Research Evaluation数据:`, lastEvaluation.evaluate_research_enhanced);
      const evaluationData = lastEvaluation.evaluate_research_enhanced as {
        evaluation_is_sufficient?: boolean;
        evaluation_reasoning?: string;
        quality_score?: number;
      };
      
      const details = [];
      
      // 主要评估结果
      details.push({
        type: 'analysis' as const,
        content: evaluationData.evaluation_is_sufficient
          ? '✅ Research meets quality standards - ready for report generation'
          : '❌ Research quality insufficient - additional work required',
        metadata: {
          is_sufficient: evaluationData.evaluation_is_sufficient,
          evaluation_type: 'quality_assessment',
          quality_score: evaluationData.quality_score
        }
      });
      
      // 评估推理信息
      if (evaluationData.evaluation_reasoning) {
        details.push({
          type: 'analysis' as const,
          content: `Quality Assessment: ${evaluationData.evaluation_reasoning}`,
          metadata: {
            reasoning: evaluationData.evaluation_reasoning,
            assessment_type: 'automated'
          }
        });
      }
      
      console.log(`📊 添加Research Evaluation步骤，是否充分: ${evaluationData.evaluation_is_sufficient}, 详情数量: ${details.length}`);
      steps.push({
        type: 'evaluation',
        title: 'Research Quality Evaluation',
        status: 'completed',
        data: lastEvaluation.evaluate_research_enhanced as EventData,
        details: details
      });
    }

    // 6. Task Completion
    const completionEvents = events.filter(event => event.record_task_completion);
    if (completionEvents.length > 0) {
      steps.push({
        type: 'completion',
        title: 'Task Completion Recorded',
        status: 'completed',
        data: completionEvents[completionEvents.length - 1].record_task_completion as EventData
      });
    }
  }

  return steps;
}

/**
 * 获取当前任务ID
 */
function getCurrentTaskId(state: StateData): string | null {
  const plan = state.plan || [];
  const currentPointer = state.current_task_pointer || 0;
  
  if (plan[currentPointer]) {
    return plan[currentPointer].id;
  }
  
  return null;
}

/**
 * 确定整体状态
 */
function determineOverallStatus(events: EventData[]): 'planning' | 'researching' | 'completed' {
  // 检查是否有finalize_answer事件
  const finalizeEvents = events.filter(event => event.finalize_answer);
  if (finalizeEvents.length > 0) {
    return 'completed';
  }

  // 检查是否有planning
  const planningEvents = events.filter(event => event.planner || event.planner_node);
  if (planningEvents.length > 0) {
    return 'researching';
  }

  return 'planning';
}

/**
 * 获取增强状态消息
 */
function getEnhancementStatusMessage(status: string): string {
  const statusMessages: Record<string, string> = {
    "skipped": "Content enhancement skipped - quality sufficient",
    "completed": "Content enhancement completed successfully", 
    "failed": "Content enhancement failed",
    "error": "Content enhancement encountered errors",
    "analyzing": "Analyzing content enhancement needs",
    "skipped_no_api": "Content enhancement skipped - no API key"
  };
  
  return statusMessages[status] || `Status: ${status}`;
}

/**
 * 调试函数：打印转换结果
 */
export function debugTransformResult(data: ProcessedResearchData): void {
  console.log('🔍 转换结果分析:', {
    planning: data.planning,
    tasksCount: data.tasks.length,
    currentTaskId: data.currentTaskId,
    overallStatus: data.overallStatus,
    tasks: data.tasks.map(task => ({
      id: task.taskId,
      description: task.description,
      status: task.status,
      stepsCount: task.steps.length
    }))
  });
} 