import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import ReactMarkdown from "react-markdown";
import { HtmlRenderer, isHtmlContent, mdComponents } from "../renderers";

interface HumanMessageBubbleProps {
  message: Message;
}

export const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = ({
  message,
}) => {
  const content = typeof message.content === "string"
    ? message.content
    : JSON.stringify(message.content);

  return (
    <div
      className={`text-card-foreground rounded-3xl break-words min-h-7 bg-card border border-border max-w-[100%] sm:max-w-[90%] px-4 pt-3 rounded-br-lg`}
    >
      {isHtmlContent(content) ? (
        <HtmlRenderer content={content} />
      ) : (
        <ReactMarkdown components={mdComponents}>
          {content}
        </ReactMarkdown>
      )}
    </div>
  );
};