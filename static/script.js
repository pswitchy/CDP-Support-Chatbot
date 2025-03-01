document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    const sendButton = document.getElementById('send-button');
    const questionInput = document.getElementById('question-input');
    const chatHistory = document.getElementById('chat-history');
    let isRequesting = false;

    // Fetch supported CDPs on page load
    fetchSupportedCDPs();

    // Display welcome message on page load
    addMessageToHistory('bot', 'Hello! I\'m your CDP Support Assistant. How can I help you with your Customer Data Platform questions today?');
    questionInput.focus();

    // Event listeners
    sendButton.addEventListener('click', sendQuestion);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !isRequesting) {
            sendQuestion();
        }
    });

    // Function to fetch supported CDPs
    async function fetchSupportedCDPs() {
        try {
            const response = await fetch('/supported-cdps');
            if (!response.ok) {
                throw new Error('Failed to fetch supported CDPs');
            }
            const data = await response.json();
            if (data.cdps && Array.isArray(data.cdps)) {
                const cdpList = data.cdps.join(', ');
                addMessageToHistory('bot', `I can answer questions about these CDP platforms: ${cdpList}. What would you like to know?`);
            }
        } catch (error) {
            console.error('Error fetching supported CDPs:', error);
        }
    }

    // Function to send question to backend
    async function sendQuestion() {
        if (isRequesting) return;
        const question = questionInput.value.trim();
        if (!question) return;

        // Set loading state
        isRequesting = true;
        sendButton.disabled = true;
        sendButton.textContent = 'Sending...';

        // Display user's message
        addMessageToHistory('user', question);
        questionInput.value = '';

        // Show typing indicator
        const typingIndicator = addTypingIndicator();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: question })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            typingIndicator.remove();
            
            // Create message with platform info if available
            let message = data.answer;
            if (data.cdp && data.cdp !== "None") {
                const platformInfo = document.createElement('div');
                platformInfo.classList.add('platform-info');
                platformInfo.innerHTML = `<span class="platform-badge">${data.cdp}</span>`;
                if (data.task && data.task !== "None") {
                    platformInfo.innerHTML += ` <span class="task-badge">${data.task}</span>`;
                }
                
                const messageWrapper = document.createElement('div');
                const messageText = document.createElement('div');
                messageText.textContent = message;
                
                messageWrapper.appendChild(platformInfo);
                messageWrapper.appendChild(messageText);
                
                addCustomMessageToHistory('bot', messageWrapper);
            } else {
                addMessageToHistory('bot', message);
            }
        } catch (error) {
            console.error('Error:', error);
            typingIndicator.remove();
            addMessageToHistory('bot', 'Sorry, there was an error processing your request. Please try again.');
        } finally {
            // Reset loading state
            isRequesting = false;
            sendButton.disabled = false;
            sendButton.textContent = 'Send';
            questionInput.focus();
        }
    }

    // Function to add messages to chat history
    function addMessageToHistory(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role);
        messageDiv.textContent = content;
        chatHistory.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Function to add custom HTML content to chat history
    function addCustomMessageToHistory(role, contentElement) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role);
        messageDiv.appendChild(contentElement);
        chatHistory.appendChild(messageDiv);
        scrollToBottom();
    }

    // Function to add typing indicator
    function addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('message', 'bot', 'typing');
        
        // Create animated typing dots
        const dotsContainer = document.createElement('div');
        dotsContainer.classList.add('typing-dots');
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.classList.add('dot');
            dotsContainer.appendChild(dot);
        }
        
        typingDiv.appendChild(dotsContainer);
        chatHistory.appendChild(typingDiv);
        scrollToBottom();
        return typingDiv;
    }
    
    // Function to scroll chat to bottom
    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});