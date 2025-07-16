import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ThumbsUp, ThumbsDown, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

export interface Source {
  id: string;
  title: string;
  url?: string;
  snippet: string;
  fullContent?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: Message;
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative', comment?: string) => void;
}

export function ChatMessage({ message, onFeedback }: ChatMessageProps) {
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackComment, setFeedbackComment] = useState('');
  const { toast } = useToast();

  const toggleSourceExpansion = (sourceId: string) => {
    const newExpanded = new Set(expandedSources);
    if (newExpanded.has(sourceId)) {
      newExpanded.delete(sourceId);
    } else {
      newExpanded.add(sourceId);
    }
    setExpandedSources(newExpanded);
  };

  const handleFeedback = (type: 'positive' | 'negative') => {
    if (type === 'negative') {
      setShowFeedbackForm(true);
    } else {
      onFeedback?.(message.id, type);
      setFeedbackGiven(type);
      toast({
        title: "Feedback enviado",
        description: "Obrigado pelo seu feedback!",
      });
    }
  };

  const submitNegativeFeedback = () => {
    onFeedback?.(message.id, 'negative', feedbackComment);
    setFeedbackGiven('negative');
    setShowFeedbackForm(false);
    setFeedbackComment('');
    toast({
      title: "Feedback enviado",
      description: "Obrigado pelo seu feedback detalhado!",
    });
  };

  const isUser = message.role === 'user';

  return (
    <div className={cn(
      "flex w-full gap-4 mb-6",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={cn(
        "max-w-[85%] space-y-3",
        isUser ? "order-2" : "order-1"
      )}>
        {/* Message Content */}
        <Card className={cn(
          "p-4 transition-all duration-300",
          isUser 
            ? "message-user shadow-chat" 
            : "message-assistant border-border/50"
        )}>
          <div className="space-y-2">
            <p className={cn(
              "text-sm leading-relaxed whitespace-pre-wrap",
              isUser ? "text-primary-foreground" : "text-foreground"
            )}>
              {message.content}
              {message.isStreaming && (
                <span className="inline-flex ml-1">
                  <div className="typing-dots">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                </span>
              )}
            </p>
            
            <div className="flex items-center justify-between">
              <span className={cn(
                "text-xs opacity-70",
                isUser ? "text-primary-foreground" : "text-muted-foreground"
              )}>
                {message.timestamp.toLocaleTimeString()}
              </span>
              
              {/* Feedback buttons for assistant messages */}
              {!isUser && !message.isStreaming && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleFeedback('positive')}
                    disabled={feedbackGiven !== null}
                    className={cn(
                      "h-8 w-8 p-0 hover:bg-green-500/20",
                      feedbackGiven === 'positive' && "bg-green-500/20 text-green-400"
                    )}
                  >
                    <ThumbsUp className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleFeedback('negative')}
                    disabled={feedbackGiven !== null}
                    className={cn(
                      "h-8 w-8 p-0 hover:bg-red-500/20",
                      feedbackGiven === 'negative' && "bg-red-500/20 text-red-400"
                    )}
                  >
                    <ThumbsDown className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Feedback Form */}
        {showFeedbackForm && (
          <Card className="p-4 border-yellow-500/20 bg-yellow-500/5">
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Como podemos melhorar esta resposta?
              </p>
              <Textarea
                placeholder="Descreva o que poderia ser melhorado..."
                value={feedbackComment}
                onChange={(e) => setFeedbackComment(e.target.value)}
                className="min-h-[80px] resize-none"
              />
              <div className="flex gap-2 justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowFeedbackForm(false);
                    setFeedbackComment('');
                  }}
                >
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  onClick={submitNegativeFeedback}
                  className="bg-primary hover:bg-primary/90"
                >
                  Enviar Feedback
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Sources Section */}
        {message.sources && message.sources.length > 0 && !message.isStreaming && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-foreground flex items-center gap-2">
              <span className="w-2 h-2 bg-source-highlight rounded-full"></span>
              Fontes consultadas ({message.sources.length})
            </h4>
            <div className="space-y-2">
              {message.sources.map((source) => (
                <Card 
                  key={source.id} 
                  className="p-3 border-border/30 hover:border-border/60 transition-colors bg-card/50"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h5 className="text-sm font-medium text-foreground line-clamp-1">
                        {source.title}
                      </h5>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {source.url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 hover:bg-primary/20"
                            onClick={() => window.open(source.url, '_blank')}
                          >
                            <ExternalLink className="h-3 w-3" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 hover:bg-primary/20"
                          onClick={() => toggleSourceExpansion(source.id)}
                        >
                          {expandedSources.has(source.id) ? (
                            <ChevronUp className="h-3 w-3" />
                          ) : (
                            <ChevronDown className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                    </div>
                    
                    <div className="text-xs text-muted-foreground">
                      {expandedSources.has(source.id) 
                        ? (source.fullContent || source.snippet)
                        : source.snippet.length > 150 
                          ? `${source.snippet.substring(0, 150)}...`
                          : source.snippet
                      }
                    </div>
                    
                    {source.url && (
                      <div className="text-xs text-primary/70 truncate">
                        {source.url}
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}