import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { MessageCircle, Send, User } from 'lucide-react';

interface HumanInteractionModalProps {
  question: string;
  query: string;
  onSubmit: (response: string) => void;
  isVisible: boolean;
}

export const HumanInteractionModal: React.FC<HumanInteractionModalProps> = ({
  question,
  query,
  onSubmit,
  isVisible
}) => {
  const [response, setResponse] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!response.trim()) return;
    
    setIsSubmitting(true);
    try {
      await onSubmit(response.trim());
      setResponse('');
    } catch (error) {
      console.error('Failed to submit response:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Parse numbered options from question
  const parseOptions = (questionText: string): string[] => {
    const lines = questionText.split('\n');
    return lines
      .filter(line => /^\d+\.\s/.test(line.trim()))
      .map(line => line.replace(/^\d+\.\s/, '').trim());
  };

  const options = parseOptions(question);
  const questionIntro = question.split('\n')[0];

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-2xl bg-gray-900 border-gray-700 max-h-[90vh] overflow-auto">
        <CardHeader className="border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <MessageCircle className="w-5 h-5 text-yellow-400" />
            </div>
            <div className="flex-grow">
              <CardTitle className="text-lg font-semibold text-white">
                Input Needed
              </CardTitle>
              <p className="text-sm text-gray-400 mt-1">
                The system needs clarification to continue the analysis
              </p>
            </div>
            <Badge variant="secondary" className="bg-yellow-500 text-black">
              WAITING
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent className="pt-6">
          {/* Original Query Context */}
          <div className="mb-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-300">Your Query:</span>
            </div>
            <p className="text-gray-200 text-sm italic">{query}</p>
          </div>

          {/* Question */}
          <div className="mb-4">
            <h3 className="text-white font-medium mb-3">
              {questionIntro}
            </h3>
            
            {options.length > 0 && (
              <div className="mb-4">
                <p className="text-gray-300 text-sm mb-3">
                  Choose from these examples or provide your own:
                </p>
                <div className="space-y-2">
                  {options.map((option, index) => (
                    <button
                      key={index}
                      onClick={() => setResponse(option)}
                      className="w-full text-left p-3 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors text-gray-200 text-sm"
                    >
                      <span className="font-medium text-blue-400">{index + 1}.</span> {option}
                    </button>
                  ))}
                </div>
                
                <div className="mt-4 text-center">
                  <span className="text-gray-400 text-sm">or</span>
                </div>
              </div>
            )}
          </div>

          {/* Response Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Your Response:
            </label>
            <Textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type your custom response or select an option above..."
              className="bg-gray-800 border-gray-600 text-white placeholder-gray-400 min-h-[100px]"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              Press Ctrl+Enter to submit
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              onClick={handleSubmit}
              disabled={!response.trim() || isSubmitting}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit Response
                </>
              )}
            </Button>
          </div>
          
          {response.trim() && (
            <div className="mt-3 p-3 bg-blue-900/20 border border-blue-500/30 rounded-md">
              <div className="text-blue-300 text-sm">
                <span className="font-medium">Your response:</span> "{response.trim()}"
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};