import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  CheckCircle2, 
  Circle, 
  AlertCircle, 
  Clock, 
  Play,
  Square,
  StopCircle
} from 'lucide-react';

interface NodeProgressEvent {
  event_type: "node_start" | "node_end" | "node_error" | "graph_start" | "graph_end";
  node_name: string;
  graph_name?: string;
  duration_ms?: number;
  error?: string;
  metadata?: Record<string, any>;
}

interface ProgressTrackerProps {
  progressEvents: NodeProgressEvent[];
  currentStatus?: {
    status: string;
    query: string;
    html_file_path?: string;
    error?: string;
  } | null;
  onStop?: () => void;
  isStoppable?: boolean;
}

const NODE_DISPLAY_NAMES: Record<string, string> = {
  'pars_query': 'Parsing Query',
  'enrich_query': 'Enriching Query',
  'human_ask_for_use_case': 'Asking for Use Case',
  'find_criteria': 'Finding Criteria',
  'query_generator': 'Generating Queries',
  'call_product_search_graph': 'Searching Products',
  'select_final_products': 'Selecting Products',
  'complete_product_info': 'Completing Product Info',
  'save_results_to_disk': 'Saving Results',
  'generate_html_results': 'Generating Report',
  '__GRAPH_START__': 'Starting Analysis',
  '__GRAPH_END__': 'Analysis Complete',
  '__GRAPH_ERROR__': 'Analysis Error'
};

const getNodeIcon = (event: NodeProgressEvent, isActive: boolean) => {
  const iconClass = "w-4 h-4";
  
  if (event.event_type === "node_error") {
    return <AlertCircle className={`${iconClass} text-red-600`} />;
  }
  
  if (event.event_type === "node_end") {
    return <CheckCircle2 className={`${iconClass} text-green-600`} />;
  }
  
  if (event.event_type === "node_start" && isActive) {
    return <Play className={`${iconClass} text-blue-600 animate-pulse`} />;
  }
  
  return <Circle className={`${iconClass} text-gray-500`} />;
};

const formatDuration = (ms?: number): string => {
  if (!ms) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed': return 'bg-green-500';
    case 'failed': return 'bg-red-500';
    case 'awaiting_human_input': return 'bg-yellow-500';
    case 'running': return 'bg-blue-500';
    default: return 'bg-gray-500';
  }
};

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ 
  progressEvents, 
  currentStatus,
  onStop,
  isStoppable = false
}) => {
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new progress events come in
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [progressEvents]);

  // Group events by node to track start/end pairs
  const nodeStates = new Map<string, {
    started: NodeProgressEvent | null;
    ended: NodeProgressEvent | null;
    error: NodeProgressEvent | null;
  }>();

  // Process events chronologically
  progressEvents.forEach(event => {
    const key = event.node_name;
    if (!nodeStates.has(key)) {
      nodeStates.set(key, { started: null, ended: null, error: null });
    }
    
    const state = nodeStates.get(key)!;
    
    switch (event.event_type) {
      case 'node_start':
      case 'graph_start':
        state.started = event;
        break;
      case 'node_end':
      case 'graph_end':
        state.ended = event;
        break;
      case 'node_error':
        state.error = event;
        break;
    }
  });

  // Convert to sorted list for display
  const nodeList = Array.from(nodeStates.entries())
    .map(([key, state]) => {
      const event = state.error || state.ended || state.started;
      const isActive = Boolean(state.started && !state.ended && !state.error);
      const isCompleted = Boolean(state.ended || state.error);
      
      return {
        key,
        event: event!,
        isActive,
        isCompleted,
        duration: state.ended?.duration_ms || state.error?.duration_ms,
        error: state.error?.error
      };
    })
    .filter(item => item.event)
    .sort((a, b) => {
      // Sort by timestamp of the first event for each node
      const aTime = a.event ? new Date(progressEvents.find(e => 
        e.node_name === a.event.node_name
      )?.metadata?.timestamp || 0).getTime() : 0;
      const bTime = b.event ? new Date(progressEvents.find(e => 
        e.node_name === b.event.node_name
      )?.metadata?.timestamp || 0).getTime() : 0;
      return aTime - bTime;
    });

  return (
    <Card className="w-full bg-gray-50 border-gray-300">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-gray-800">
            Analysis Progress
          </CardTitle>
          <div className="flex items-center gap-2">
            {currentStatus && (
              <Badge 
                variant="secondary" 
                className={`${getStatusColor(currentStatus.status)} text-white`}
              >
                {currentStatus.status.replace('_', ' ').toUpperCase()}
              </Badge>
            )}
            {isStoppable && onStop && (
              <Button
                onClick={onStop}
                size="sm"
                variant="destructive"
                className="bg-red-500 hover:bg-red-600 text-white"
              >
                <StopCircle className="w-4 h-4 mr-1" />
                Stop
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64 w-full" ref={scrollAreaRef}>
          <div className="space-y-2">
            {nodeList.length === 0 ? (
              <div className="text-gray-600 text-center py-4">
                <Square className="w-8 h-8 mx-auto mb-2" />
                Waiting to start...
              </div>
            ) : (
              nodeList.map(({ key, event, isActive, isCompleted, duration, error }) => (
                <div 
                  key={key}
                  className={`flex items-center gap-3 p-2 rounded-md transition-colors ${
                    isActive ? 'bg-blue-100 border border-blue-300' : 
                    isCompleted ? 'bg-gray-100' : 'bg-gray-50'
                  }`}
                >
                  <div className="flex-shrink-0">
                    {getNodeIcon(event, isActive)}
                  </div>
                  
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-medium truncate ${
                        isActive ? 'text-blue-700' : 
                        error ? 'text-red-700' : 
                        isCompleted ? 'text-green-700' : 'text-gray-700'
                      }`}>
                        {NODE_DISPLAY_NAMES[event.node_name] || event.node_name}
                      </span>
                      
                      {duration && (
                        <div className="flex items-center gap-1 text-xs text-gray-600">
                          <Clock className="w-3 h-3" />
                          {formatDuration(duration)}
                        </div>
                      )}
                    </div>
                    
                    {event.graph_name && event.graph_name !== 'main' && (
                      <div className="text-xs text-gray-600 truncate">
                        {event.graph_name}
                      </div>
                    )}
                    
                    {error && (
                      <div className="text-xs text-red-600 truncate mt-1">
                        Error: {error}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
        
        {currentStatus?.error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-300 rounded-md">
            <div className="flex items-center gap-2 text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="font-medium">Error:</span>
              <span className="truncate">{currentStatus.error}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};