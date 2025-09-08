import type React from "react";
import { useEffect, useRef } from "react";
import DOMPurify from 'dompurify';

interface HtmlRendererProps {
  content: string;
}

export const HtmlRenderer: React.FC<HtmlRendererProps> = ({ content }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    console.log('HtmlRenderer: Received content length:', content.length);
    
    // Parse the full HTML document and extract what we need
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, 'text/html');
    
    // Extract styles from head
    const styles = doc.querySelectorAll('style');
    const bodyContent = doc.body?.innerHTML || '';
    const scripts = doc.querySelectorAll('script');
    
    console.log('HtmlRenderer: Found', styles.length, 'style tags');
    console.log('HtmlRenderer: Found', scripts.length, 'script tags');
    console.log('HtmlRenderer: Body content length:', bodyContent.length);
    
    // Add styles to document head
    styles.forEach((style, index) => {
      const newStyle = document.createElement('style');
      newStyle.textContent = style.textContent;
      newStyle.id = `html-renderer-style-${index}`;
      document.head.appendChild(newStyle);
      console.log(`HtmlRenderer: Added style ${index + 1} to document head`);
    });
    
    // Set the body content (without the full document structure)
    containerRef.current.innerHTML = bodyContent;
    
    // Execute scripts
    scripts.forEach((script, index) => {
      console.log(`HtmlRenderer: Executing script ${index + 1}`);
      const newScript = document.createElement('script');
      
      // Copy attributes
      Array.from(script.attributes).forEach((attr) => {
        newScript.setAttribute(attr.name, attr.value);
      });
      
      // Copy content
      newScript.textContent = script.textContent;
      console.log(`HtmlRenderer: Script ${index + 1} content length:`, script.textContent?.length || 0);
      
      try {
        // Append to body to execute
        document.body.appendChild(newScript);
        console.log(`HtmlRenderer: Script ${index + 1} executed successfully`);
      } catch (error) {
        console.error(`HtmlRenderer: Error executing script ${index + 1}:`, error);
      }
    });

    // Cleanup function
    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      // Remove added styles
      styles.forEach((_, index) => {
        const styleElement = document.getElementById(`html-renderer-style-${index}`);
        if (styleElement) {
          styleElement.remove();
        }
      });
    };
  }, [content]);
  
  return (
    <div 
      ref={containerRef}
      className="w-full h-full html-content-reset"
      style={{ 
        minHeight: '100%',
        overflow: 'auto'
      }}
    />
  );
};