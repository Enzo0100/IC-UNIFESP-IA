import { useState, useCallback } from 'react';
import { Message, Source } from '@/components/chat/ChatMessage';
import { useToast } from '@/hooks/use-toast';

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
}

export function useChat() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    sessionId: null,
    isLoading: false
  });
  
  const { toast } = useToast();

  const sendMessage = useCallback(async (
    content: string
  ) => {
    if (!content.trim() || chatState.isLoading) return;

    const messageId = Date.now().toString();
    const sessionId = chatState.sessionId || `session_${Date.now()}`;

    // Add user message
    const userMessage: Message = {
      id: `user_${messageId}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      sessionId,
      isLoading: true
    }));

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: content.trim() }),
      });

      if (!response.ok) {
        throw new Error('A resposta da rede não foi bem-sucedida');
      }

      const data = await response.json();

      const sources: Source[] = data.source_documents.map((doc: any, index: number) => ({
        id: `source_${messageId}_${index}`,
        title: doc.metadata.source || `Fonte ${index + 1}`,
        snippet: doc.content,
        fullContent: doc.content,
        url: doc.metadata.url || undefined,
      }));

      const assistantMessage: Message = {
        id: `assistant_${messageId}`,
        role: 'assistant',
        content: data.answer,
        sources,
        timestamp: new Date()
      };

      setChatState(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        isLoading: false
      }));

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: `error_${messageId}`,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.',
        timestamp: new Date()
      };

      setChatState(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage],
        isLoading: false
      }));

      toast({
        title: "Erro de comunicação",
        description: "Não foi possível processar sua mensagem. Tente novamente.",
        variant: "destructive",
      });
    }
  }, [chatState.isLoading, chatState.sessionId, toast]);

  const clearChat = useCallback(() => {
    setChatState({
      messages: [],
      sessionId: null,
      isLoading: false
    });
  }, []);

  const handleFeedback = useCallback((
    messageId: string, 
    feedback: 'positive' | 'negative', 
    comment?: string
  ) => {
    console.log('Feedback received:', { messageId, feedback, comment });
    
    // In a real application, this would send feedback to the backend
    toast({
      title: "Feedback registrado",
      description: `Obrigado pelo seu feedback ${feedback === 'positive' ? 'positivo' : 'negativo'}!`,
    });
  }, [toast]);

  return {
    messages: chatState.messages,
    isLoading: chatState.isLoading,
    sessionId: chatState.sessionId,
    sendMessage,
    clearChat,
    handleFeedback
  };
}
