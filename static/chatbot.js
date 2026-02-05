// Chatbot Configuration
const CHATBOT_CONFIG = {
    provider: 'groq',
    groqApiKey: null, // Will be loaded from backend
    groqModel: 'llama-3.3-70b-versatile',
};

// Load API key from backend
async function loadChatbotConfig() {
    try {
        const response = await fetch('/api/chatbot-config');
        const config = await response.json();
        CHATBOT_CONFIG.groqApiKey = config.groqApiKey;
    } catch (error) {
        console.error('Failed to load chatbot config:', error);
    }
}

// Context about Analytics Assistant
const CONTEXT_PROMPT = `You are Nova, an intelligent and friendly AI assistant for the Conversational Data Analyst application. You help users understand how to use this powerful analytics platform.

COMMUNICATION STYLE:
- Confident and conversational (not robotic)
- Adapt to user's tone - be professional with serious queries, friendly with casual chat
- Give specific, technical details when asked
- Be engaging and personable while staying informative

ABOUT THIS PROJECT - CONVERSATIONAL DATA ANALYST:

Creator & Contact:
- **Created by**: Nadeem Akhtar
- **Email**: nadeemnns2000@gmail.com
- **LinkedIn**: linkedin.com/in/nadeem-akhtar-
- **Portfolio**: nsde.netlify.app
- **GitHub**: github.com/NadeemAkhtar1947
- **Repository**: github.com/NadeemAkhtar1947/conversational-data-analyst

Project Overview:
- Multi-agent AI system for natural language data analysis
- Supports multiple datasets: Superstore Sales, IPL Cricket, Netflix Titles, World Population, and custom CSV uploads
- Generates SQL queries from natural language questions
- Provides AI-powered insights and visualizations

Key Features:
1. **Multiple Datasets**: Switch between pre-loaded datasets or upload your own CSV
2. **Natural Language Queries**: Ask questions in plain English - no SQL knowledge required
3. **Multi-Agent Architecture**:
   - Context Rewriter Agent: Understands conversation context
   - SQL Generator Agent: Converts questions to SQL using Groq API (Llama 3.1 70B)
   - Analysis Agent: Provides insights and summaries
   - Visualization Agent: Suggests appropriate charts
4. **Smart SQL Generation**: Uses sentence-transformers for semantic understanding
5. **Real-time Analysis**: Fast query execution with Neon PostgreSQL database
6. **CSV Upload Support**: Analyze your own data with DuckDB in-memory processing

Technologies Used:
- **Backend**: FastAPI (Python)
- **Database**: Neon PostgreSQL (serverless), DuckDB (CSV processing)
- **AI/ML**: Groq API (Llama 3.1 70B), sentence-transformers, spaCy
- **Frontend**: Tailwind CSS, Vanilla JavaScript
- **Agents**: Multi-agent orchestration with context management

Available Datasets:
1. **Superstore Sales** (9,994 rows): Retail sales with orders, customers, products
2. **E-Commerce Sales** (9,994 rows): Online sales with segments and regions
3. **IPL Cricket** (1,169 rows): Indian Premier League match statistics
4. **Netflix Titles** (8,807 rows): Movies and TV shows catalog
5. **World Population** (234 rows): Population data by country (1970-2022)

How to Use:
1. Select a dataset from the sidebar (or upload your own CSV)
2. Click suggested questions or type your own
3. Get instant SQL query, results, insights, and visualizations
4. Continue the conversation - the AI remembers context

For greetings, respond warmly and offer help with the platform.
For technical questions, provide detailed explanations about the architecture, agents, or datasets.
For usage questions, guide users on how to analyze data effectively.
For creator/contact questions, provide Nadeem Akhtar's information and links.

IMPORTANT RULES:
- Be specific when asked technical questions
- Match the user's energy (casual = friendly, formal = professional)
- Never say "I don't know" - provide what information you have
- Keep responses concise but informative
- When asked about the creator, always mention Nadeem Akhtar with his contact details
`;

class ResumeChatbot {
    constructor() {
        this.messages = [];
        this.isOpen = false;
        this.isTyping = false;
        this.hasInteracted = false;
        this.autoCloseTimer = null;
        this.conversationHistory = []; // Track conversation for context
        this.init();
    }

    init() {
        this.createChatUI();
        this.attachEventListeners();
    }

