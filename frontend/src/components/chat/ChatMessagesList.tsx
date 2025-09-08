import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { Loader2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ActivityTimeline, ProcessedEvent } from "@/components/ActivityTimeline";
import { HumanMessageBubble, AiMessageBubble } from "./message-bubbles";

interface ChatMessagesListProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
  handleCopy: (text: string, messageId: string) => void;
  copiedMessageId: string | null;
  showCompactTimeline: boolean;
}

export const ChatMessagesList: React.FC<ChatMessagesListProps> = ({
  messages,
  isLoading,
  scrollAreaRef,
  liveActivityEvents,
  historicalActivities,
  handleCopy,
  copiedMessageId,
  showCompactTimeline,
}) => {
  return (
    <ScrollArea className="flex-grow h-0" ref={scrollAreaRef}>
      <div className="p-4 md:p-6 space-y-2 min-h-full">
        {messages.map((message, index) => {
          const isLast = index === messages.length - 1;
          return (
            <div key={message.id || `msg-${index}`} className="space-y-3">
              <div
                className={`flex items-start gap-3 ${
                  message.type === "human" ? "justify-end" : ""
                }`}
              >
                {message.type === "human" ? (
                  <HumanMessageBubble message={message} />
                ) : (
                  <AiMessageBubble
                    message={message}
                    historicalActivity={historicalActivities[message.id!]}
                    liveActivity={liveActivityEvents}
                    isLastMessage={isLast}
                    isOverallLoading={isLoading}
                    handleCopy={handleCopy}
                    copiedMessageId={copiedMessageId}
                    showCompactTimeline={showCompactTimeline}
                  />
                )}
              </div>
            </div>
          );
        })}
        
        {/* Loading state for initial request */}
        {isLoading && messages.length === 0 && (
          <div className="flex items-start gap-3 mt-3">
            <div className="relative group max-w-[85%] md:max-w-[80%] rounded-xl p-3 shadow-sm break-words bg-card text-card-foreground border border-border rounded-bl-none w-full min-h-[56px]">
              <div className="flex items-center justify-start h-full">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
                <span>Initializing research...</span>
              </div>
            </div>
          </div>
        )}
        
        {/* Loading state when processing response */}
        {isLoading && messages.length > 0 && messages[messages.length - 1].type === "human" && (
          <div className="flex items-start gap-3 mt-3">
            <div className="relative group max-w-[85%] md:max-w-[80%] rounded-xl p-3 shadow-sm break-words bg-card text-card-foreground border border-border rounded-bl-none w-full min-h-[56px]">
              {showCompactTimeline ? (
                <div className="flex items-center justify-start h-full">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
                  <span>Processing... (Detailed information can be found in the right think panel)</span>
                </div>
              ) : (
                liveActivityEvents.length > 0 ? (
                  <div className="text-xs">
                    <ActivityTimeline
                      processedEvents={liveActivityEvents}
                      isLoading={true}
                    />
                  </div>
                ) : (
                  <div className="flex items-center justify-start h-full">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
                    <span>Processing...</span>
                  </div>
                )
              )}
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
};