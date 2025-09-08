import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import ReactMarkdown from "react-markdown";
import { Copy, CopyCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ActivityTimeline, ProcessedEvent } from "@/components/ActivityTimeline";
import { HtmlRenderer, isHtmlContent, mdComponents } from "../renderers";

interface AiMessageBubbleProps {
  message: Message;
  historicalActivity: ProcessedEvent[] | undefined;
  liveActivity: ProcessedEvent[] | undefined;
  isLastMessage: boolean;
  isOverallLoading: boolean;
  handleCopy: (text: string, messageId: string) => void;
  copiedMessageId: string | null;
  showCompactTimeline: boolean;
}

export const AiMessageBubble: React.FC<AiMessageBubbleProps> = ({
  message,
  historicalActivity,
  liveActivity,
  isLastMessage,
  isOverallLoading,
  handleCopy,
  copiedMessageId,
  showCompactTimeline,
}) => {
  // Improved activity display logic - prioritize snapshots
  // 1. If historical activity snapshots exist, prioritize snapshots (avoid flickering)
  // 2. Only show live activity for the last message when no snapshot exists
  const hasHistoricalActivity = historicalActivity && historicalActivity.length > 0;
  const shouldShowLiveActivity = isLastMessage && isOverallLoading && !hasHistoricalActivity;
  
  const activityForThisBubble = hasHistoricalActivity 
    ? historicalActivity 
    : (shouldShowLiveActivity ? liveActivity : []);
  const isLiveActivityForThisBubble = shouldShowLiveActivity;

  // Debug information in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`🎯 AiMessageBubble [${message.id?.slice(-8)}]:`, {
      isLastMessage,
      hasHistoricalActivity,
      shouldShowLiveActivity,
      activityCount: activityForThisBubble?.length || 0,
      showingType: hasHistoricalActivity ? 'snapshot' : (shouldShowLiveActivity ? 'live' : 'none')
    });
  }

  const content = typeof message.content === "string"
    ? message.content
    : JSON.stringify(message.content);

  return (
    <div className={`relative break-words flex flex-col`}>
      {/* Debug status display in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="text-xs bg-blue-900 p-1 mb-2 rounded text-white">
          Message: {message.id} | Historical: {historicalActivity?.length || 0} | Live: {liveActivity?.length || 0} | Showing: {activityForThisBubble?.length || 0}
        </div>
      )}
      
      {/* Only show activity timeline when think panel is hidden */}
      {!showCompactTimeline && activityForThisBubble && activityForThisBubble.length > 0 && (
        <div className="mb-3 border-b border-neutral-700 pb-3 text-xs">
          <ActivityTimeline
            processedEvents={activityForThisBubble}
            isLoading={isLiveActivityForThisBubble}
          />
        </div>
      )}
      
      {/* Message content */}
      {isHtmlContent(content) ? (
        <HtmlRenderer content={content} />
      ) : (
        <ReactMarkdown components={mdComponents}>
          {content}
        </ReactMarkdown>
      )}
      
      {/* Copy button */}
      <Button
        variant="default"
        className="cursor-pointer bg-card border border-border text-card-foreground self-end"
        onClick={() => handleCopy(content, message.id!)}
      >
        {copiedMessageId === message.id ? "Copied" : "Copy"}
        {copiedMessageId === message.id ? <CopyCheck /> : <Copy />}
      </Button>
    </div>
  );
};