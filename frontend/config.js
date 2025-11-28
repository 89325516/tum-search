// API配置
// 配置后端API的基础URL
// 如果前端和后端部署在同一域名下，可以设置为空字符串或相对路径
// 如果前后端分离部署，需要设置为完整的后端URL，例如: 'https://api.example.com'

const API_CONFIG = {
    // 后端API基础URL
    baseURL: window.location.origin, // 默认使用当前域名
    
    // WebSocket连接URL
    wsURL: (() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}`;
    })(),
    
    // API端点
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
    
    // 获取完整的API URL
    getURL: function(endpoint) {
        if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
            return endpoint;
        }
        return `${this.baseURL}${endpoint}`;
    },
    
    // 获取WebSocket URL
    getWebSocketURL: function(path = '/ws') {
        return `${this.wsURL}${path}`;
    }
};

// 如果需要在不同环境使用不同配置，可以这样设置：
// if (window.location.hostname === 'localhost') {
//     API_CONFIG.baseURL = 'http://localhost:8000';
//     API_CONFIG.wsURL = 'ws://localhost:8000';
// } else {
//     API_CONFIG.baseURL = 'https://api.production.com';
//     API_CONFIG.wsURL = 'wss://api.production.com';
// }

