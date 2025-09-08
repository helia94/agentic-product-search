import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { TaskStep } from '@/utils/dataTransformer';
import { getStatusIcon, StatusBadge } from '../ui';

interface StepCardProps {
  step: TaskStep;
  stepKey: string;
  isExpanded: boolean;
  onToggleExpansion: () => void;
}

export const StepCard: React.FC<StepCardProps> = ({
  step,
  isExpanded,
  onToggleExpansion,
}) => {
  const hasDetails = step.details && step.details.length > 0;
  const [showAllSources, setShowAllSources] = React.useState(false);

  const getStepTypeLabel = (type: string) => {
    switch (type) {
      case 'query_generation': return 'Query Generation';
      case 'web_research': return 'Web Research';
      case 'reflection': return 'Reflection Analysis';
      case 'content_enhancement': return 'Content Enhancement';
      case 'evaluation': return 'Quality Evaluation';
      case 'completion': return 'Task Completion';
      default: return type;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending': return 'Pending';
      case 'in_progress': return 'Running';
      case 'completed': return 'Done';
      case 'skipped': return 'Skipped';
      default: return status;
    }
  };

  return (
    <div className="bg-gray-200/50 rounded-lg border border-neutral-600">
      {/* Step Header */}
      <div
        className={`p-3 ${hasDetails ? 'cursor-pointer hover:bg-neutral-600/50' : ''} transition-colors`}
        onClick={hasDetails ? onToggleExpansion : undefined}
      >
        <div className="flex items-center gap-3">
          {hasDetails && (
            isExpanded ? (
              <ChevronDown className="h-3 w-3 text-gray-600" />
            ) : (
              <ChevronRight className="h-3 w-3 text-gray-600" />
            )
          )}
          {getStatusIcon(step.status)}
          <div className="flex-1">
            <div className="font-medium text-white text-sm">{step.title}</div>
            <div className="text-xs text-gray-600 mt-1">
              {getStepTypeLabel(step.type)}
            </div>
          </div>
          <StatusBadge status={step.status}>
            {getStatusLabel(step.status)}
          </StatusBadge>
        </div>
      </div>

      {/* Step Details */}
      {isExpanded && step.details && (
        <div className="border-t border-neutral-600 p-3 space-y-2">
          {step.details.map((detail, detailIndex) => (
            <StepDetail
              key={detailIndex}
              detail={detail}
              showAllSources={showAllSources}
              onToggleAllSources={() => setShowAllSources(!showAllSources)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface StepDetailProps {
  detail: any;
  showAllSources: boolean;
  onToggleAllSources: () => void;
}

const StepDetail: React.FC<StepDetailProps> = ({
  detail,
  showAllSources,
  onToggleAllSources,
}) => {
  const getDetailTypeLabel = (type: string) => {
    switch (type) {
      case 'search_queries': return 'Search Queries';
      case 'sources': return 'Data Sources';
      case 'analysis': return 'Analysis Results';
      case 'decision': return 'Decision Info';
      default: return type;
    }
  };

  return (
    <div className="bg-gray-100/50 rounded p-3">
      <div className="text-xs font-medium text-neutral-300 mb-2 uppercase tracking-wide">
        {getDetailTypeLabel(detail.type)}
      </div>
      <div className="text-sm text-white mb-2">{detail.content}</div>
      
      {detail.metadata && (
        <div className="space-y-2">
          {detail.metadata.count !== undefined && (
            <div className="text-xs text-gray-600">
              Count: {detail.metadata.count}
            </div>
          )}
          
          {detail.metadata.sources && (
            <SourcesList
              sources={detail.metadata.sources}
              showAll={showAllSources}
              onToggleShowAll={onToggleAllSources}
            />
          )}
          
          {detail.metadata.follow_up_queries && (
            <FollowUpQueries queries={detail.metadata.follow_up_queries} />
          )}
        </div>
      )}
    </div>
  );
};

interface SourcesListProps {
  sources: any[];
  showAll: boolean;
  onToggleShowAll: () => void;
}

const SourcesList: React.FC<SourcesListProps> = ({ sources, showAll, onToggleShowAll }) => {
  const displayedSources = showAll ? sources : sources.slice(0, 3);

  return (
    <div className="space-y-1">
      <div className="text-xs font-medium text-neutral-300">Source Details:</div>
      {displayedSources.map((source, sourceIndex) => (
        <div key={sourceIndex} className="text-xs text-gray-600 bg-gray-100 rounded p-2">
          <div className="font-medium text-neutral-300">{source.title}</div>
          <div className="text-xs text-blue-400 mt-1">
            <span className="bg-blue-900/30 px-1 py-0.5 rounded text-xs mr-2">{source.label}</span>
          </div>
          {source.url && (
            <div className="text-blue-400 break-all mt-1 text-xs">{source.url}</div>
          )}
          {source.snippet && (
            <div className="mt-1 text-gray-600 text-xs">{source.snippet}</div>
          )}
        </div>
      ))}
      
      {sources.length > 3 && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleShowAll();
          }}
          className="text-xs text-blue-400 hover:text-blue-300 transition-colors border border-blue-400/30 hover:border-blue-300/50 rounded px-2 py-1 mt-2"
        >
          {showAll 
            ? `Show less sources` 
            : `Show all ${sources.length} sources`
          }
        </button>
      )}
    </div>
  );
};

interface FollowUpQueriesProps {
  queries: string[];
}

const FollowUpQueries: React.FC<FollowUpQueriesProps> = ({ queries }) => (
  <div className="space-y-1">
    <div className="text-xs font-medium text-neutral-300">Follow-up Queries:</div>
    <div className="text-xs text-gray-600">
      {queries.join(', ')}
    </div>
  </div>
);