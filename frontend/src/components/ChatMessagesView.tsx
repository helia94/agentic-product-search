import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { InputForm } from "@/components/InputForm";
import { ProcessedEvent } from "@/components/ActivityTimeline";
import { HtmlRenderer, isHtmlContent } from "./chat/renderers";
import { ChatPanels } from "./chat/layout";
import { ChatMessagesList } from "./chat/ChatMessagesList";
import { useChatState } from "@/hooks";

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

interface HumanInteractionRequest {
  question: string;
  query: string;
}

interface ChatMessagesViewProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (inputValue: string, effort: string) => void;
  onCancel: () => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
  progressEvents?: NodeProgressEvent[];
  currentStatus?: JobStatus | null;
  humanRequest?: HumanInteractionRequest | null;
  onSubmitHumanResponse?: (response: string) => void;
  onStop?: () => void;
}

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  liveActivityEvents,
  historicalActivities,
  progressEvents = [],
  currentStatus = null,
  humanRequest = null,
  onSubmitHumanResponse,
  onStop,
}: ChatMessagesViewProps) {
  const { copiedMessageId, showThinkPanel, handleCopy, toggleThinkPanel } = useChatState();

  // Check if the last AI message contains HTML content
  const lastAiMessage = messages.filter(msg => msg.type === "ai").pop();
  const lastAiContent = lastAiMessage ? (typeof lastAiMessage.content === "string" ? lastAiMessage.content : JSON.stringify(lastAiMessage.content)) : "";
  const hasHtmlResult = lastAiMessage && isHtmlContent(lastAiContent);

  // If we have HTML result, show it full-screen with input below
  if (hasHtmlResult) {
    return (
      <div className="flex flex-col h-full">
        {/* Full-screen HTML content */}
        <div className="flex-1 w-full h-full overflow-hidden">
          <HtmlRenderer content={lastAiContent} />
        </div>
        
        {/* Human Question Display for HTML view */}
        {humanRequest && onSubmitHumanResponse && (
          <div className="flex-shrink-0 p-4 bg-gray-900/50 border-t border-gray-700">
            <div className="max-w-2xl">
              <p className="text-foreground mb-3">{humanRequest.question.split('\n')[0]}</p>
              <div className="space-y-2">
                {humanRequest.question.split('\n')
                  .filter(line => /^\d+\.\s/.test(line.trim()))
                  .map((line, index) => {
                    const option = line.replace(/^\d+\.\s/, '').trim();
                    return (
                      <button
                        key={index}
                        onClick={() => onSubmitHumanResponse(option)}
                        className="block w-full text-left px-3 py-2 text-sm bg-blue-600/10 hover:bg-blue-600/20 border border-blue-600/30 rounded-lg transition-colors text-blue-400"
                      >
                        {index + 1}. {option}
                      </button>
                    );
                  })}
              </div>
            </div>
          </div>
        )}
        
        {/* Input form at the bottom */}
        <div className="flex-shrink-0">
          <InputForm
            onSubmit={onSubmit}
            isLoading={isLoading}
            onCancel={onCancel}
            hasHistory={messages.length > 0}
            humanRequest={humanRequest}
          />
        </div>
      </div>
    );
  }

  return (
    <>
      <ChatPanels
        showThinkPanel={showThinkPanel}
        onToggleThinkPanel={toggleThinkPanel}
        messages={messages}
        isLoading={isLoading}
        liveActivityEvents={liveActivityEvents}
        progressEvents={progressEvents}
        currentStatus={currentStatus}
        onStop={onStop}
      >
        <ChatMessagesList
          messages={messages}
          isLoading={isLoading}
          scrollAreaRef={scrollAreaRef}
          liveActivityEvents={liveActivityEvents}
          historicalActivities={historicalActivities}
          handleCopy={handleCopy}
          copiedMessageId={copiedMessageId}
          showCompactTimeline={showThinkPanel}
          humanRequest={humanRequest}
          onSubmitHumanResponse={onSubmitHumanResponse}
        />
        
        <div className="flex-shrink-0">
          <InputForm
            onSubmit={onSubmit}
            isLoading={isLoading}
            onCancel={onCancel}
            hasHistory={messages.length > 0}
            humanRequest={humanRequest}
          />
        </div>
      </ChatPanels>
    </>
  );
}