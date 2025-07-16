import { useState, useCallback } from 'react';
import { Message, Source } from '@/components/chat/ChatMessage';
import { useToast } from '@/hooks/use-toast';

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
}

interface SendMessageOptions {
  enableStreaming?: boolean;
}

// Mock API responses for demonstration
const mockSources: Source[] = [
  {
    id: "doc_ai_education_001",
    title: "O Futuro da Educação com IA - Relatório UNESCO",
    url: "https://example.org/unesco-ai-education-report.pdf",
    snippet: "A inteligência artificial tem o potencial de revolucionar a educação através da personalização do aprendizado, permitindo que cada estudante progrida em seu próprio ritmo e estilo de aprendizagem...",
    fullContent: "A inteligência artificial tem o potencial de revolucionar a educação através da personalização do aprendizado, permitindo que cada estudante progrida em seu próprio ritmo e estilo de aprendizagem. Sistemas de IA podem analisar padrões de aprendizado individuais, identificar lacunas de conhecimento e sugerir recursos educacionais específicos para cada aluno."
  },
  {
    id: "doc_ai_automation_002",
    title: "Automação Inteligente na Gestão Educacional",
    url: "https://example.com/automation-education-management.html",
    snippet: "Ferramentas de IA podem automatizar tarefas administrativas como correção de provas, agendamento de aulas e geração de relatórios de progresso...",
    fullContent: "Ferramentas de IA podem automatizar tarefas administrativas como correção de provas, agendamento de aulas e geração de relatórios de progresso, liberando tempo valioso para que educadores se concentrem no que realmente importa: o ensino e a mentoria dos alunos."
  }
];

const generateMockResponse = (query: string): { response: string; sources: Source[] } => {
  // Simple keyword-based response generation for demo
  const lowerQuery = query.toLowerCase();
  
  if (lowerQuery.includes('inteligência artificial') || lowerQuery.includes('ia') || lowerQuery.includes('educação')) {
    return {
      response: `A inteligência artificial está transformando profundamente o setor educacional através de várias frentes inovadoras. 

**Personalização do Aprendizado**: Sistemas de IA analisam o comportamento e desempenho individual de cada estudante, criando trilhas de aprendizagem customizadas que se adaptam ao ritmo e estilo de cada um.

**Automação Inteligente**: Tarefas administrativas como correção de provas, geração de relatórios e agendamento são automatizadas, permitindo que educadores dediquem mais tempo ao ensino direto.

**Análise Preditiva**: A IA pode identificar estudantes em risco de evasão ou com dificuldades específicas, permitindo intervenções precoces e direcionadas.

**Assistentes Virtuais**: Chatbots educacionais disponíveis 24/7 para tirar dúvidas e fornecer suporte aos estudantes fora do horário de aula.

Essa transformação não substitui o papel fundamental dos educadores, mas sim amplifica suas capacidades e cria um ambiente de aprendizagem mais eficiente e inclusivo.`,
      sources: mockSources
    };
  }
  
  // Default response for other queries
  return {
    response: `Obrigado por sua pergunta sobre "${query}". Esta é uma resposta de demonstração do sistema RAG. 

O sistema está processando sua consulta e buscando informações relevantes em nossa base de conhecimento para fornecer uma resposta precisa e fundamentada.

Em um sistema real, esta resposta seria gerada com base em documentos específicos recuperados da base de dados de conhecimento, garantindo que todas as informações fornecidas sejam verificáveis e confiáveis.`,
    sources: [
      {
        id: "demo_doc_001",
        title: "Documentação do Sistema RAG",
        snippet: "Este é um exemplo de como as fontes são exibidas no sistema...",
        fullContent: "Este é um exemplo completo de como as fontes são exibidas no sistema RAG, mostrando a transparência e rastreabilidade das informações fornecidas."
      }
    ]
  };
};

export function useChat() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    sessionId: null,
    isLoading: false
  });
  
  const { toast } = useToast();

  const sendMessage = useCallback(async (
    content: string, 
    options: SendMessageOptions = {}
  ) => {
    if (!content.trim() || chatState.isLoading) return;

    const { enableStreaming = true } = options;
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
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

      const { response, sources } = generateMockResponse(content);

      if (enableStreaming) {
        // Simulate streaming response
        const assistantMessage: Message = {
          id: `assistant_${messageId}`,
          role: 'assistant',
          content: '',
          sources: [],
          timestamp: new Date(),
          isStreaming: true
        };

        // Add empty assistant message
        setChatState(prev => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isLoading: false
        }));

        // Stream the response word by word
        const words = response.split(' ');
        for (let i = 0; i < words.length; i++) {
          await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100));
          
          setChatState(prev => ({
            ...prev,
            messages: prev.messages.map(msg => 
              msg.id === assistantMessage.id 
                ? { 
                    ...msg, 
                    content: words.slice(0, i + 1).join(' ') + (i < words.length - 1 ? '...' : ''),
                    isStreaming: i < words.length - 1
                  }
                : msg
            )
          }));
        }

        // Add sources after streaming is complete
        setChatState(prev => ({
          ...prev,
          messages: prev.messages.map(msg => 
            msg.id === assistantMessage.id 
              ? { ...msg, sources, isStreaming: false }
              : msg
          )
        }));

      } else {
        // Add complete assistant message
        const assistantMessage: Message = {
          id: `assistant_${messageId}`,
          role: 'assistant',
          content: response,
          sources,
          timestamp: new Date()
        };

        setChatState(prev => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isLoading: false
        }));
      }

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