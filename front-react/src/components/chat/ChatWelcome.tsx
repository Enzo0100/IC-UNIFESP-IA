import { Card } from '@/components/ui/card';
import { MessageSquare, Zap, Shield, Search } from 'lucide-react';

export function ChatWelcome() {
  const features = [
    {
      icon: MessageSquare,
      title: "Conversas Inteligentes",
      description: "Faça perguntas complexas e receba respostas detalhadas baseadas em fontes confiáveis."
    },
    {
      icon: Search,
      title: "Busca Avançada",
      description: "Acesso a uma vasta base de conhecimento com recuperação precisa de informações."
    },
    {
      icon: Zap,
      title: "Respostas Rápidas",
      description: "Streaming em tempo real para respostas instantâneas e experiência fluida."
    },
    {
      icon: Shield,
      title: "Fontes Transparentes",
      description: "Todas as respostas incluem referências às fontes utilizadas para total transparência."
    }
  ];

  const exampleQuestions = [
    "Como a inteligência artificial está transformando a educação?",
    "Quais são as melhores práticas para desenvolvimento sustentável?",
    "Explique os conceitos básicos de machine learning",
    "Como funciona a tecnologia blockchain?",
  ];

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Hero section */}
      <div className="text-center space-y-4">
        <div className="w-16 h-16 bg-gradient-primary rounded-2xl flex items-center justify-center mx-auto shadow-glow">
          <MessageSquare className="h-8 w-8 text-primary-foreground" />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-4xl font-bold gradient-text">
            Bem-vindo ao RAG Assistant
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Seu assistente inteligente com tecnologia de Geração Aumentada por Recuperação. 
            Faça perguntas e receba respostas precisas com fontes verificadas.
          </p>
        </div>
      </div>

      {/* Features grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {features.map((feature, index) => (
          <Card 
            key={index}
            className="p-6 border-border/30 hover:border-border/60 transition-all duration-300 hover:shadow-lg bg-card/50"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <feature.icon className="h-5 w-5 text-primary" />
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold text-foreground">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Example questions */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-center text-foreground">
          Experimente estas perguntas
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {exampleQuestions.map((question, index) => (
            <Card 
              key={index}
              className="p-4 border-border/30 hover:border-primary/30 transition-all duration-300 cursor-pointer hover:shadow-md bg-card/30 hover:bg-card/50"
            >
              <p className="text-sm text-foreground leading-relaxed">
                "{question}"
              </p>
            </Card>
          ))}
        </div>
      </div>

      {/* Getting started tip */}
      <Card className="p-6 border-primary/20 bg-primary/5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-foreground">Dica para começar</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Digite sua pergunta na caixa de texto abaixo. Você pode usar o microfone para entrada de voz 
              ou digitar diretamente. O assistente irá processar sua consulta e fornecer uma resposta 
              detalhada com todas as fontes relevantes.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}