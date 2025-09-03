import { useState, useEffect, useRef, useCallback } from "react";

// Define message type locally
interface Message {
  type: "human" | "ai";
  content: string;
  id: string;
}

// Custom hook to replace LangGraph SDK useStream
interface SearchState {
  messages: Message[];
  isLoading: boolean;
  submit: (data: { messages: Message[]; effort: string; reasoning_model: string }) => Promise<void>;
  stop: () => void;
}

function useSearchApi(): SearchState {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const currentJobId = useRef<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const submit = useCallback(async (data: { messages: Message[]; effort: string; reasoning_model: string }) => {
    setIsLoading(true);
    setMessages(data.messages);

    try {
      // Start the search job
      const apiUrl = import.meta.env.DEV ? "http://localhost:8000" : "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: data.messages[data.messages.length - 1].content,
          effort: data.effort
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const { job_id } = await response.json();
      currentJobId.current = job_id;

      // Start streaming updates
      eventSourceRef.current = new EventSource(`${apiUrl}/api/search/${job_id}/stream`);
      
      eventSourceRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.event === "job_complete" && data.data.status === "completed") {
            // Get the HTML result
            const htmlFilePath = data.data.html_file_path;
            if (htmlFilePath) {
              fetch(`${apiUrl}/api/results/${htmlFilePath}`)
                .then(res => res.text())
                .then(htmlContent => {
                  const aiMessage: Message = {
                    type: "ai",
                    content: htmlContent,
                    id: Date.now().toString()
                  };
                  setMessages(prev => [...prev, aiMessage]);
                  setIsLoading(false);
                  eventSourceRef.current?.close();
                });
            } else {
              setIsLoading(false);
              eventSourceRef.current?.close();
            }
          }
        } catch (error) {
          console.error("Error parsing stream event:", error);
        }
      };

      eventSourceRef.current.onerror = (error) => {
        console.error("EventSource failed:", error);
        setIsLoading(false);
        eventSourceRef.current?.close();
      };

    } catch (error) {
      console.error("Search submission failed:", error);
      setIsLoading(false);
    }
  }, []);

  const stop = useCallback(() => {
    eventSourceRef.current?.close();
    setIsLoading(false);
  }, []);

  return { messages, isLoading, submit, stop };
}
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";

export default function App() {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const thread = useSearchApi();


  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [thread.messages]);


  const handleSubmit = useCallback(
    (submittedInputValue: string, effort: string, model: string) => {
      if (!submittedInputValue.trim()) return;
      
      const newMessages: Message[] = [
        ...(thread.messages || []),
        {
          type: "human",
          content: submittedInputValue,
          id: Date.now().toString(),
        },
      ];
      thread.submit({
        messages: newMessages,
        effort: effort,
        reasoning_model: model,
      });
    },
    [thread]
  );

  const handleCancel = useCallback(() => {
    thread.stop();
  }, [thread]);


  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      <main className="flex-1 flex flex-col overflow-hidden w-full h-full">
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {thread.messages.length === 0 ? (
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={thread.isLoading}
              onCancel={handleCancel}
            />
          ) : (
            <ChatMessagesView
              messages={thread.messages}
              isLoading={thread.isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              liveActivityEvents={[]}
              historicalActivities={{}}
            />
          )}
        </div>
      </main>
    </div>
  );
}
