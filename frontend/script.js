document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    const API_URL = '/ask';

    const addMessage = (text, sender) => {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        
        const p = document.createElement('p');
        p.textContent = text;
        messageElement.appendChild(p);
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageElement;
    };

    const handleSend = async () => {
        const query = userInput.value.trim();
        if (!query) return;

        addMessage(query, 'user');
        userInput.value = '';
        
        const loadingMessage = addMessage('Digitando...', 'bot');
        loadingMessage.classList.add('loading');

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            loadingMessage.remove();
            addMessage(data.answer, 'bot');

        } catch (error) {
            console.error('Erro ao buscar resposta:', error);
            loadingMessage.remove();
            addMessage('Desculpe, ocorreu um erro ao conectar com o servidor.', 'bot');
        }
    };

    sendBtn.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    });
});
