import { useState } from 'react';

export const useChatState = () => {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [showThinkPanel, setShowThinkPanel] = useState(true);

  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  const toggleThinkPanel = () => setShowThinkPanel(!showThinkPanel);

  return {
    copiedMessageId,
    showThinkPanel,
    handleCopy,
    toggleThinkPanel,
  };
};