    createChatUI() {
        const chatContainer = document.createElement('div');
        chatContainer.className = 'chatbot-container';
        chatContainer.innerHTML = `
            <button class="chatbot-toggle" id="chatbot-toggle">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </button>
            <div class="chatbot-window" id="chatbot-window">
                <div class="chatbot-header">
                    <div class="chatbot-header-content">
                        <h3>Nova - AI Assistant</h3>
                        <p>Ask about this analytics platform</p>
                    </div>
                    <button class="chatbot-close" id="chatbot-close">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="chatbot-messages" id="chatbot-messages">
                    <div class="message bot-message">
                        <div class="message-content">
                            Hey! 👋 I'm <strong>Nova</strong>, your AI assistant for this Analytics Platform. I can help you with:
                            <br>• How to use the platform & analyze data
                            <br>• Understanding the multi-agent AI system
                            <br>• Available datasets & their schemas
                            <br>• Tech stack & architecture details
                            <br><br>Got questions? I'm here to help! 😊
                        </div>
                    </div>
                </div>
                <div class="chatbot-input-container">
                    <input 
                        type="text" 
                        id="chatbot-input" 
                        placeholder="Ask about features, datasets, or how to use..." 
                        autocomplete="off"
                    />
                    <button class="chatbot-send" id="chatbot-send">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(chatContainer);
    }

    attachEventListeners() {
        const toggle = document.getElementById('chatbot-toggle');
        const close = document.getElementById('chatbot-close');
        const send = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');

        toggle.addEventListener('click', () => this.toggleChat());
        close.addEventListener('click', () => this.toggleChat());
        send.addEventListener('click', () => this.sendMessage());
        
        input.addEventListener('input', () => {
            if (!this.hasInteracted) {
                this.hasInteracted = true;
                if (this.autoCloseTimer) {
                    clearTimeout(this.autoCloseTimer);
                    this.autoCloseTimer = null;
                }
            }
        });
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        const window = document.getElementById('chatbot-window');
        const toggle = document.getElementById('chatbot-toggle');
        
        if (this.isOpen) {
            window.classList.add('open');
            toggle.style.display = 'none';
            
            if (this.autoCloseTimer) {
                clearTimeout(this.autoCloseTimer);
                this.autoCloseTimer = null;
            }
            
            if (!this.hasInteracted) {
                this.autoCloseTimer = setTimeout(() => {
                    if (!this.hasInteracted && this.isOpen) {
                        this.toggleChat();
                    }
                }, 20000); // 20 seconds
            }
        } else {
            window.classList.remove('open');
            toggle.style.display = 'flex';
            
            if (this.autoCloseTimer) {
                clearTimeout(this.autoCloseTimer);
                this.autoCloseTimer = null;
            }
        }
    }

    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        
        if (!message || this.isTyping) return;

        this.addMessage(message, 'user');
        input.value = '';

        this.showTyping();

        try {
            const response = await this.getAIResponse(message);
            this.hideTyping();
            await this.addMessageWithTypingEffect(response, 'bot');
        } catch (error) {
            this.hideTyping();
            await this.addMessageWithTypingEffect(
                `Sorry, I encountered an error. Please try again or check your connection.`,
                'bot'
            );
            console.error('Chatbot error:', error);
        }
    }

    async getAIResponse(userMessage) {
        const messageLower = userMessage.toLowerCase().trim();
        
        // Handle greetings
        const greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening'];
        if (greetings.some(greeting => messageLower === greeting || messageLower.startsWith(greeting + ' '))) {
            return "Hey there! 👋 I'm Nova, your AI assistant for this Analytics Platform. Ask me anything about how it works, the datasets, or the AI agents!";
        }
        
        // Handle "how are you"
        if (messageLower.includes('how are you') || messageLower.includes('how are u')) {
            return "I'm doing great, thanks for asking! 😊 Ready to help you understand this analytics platform. What would you like to know?";
        }
        
        // Handle compliments
        const compliments = ['smart', 'cool', 'awesome', 'amazing', 'great', 'nice', 'good job', 'impressive'];
        if (compliments.some(word => messageLower.includes(word)) && messageLower.split(' ').length < 8) {
            return "Thanks! I appreciate that! 😊 This platform is pretty impressive too - built with multi-agent AI for smart data analysis. Want to know more?";
        }
        
        return await this.getGroqResponse(userMessage);
    }

    async getGroqResponse(userMessage) {
        const apiKey = CHATBOT_CONFIG.groqApiKey;
        const url = 'https://api.groq.com/openai/v1/chat/completions';
        
        // Build conversation context from recent messages
        const conversationContext = this.conversationHistory.length > 0 
            ? `\n\nRecent conversation topics: ${this.conversationHistory.join(', ')}` 
            : '';
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: CHATBOT_CONFIG.groqModel,
                messages: [
                    { role: 'system', content: CONTEXT_PROMPT + conversationContext },
                    { role: 'user', content: userMessage }
                ],
                temperature: 0.8, // Increased for more creative, natural responses
                max_tokens: 600,  // Increased for more detailed answers
                top_p: 0.9,       // Better diversity in responses
            })
        });

        if (!response.ok) {
            throw new Error('API request failed');
        }

        const data = await response.json();
        return data.choices[0].message.content;
    }

    addMessage(text, type) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.innerHTML = `<div class="message-content">${this.formatMessage(text)}</div>`;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async addMessageWithTypingEffect(text, type) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        
        // Format the text first
        const formattedText = this.formatMessage(text);
        
        // Type character by character
        let currentText = '';
        const speed = 15; // milliseconds per character (adjust for faster/slower typing)
        
        for (let i = 0; i < formattedText.length; i++) {
            currentText += formattedText[i];
            contentDiv.innerHTML = currentText;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Slight delay for smoother effect
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }

    async addMessageWithTypingEffect(text, type) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        
        // Format the text first
        const formattedText = this.formatMessage(text);
        
        // Create a temporary div to parse HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = formattedText;
        
        // Type character by character
        let currentText = '';
        const speed = 15; // milliseconds per character
        
        for (let i = 0; i < formattedText.length; i++) {
            currentText += formattedText[i];
            contentDiv.innerHTML = currentText;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }

    formatMessage(text) {
        // Convert LinkedIn URLs
        text = text.replace(/(https:\/\/www\.linkedin\.com\/in\/[^\s]+)/g, 
            '<a href="$1" target="_blank" class="chat-link">LinkedIn Profile</a>');
        
        // Convert GitHub profile URL
        text = text.replace(/https:\/\/github\.com\/NadeemAkhtar1947(?!\/[a-zA-Z0-9-]+)/g, 
            '<a href="https://github.com/NadeemAkhtar1947" target="_blank" class="chat-link">GitHub Profile</a>');
        
        // Convert Kaggle URLs
        text = text.replace(/(https:\/\/www\.kaggle\.com\/[^\s]+)/g, 
            '<a href="$1" target="_blank" class="chat-link">Kaggle Profile</a>');
        
        // Convert portfolio URL
        text = text.replace(/https:\/\/nsde\.netlify\.app\/?/g, 
            '<a href="https://nsde.netlify.app/" target="_blank" class="chat-link">View Portfolio</a>');
        
        // Convert Streamlit app URLs
        text = text.replace(/(https:\/\/[a-z0-9-]+\.streamlit\.app[^\s]*)/g, 
            '<a href="$1" target="_blank" class="chat-link">View Live App</a>');
        
        // Convert GitHub repo URLs
        text = text.replace(/https:\/\/github\.com\/([^\/\s]+)\/([^\s<]+)/g, (match, user, repo) => {
            return `<a href="${match}" target="_blank" class="chat-link">🔗 ${repo}</a>`;
        });
        
        // Convert email addresses
        text = text.replace(/nadeemnns2000@gmail\.com/g, 
            '<a href="mailto:nadeemnns2000@gmail.com" class="chat-link">Email Me</a>');
        
        // Convert remaining URLs
        text = text.replace(/(?<!href="|">)(https?:\/\/[^\s<]+)(?!<\/a>)/g, 
            '<a href="$1" target="_blank" class="chat-link">🔗 Link</a>');
        
        // Convert newlines to <br>
        text = text.replace(/\n/g, '<br>');
        
        return text;
    }

    showTyping() {
        this.isTyping = true;
        const messagesContainer = document.getElementById('chatbot-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-content">
                <span></span><span></span><span></span>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTyping() {
        this.isTyping = false;
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('Initializing chatbot...');
        
        // Load config from backend first
        await loadChatbotConfig();
        
        const chatbot = new ResumeChatbot();
        console.log('Chatbot initialized successfully');
        
        // Auto-open after 3 seconds
        setTimeout(() => {
            if (!chatbot.isOpen) {
                chatbot.toggleChat();
            }
        }, 3000);
    } catch (error) {
        console.error('Chatbot initialization error:', error);
    }
});
