import { useEffect, useRef } from 'react';
import { ChatMessage, Message } from './ChatMessage';
import { ChatWelcome } from './ChatWelcome';
import { cn } from '@/lib/utils';

interface ChatContainerProps {
  messages: Message[];
  isLoading?: boolean;
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative', comment?: string) => void;
}

export function ChatContainer({ messages, isLoading, onFeedback }: ChatContainerProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const hasMessages = messages.length > 0;

  return (
    <div className={cn(
      "flex-1 overflow-hidden",
      hasMessages ? "flex flex-col" : "flex items-center justify-center"
    )}>
      {hasMessages ? (
        <>
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="container max-w-4xl mx-auto px-4 py-6 space-y-6">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onFeedback={onFeedback}
                />
              ))}
              
              {/* Loading indicator */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[85%]">
                    <div className="message-assistant p-4 rounded-xl border border-border/50">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <div className="typing-dots">
                          <div className="typing-dot"></div>
                          <div className="typing-dot"></div>
                          <div className="typing-dot"></div>
                        </div>
                        <span className="text-sm">Processando sua pergunta...</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </>
      ) : (
        /* Welcome screen */
        <ChatWelcome />
      )}
    </div>
  );
}