import type React from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ResearchThinkPanel } from "@/components/ResearchThinkPanel";
import { ProgressTracker } from "@/components/ProgressTracker";
import { transformEventsToHierarchy, EventData } from "@/utils/dataTransformer";
import { useMemo } from "react";
import type { Message } from "@langchain/langgraph-sdk";
import type { ProcessedEvent } from "@/components/ActivityTimeline";

interface NodeProgressEvent {
  event_type: "node_start" | "node_end" | "node_error" | "graph_start" | "graph_end";
  node_name: string;
  graph_name: string;
  duration_ms?: number;
  error?: string;
  metadata?: Record<string, any>;
}

interface JobStatus {
  status: string;
  query: string;
  html_file_path?: string;
  error?: string;
}

interface ChatPanelsProps {
  showThinkPanel: boolean;
  onToggleThinkPanel: () => void;
  messages: Message[];
  isLoading: boolean;
  liveActivityEvents: ProcessedEvent[];
  progressEvents?: NodeProgressEvent[];
  currentStatus?: JobStatus | null;
  onStop?: () => void;
  children: React.ReactNode;
}

export const ChatPanels: React.FC<ChatPanelsProps> = ({
  showThinkPanel,
  onToggleThinkPanel,
  messages,
  isLoading,
  liveActivityEvents,
  progressEvents = [],
  currentStatus = null,
  onStop,
  children,
}) => {
  // Get transformed research data
  const researchData = useMemo(() => {
    try {
      // Get event data from sessionStorage
      const storedEvents = JSON.parse(sessionStorage.getItem('research_events') || '[]') as EventData[];
      if (storedEvents.length === 0) {
        console.log("🔍 Think Panel: No stored event data");
        return null;
      }
      
      console.log(`🔍 Think Panel: Processing ${storedEvents.length} events`);
      const result = transformEventsToHierarchy(storedEvents, messages || []);
      console.log("🔍 Think Panel: Transformation results", {
        tasksCount: result.tasks.length,
        overallStatus: result.overallStatus,
        currentTaskId: result.currentTaskId,
        tasks: result.tasks.map(t => ({
          id: t.taskId,
          description: t.description,
          stepsCount: t.steps.length,
          steps: t.steps.map(s => ({ type: s.type, title: s.title, status: s.status }))
        }))
      });
      
      return result;
    } catch (error) {
      console.warn("⚠️ Think Panel: Unable to get research data:", error);
      return null;
    }
  }, [messages, liveActivityEvents, isLoading]); // Add isLoading dependency to ensure real-time updates

  return (
    <div className="flex h-full">
      {/* Left message area */}
      <div className={`flex flex-col transition-all duration-300 ${showThinkPanel ? 'w-1/2' : 'w-full'}`}>
        {/* Toggle button */}
        <div className="flex justify-between items-center p-4 border-b border-border flex-shrink-0">
          <h3 className="text-lg font-medium text-foreground">Conversation</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={onToggleThinkPanel}
            className="text-muted-foreground border-border hover:bg-accent"
          >
            {showThinkPanel ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
            {showThinkPanel ? 'Hide Think Panel' : 'Show Think Panel'}
          </Button>
        </div>

        {children}
      </div>

      {/* Right panel - progress tracker or think panel */}
      {showThinkPanel && (
        <div className="w-1/2 border-l border-border flex flex-col h-full">
          {/* Show progress tracker if there are progress events, otherwise show think panel */}
          {progressEvents.length > 0 || isLoading ? (
            <div className="p-4 h-full overflow-auto">
              <ProgressTracker 
                progressEvents={progressEvents}
                currentStatus={currentStatus}
                onStop={onStop}
                isStoppable={isLoading && currentStatus?.status !== "cancelled"}
              />
            </div>
          ) : (
            <ResearchThinkPanel 
              researchData={researchData}
              isLoading={isLoading}
            />
          )}
        </div>
      )}
    </div>
  );
};