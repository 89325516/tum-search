// API Configuration
// Configure the base URL for backend API
// If frontend and backend are deployed under the same domain, can be set to empty string or relative path
// If frontend and backend are deployed separately, need to set to full backend URL, e.g.: 'https://api.example.com'

const API_CONFIG = {
    // Backend API base URL
    baseURL: window.location.origin, // Default to current domain
    
    // WebSocket connection URL
    wsURL: (() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}`;
    })(),
    
    // API endpoints
    endpoints: {
        search: '/api/search',
        feedback: '/api/feedback',
        trending: '/api/trending',
        feed: '/api/feed',
        item: '/api/item',
        upload: {
            url: '/api/upload/url',
            text: '/api/upload/text',
            image: '/api/upload/image'
        },
        admin: {
            browse: '/api/admin/browse',
            promote: '/api/admin/promote',
            delete: '/api/admin/delete',
            backfill: '/api/admin/backfill'
        }
    },
    
    // Get full API URL
    getURL: function(endpoint) {
        if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
            return endpoint;
        }
        return `${this.baseURL}${endpoint}`;
    },
    
    // Get WebSocket URL
    getWebSocketURL: function(path = '/ws') {
        return `${this.wsURL}${path}`;
    }
};

// If you need to use different configurations for different environments, set it like this:
// if (window.location.hostname === 'localhost') {
//     API_CONFIG.baseURL = 'http://localhost:8000';
//     API_CONFIG.wsURL = 'ws://localhost:8000';
// } else {
//     API_CONFIG.baseURL = 'https://api.production.com';
//     API_CONFIG.wsURL = 'wss://api.production.com';
// }

