import { ChatHeader } from '@/components/chat/ChatHeader';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { ChatInput } from '@/components/chat/ChatInput';
import { useChat } from '@/hooks/useChat';

const Index = () => {
  const { messages, isLoading, sendMessage, clearChat, handleFeedback } = useChat();

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      {/* <ChatHeader 
        onNewChat={clearChat}
        messageCount={messages.length}
        isLoading={isLoading}
      /> */}

      {/* Main chat area */}
      <ChatContainer 
        messages={messages}
        isLoading={isLoading}
        onFeedback={handleFeedback}
      />

      {/* Input area */}
      <ChatInput 
        onSendMessage={sendMessage}
        isLoading={isLoading}
        placeholder="Digite sua pergunta sobre qualquer tópico..."
      />
    </div>
  );
};

export default Index;
