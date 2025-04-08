    // Initialize D3.js graph visualization
    document.addEventListener('DOMContentLoaded', function() {
        // Load graph data
        fetch('/graph-data')
            .then(response => response.json())
            .then(data => createForceGraph(data));
            
        // Initialize chat functionality
        initializeChat();
    });
    
    function createForceGraph(data) {
        const width = document.getElementById('graph-container').offsetWidth;
        const height = document.getElementById('graph-container').offsetHeight;
        
        // Clear any existing SVG
        d3.select("#graph-container svg").remove();
        
        // Create SVG
        const svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        // Define color scheme
        const color = d3.scaleOrdinal()
            .domain([1, 2, 3])
            .range(["#3498db", "#e74c3c", "#2ecc71"]);
            
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });
            
        svg.call(zoom);
        
        // Create container for graph
        const g = svg.append("g");
        
        // Create tooltip
        const tooltip = d3.select("body")
            .append("div")
            .attr("class", "tooltip")
            .style("position", "absolute")
            .style("background-color", "white")
            .style("border", "1px solid #ddd")
            .style("border-radius", "5px")
            .style("padding", "10px")
            .style("display", "none")
            .style("z-index", "1000");
            
        // Create force simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide().radius(d => (d.type === "Cryptocurrency" ? 40 : 30)));
            
        // Draw links
        const link = g.append("g")
            .selectAll("line")
            .data(data.links)
            .enter()
            .append("line")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", d => Math.sqrt(d.value));
            
        // Draw nodes
        const node = g.append("g")
            .selectAll("circle")
            .data(data.nodes)
            .enter()
            .append("circle")
            .attr("r", d => {
                if (d.type === "Cryptocurrency") return 15;
                if (d.type === "Topic") return 12;
                return 8;
            })
            .attr("fill", d => color(d.group))
            .call(drag(simulation))
            .on("mouseover", function(event, d) {
                tooltip.style("display", "block")
                    .html(`<strong>${d.name}</strong><br>Type: ${d.type}${d.symbol ? '<br>Symbol: ' + d.symbol : ''}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", function() {
                tooltip.style("display", "none");
            });
            
        // Add node labels
        const label = g.append("g")
            .selectAll("text")
            .data(data.nodes.filter(d => d.type === "Cryptocurrency" || d.type === "Topic"))
            .enter()
            .append("text")
            .attr("dx", 15)
            .attr("dy", ".35em")
            .text(d => d.type === "Cryptocurrency" ? d.symbol || d.name : d.name)
            .style("font-size", "12px")
            .style("fill", "white");
            
        // Update positions on each tick
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
                
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
                
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        });
        
        // Drag functionality
        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            
            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }
    }
    
    function initializeChat() {
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        const resetButton = document.getElementById('reset-chat');
        const chatMessages = document.getElementById('chat-messages');
        
        // Handle sending messages
        function sendMessage() {
            const message = chatInput.value.trim();
            if (message === '') return;
            
            // Display user message
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'user-message';
            userMessageDiv.textContent = message;
            chatMessages.appendChild(userMessageDiv);
            
            // Clear input
            chatInput.value = '';
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Show loading indicator
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'system-message';
            loadingDiv.textContent = 'Loading response...';
            chatMessages.appendChild(loadingDiv);
            
            // Send to server
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading indicator
                chatMessages.removeChild(loadingDiv);
                
                // Display assistant response
                const assistantMessageDiv = document.createElement('div');
                assistantMessageDiv.className = 'assistant-message';
                assistantMessageDiv.textContent = data.response;
                chatMessages.appendChild(assistantMessageDiv);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            })
            .catch(error => {
                // Remove loading indicator
                chatMessages.removeChild(loadingDiv);
                
                // Display error
                const errorDiv = document.createElement('div');
                errorDiv.className = 'system-message';
                errorDiv.textContent = 'Error: Could not get response.';
                chatMessages.appendChild(errorDiv);
                console.error('Error:', error);
            });
        }
        
        // Handle resetting chat
        function resetChat() {
            // Clear all messages from UI
            chatMessages.innerHTML = '';
            
            // Add loading message
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'system-message';
            loadingDiv.textContent = 'Resetting chat history...';
            chatMessages.appendChild(loadingDiv);
            
            // Send reset request to server
            fetch('/reset-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log('Chat history reset:', data);
                
                // Remove loading message
                chatMessages.removeChild(loadingDiv);
                
                // Add confirmation message
                const confirmDiv = document.createElement('div');
                confirmDiv.className = 'system-message';
                confirmDiv.textContent = data.message || 'Chat history has been reset. You can start a new conversation.';
                chatMessages.appendChild(confirmDiv);
                
                // Add welcome message back
                const welcomeDiv = document.createElement('div');
                welcomeDiv.className = 'system-message';
                welcomeDiv.textContent = 'Welcome to the Crypto News GraphRAG assistant. Ask me anything about the latest cryptocurrency news and trends!';
                chatMessages.appendChild(welcomeDiv);
            })
            .catch(error => {
                console.error('Error resetting chat:', error);
                
                // Remove loading message
                if (chatMessages.contains(loadingDiv)) {
                    chatMessages.removeChild(loadingDiv);
                }
                
                // Add error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'system-message';
                errorDiv.textContent = 'Error resetting chat. Please try again.';
                chatMessages.appendChild(errorDiv);
            });
        }
        
        // Event listeners
        sendButton.addEventListener('click', sendMessage);
        resetButton.addEventListener('click', resetChat);
        
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Add event listener for the reset button - double-check it's working
        if (resetButton) {
            console.log("Reset button found and listener attached");
            resetButton.onclick = resetChat;
        } else {
            console.error("Reset button not found in the DOM");
        }
    }
    