// Debug frontend API calls
async function debugAPI() {
    try {
        const response = await fetch('/api/bots');
        const data = await response.json();
        
        if (data && data.length > 0) {
            const firstBot = data[0];
            console.log('First bot data:', firstBot);
            console.log('win_rate_6h:', firstBot.win_rate_6h);
            console.log('Type of win_rate_6h:', typeof firstBot.win_rate_6h);
            console.log('performance_6h:', firstBot.performance_6h);
            
            if (firstBot.performance_6h) {
                console.log('win_rate in performance_6h:', firstBot.performance_6h.win_rate);
            }
        }
    } catch (error) {
        console.error('Error debugging API:', error);
    }
}

// Call this when the page loads
setTimeout(debugAPI, 2000);