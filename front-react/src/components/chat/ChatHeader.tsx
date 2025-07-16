import { Button } from '@/components/ui/button';
import { MessageSquarePlus, Settings, HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
  onNewChat: () => void;
  messageCount: number;
  isLoading?: boolean;
}

export function ChatHeader({ onNewChat, messageCount, isLoading }: ChatHeaderProps) {
  return (
    <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="container max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo and title */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center shadow-glow">
            <span className="text-primary-foreground font-bold text-sm">R</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold gradient-text">
              RAG Assistant
            </h1>
            <p className="text-xs text-muted-foreground">
              Powered by Retrieval Augmented Generation
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Message counter */}
          {messageCount > 0 && (
            <div className="text-xs text-muted-foreground px-2 py-1 bg-muted/50 rounded-md">
              {messageCount} mensagens
            </div>
          )}
          
          {/* New chat button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onNewChat}
            disabled={isLoading}
            className={cn(
              "h-9 px-3 gap-2 hover:bg-primary/10 hover:text-primary",
              messageCount === 0 && "opacity-50 cursor-not-allowed"
            )}
          >
            <MessageSquarePlus className="h-4 w-4" />
            <span className="hidden sm:inline">Nova Conversa</span>
          </Button>

          {/* Settings button */}
          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-9 p-0 hover:bg-primary/10 hover:text-primary"
          >
            <Settings className="h-4 w-4" />
          </Button>

          {/* Help button */}
          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-9 p-0 hover:bg-primary/10 hover:text-primary"
          >
            <HelpCircle className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}