addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // 允许的请求来源域名
  const allowedOrigins = [
    'https://cors.1008008.xyz'
  ];

  // 允许的路径前缀列表
  const allowedPathPrefixes = [
    '/api.php/provide/vod',
    '/api.php/provide/vod/at/xml'
  ];

  // 获取请求来源
  const requestOrigin = request.headers.get('origin');
  
  // 验证请求来源
  if (requestOrigin && !allowedOrigins.includes(requestOrigin)) {
    return new Response('Forbidden - Origin not allowed', { status: 403 });
  }

  // 处理OPTIONS预检请求
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': requestOrigin || '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, User-Agent'
      }
    });
  }

  // 只允许GET请求
  if (request.method !== 'GET') {
    return new Response('Method not allowed', { status: 405 });
  }

  // 获取目标URL
  const { searchParams } = new URL(request.url);
  const targetUrl = searchParams.get('url');

  // 验证目标URL
  if (!targetUrl) {
    return new Response('Missing URL parameter', { status: 400 });
  }

  try {
    // 解析目标URL
    const urlObj = new URL(targetUrl);
    
    // 验证路径前缀
    const isPathAllowed = allowedPathPrefixes.some(prefix => 
      urlObj.pathname.startsWith(prefix)
    );
    
    if (!isPathAllowed) {
      return new Response('Forbidden - Path not allowed', { status: 403 });
    }

    // 创建请求头（保留User-Agent）
    const headers = new Headers();
    const userAgent = request.headers.get('user-agent');
    if (userAgent) {
      headers.set('User-Agent', userAgent);
    }

    // 代理请求
    const response = await fetch(targetUrl, { headers });
    
    // 创建响应头（添加CORS支持）
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set('Access-Control-Allow-Origin', requestOrigin || '*');
    
    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders
    });
  } catch (error) {
    // 处理URL解析错误
    if (error instanceof TypeError && error.message.includes('Invalid URL')) {
      return new Response('Invalid URL', { status: 400 });
    }
    
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': requestOrigin || '*'
      }
    });
  }
}
