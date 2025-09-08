import React from 'react';

interface LoadingSpinnerProps {
  text?: string;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  text = "Running...", 
  className = "" 
}) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="animate-spin h-3 w-3 border border-blue-400 border-t-transparent rounded-full"></div>
      <span className="text-blue-400">{text}</span>
    </div>
  );
};