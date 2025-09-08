import { CheckCircle2, Clock, AlertCircle, Play, Pause } from 'lucide-react';

export const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-400" />;
    case 'in_progress':
      return <Play className="h-4 w-4 text-blue-400" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-400" />;
    case 'skipped':
      return <Pause className="h-4 w-4 text-gray-400" />;
    default:
      return <AlertCircle className="h-4 w-4 text-red-400" />;
  }
};

export const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'text-green-400 bg-green-900/20';
    case 'in_progress':
      return 'text-blue-400 bg-blue-900/20';
    case 'pending':
      return 'text-yellow-400 bg-yellow-900/20';
    case 'skipped':
      return 'text-gray-400 bg-gray-900/20';
    default:
      return 'text-red-400 bg-red-900/20';
  }
};