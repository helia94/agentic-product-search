import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { InputForm } from "@/components/InputForm";
import { HumanInteractionModal } from "@/components/HumanInteractionModal";
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
      <>
        {/* Human Interaction Modal */}
        {humanRequest && onSubmitHumanResponse && (
          <HumanInteractionModal
            question={humanRequest.question}
            query={humanRequest.query}
            onSubmit={onSubmitHumanResponse}
            isVisible={true}
          />
        )}

        <div className="flex flex-col h-full">
          {/* Full-screen HTML content */}
          <div className="flex-1 w-full h-full overflow-hidden">
            <HtmlRenderer content={lastAiContent} />
          </div>
          
          {/* Input form at the bottom */}
          <div className="flex-shrink-0">
            <InputForm
              onSubmit={onSubmit}
              isLoading={isLoading}
              onCancel={onCancel}
              hasHistory={messages.length > 0}
            />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      {/* Human Interaction Modal */}
      {humanRequest && onSubmitHumanResponse && (
        <HumanInteractionModal
          question={humanRequest.question}
          query={humanRequest.query}
          onSubmit={onSubmitHumanResponse}
          isVisible={true}
        />
      )}

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
        />
        
        <div className="flex-shrink-0">
          <InputForm
            onSubmit={onSubmit}
            isLoading={isLoading}
            onCancel={onCancel}
            hasHistory={messages.length > 0}
          />
        </div>
      </ChatPanels>
    </>
  );
}