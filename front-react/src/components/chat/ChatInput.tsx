import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Mic, MicOff, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

// Extend the Window interface for speech recognition
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function ChatInput({ 
  onSendMessage, 
  isLoading = false, 
  placeholder = "Digite sua pergunta aqui..." 
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'pt-BR';

      recognitionInstance.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setMessage(prev => prev + (prev ? ' ' : '') + transcript);
        setIsRecording(false);
      };

      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
        toast({
          title: "Erro no reconhecimento de voz",
          description: "Não foi possível capturar o áudio. Tente novamente.",
          variant: "destructive",
        });
      };

      recognitionInstance.onend = () => {
        setIsRecording(false);
      };

      setRecognition(recognitionInstance);
    }
  }, [toast]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleRecording = () => {
    if (!recognition) {
      toast({
        title: "Recurso não disponível",
        description: "Reconhecimento de voz não é suportado neste navegador.",
        variant: "destructive",
      });
      return;
    }

    if (isRecording) {
      recognition.stop();
      setIsRecording(false);
    } else {
      recognition.start();
      setIsRecording(true);
    }
  };

  const canSend = message.trim().length > 0 && !isLoading;

  return (
    <div className="border-t border-border/50 bg-background/80 backdrop-blur-sm">
      <div className="container max-w-4xl mx-auto p-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isLoading}
              className={cn(
                "min-h-[60px] max-h-[200px] resize-none pr-20 rounded-xl border-border/50",
                "focus:ring-2 focus:ring-primary/20 focus:border-primary/50",
                "transition-all duration-200",
                isLoading && "opacity-50 cursor-not-allowed"
              )}
            />
            
            {/* Voice input button */}
            <div className="absolute right-2 bottom-2 flex items-center gap-2">
              {recognition && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={toggleRecording}
                  disabled={isLoading}
                  className={cn(
                    "h-8 w-8 p-0 rounded-full transition-colors",
                    isRecording 
                      ? "bg-red-500 hover:bg-red-600 text-white animate-pulse" 
                      : "hover:bg-primary/20 text-muted-foreground hover:text-primary"
                  )}
                >
                  {isRecording ? (
                    <MicOff className="h-4 w-4" />
                  ) : (
                    <Mic className="h-4 w-4" />
                  )}
                </Button>
              )}
              
              {/* Send button */}
              <Button
                type="submit"
                size="sm"
                disabled={!canSend}
                className={cn(
                  "h-8 w-8 p-0 rounded-full transition-all duration-200",
                  canSend 
                    ? "bg-primary hover:bg-primary/90 text-primary-foreground shadow-glow" 
                    : "bg-muted text-muted-foreground cursor-not-allowed"
                )}
              >
                {isLoading ? (
                  <Square className="h-4 w-4" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
          
          {/* Recording indicator */}
          {isRecording && (
            <div className="flex items-center gap-2 text-sm text-red-400 animate-pulse">
              <div className="w-2 h-2 bg-red-400 rounded-full animate-ping"></div>
              Gravando... Fale agora
            </div>
          )}
          
          {/* Character count */}
          <div className="flex justify-between items-center text-xs text-muted-foreground">
            <span>
              Pressione Enter para enviar, Shift+Enter para nova linha
            </span>
            <span className={cn(
              message.length > 1000 && "text-yellow-500",
              message.length > 2000 && "text-red-500"
            )}>
              {message.length}/2000
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
