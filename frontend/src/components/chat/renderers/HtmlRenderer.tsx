import type React from "react";
import DOMPurify from 'dompurify';

interface HtmlRendererProps {
  content: string;
}

export const HtmlRenderer: React.FC<HtmlRendererProps> = ({ content }) => {
  const sanitizedHtml = DOMPurify.sanitize(content, {
    WHOLE_DOCUMENT: true,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
    SANITIZE_DOM: true,
    KEEP_CONTENT: true,
    ADD_TAGS: ['html', 'head', 'body', 'meta', 'link', 'style', 'title'],
    ADD_ATTR: ['charset', 'name', 'content', 'rel', 'href', 'type', 'media']
  });
  
  return (
    <div 
      dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
      className="w-full h-full html-content-reset"
      style={{ 
        minHeight: '100%',
        overflow: 'auto'
      }}
    />
  );
};