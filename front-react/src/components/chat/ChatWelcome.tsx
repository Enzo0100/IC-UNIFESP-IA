import { Card } from '@/components/ui/card';
import { Zap } from 'lucide-react';
import { Map, Building, Trees, Search } from 'lucide-react';

export function ChatWelcome() {
  const features = [
    {
      icon: Map,
      title: "Análise Territorial",
      description: "Entenda as dinâmicas e transformações do espaço urbano e rural."
    },
    {
      icon: Search,
      title: "Base de Conhecimento",
      description: "Acesse informações e referências sobre legislação e gestão territorial."
    },
    {
      icon: Building,
      title: "Desafios da Urbanização",
      description: "Explore os problemas decorrentes da expansão urbana desordenada."
    },
    {
      icon: Trees,
      title: "Novos Usos do Rural",
      description: "Descubra as novas formas de ocupação e uso das áreas rurais."
    }
  ];

  const exampleQuestions = [
    "O que é o conceito de urbano-rural?",
    "Quais são os principais desafios da gestão territorial no Brasil?",
    "Como a legislação aborda a expansão urbana em áreas rurais?",
    "Quais as consequências da urbanização não planejada?",
  ];

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Hero section */}
      <div className="text-center space-y-4">
        <div className="w-16 h-16 bg-gradient-primary rounded-2xl flex items-center justify-center mx-auto shadow-glow">
          <Map className="h-8 w-8 text-primary-foreground" />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-4xl font-bold gradient-text">
            Urbano-Rural e Desafios à Gestão Territorial
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Para lidar com os desafios da gestão territorial, é crucial entender o conceito de urbano-rural e as transformações que o território sofre.
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
