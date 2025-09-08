import React from 'react';
import { getStatusColor } from './StatusIcon';

interface StatusBadgeProps {
  status: string;
  children: React.ReactNode;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  status, 
  children, 
  size = 'sm' 
}) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1 text-sm';
  
  return (
    <span className={`${sizeClasses} rounded-full font-medium ${getStatusColor(status)}`}>
      {children}
    </span>
  );
};