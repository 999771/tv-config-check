addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request, event))
})

// -------------------- URL 解析函数 --------------------
/**
 * 将 GitHub blob 链接转换为 raw 链接，以获取原始文件内容。
 * @param {string} url - 原始 URL
 * @returns {string} - 可直接访问的最终 URL
 */
function resolveFinalUrl(url) {
  try {
    const urlObj = new URL(url);
    if (urlObj.hostname === 'github.com' && urlObj.pathname.includes('/blob/')) {
      const parts = urlObj.pathname.split('/');
      parts.splice(3, 1); // 移除 'blob'
      const rawPathname = parts.join('/');
      return `https://raw.githubusercontent.com${rawPathname}`;
    }
    return url;
  } catch (e) {
    return url;
  }
}

// -------------------- Base58 编码函数 --------------------
const BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
function base58Encode(obj) {
  const str = JSON.stringify(obj)
  const bytes = new TextEncoder().encode(str)
  let intVal = 0n
  for (let b of bytes) { intVal = (intVal << 8n) + BigInt(b) }
  let result = ''
  while (intVal > 0n) { const mod = intVal % 58n; result = BASE58_ALPHABET[Number(mod)] + result; intVal = intVal / 58n }
  for (let b of bytes) { if (b === 0) result = BASE58_ALPHABET[0] + result; else break }
  return result
}

// -------------------- JSON API 字段前缀替换函数 --------------------
function addOrReplacePrefix(obj, newPrefix) {
  if (typeof obj !== 'object' || obj === null) return obj
  if (Array.isArray(obj)) return obj.map(item => addOrReplacePrefix(item, newPrefix))
  const newObj = {}
  for (const key in obj) {
    if (key === 'api' && typeof obj[key] === 'string') {
      let apiUrl = obj[key]
      const urlIndex = apiUrl.indexOf('?url=')
      if (urlIndex !== -1) apiUrl = apiUrl.slice(urlIndex + 5)
      if (!apiUrl.startsWith(newPrefix)) apiUrl = newPrefix + apiUrl
      newObj[key] = apiUrl
    } else {
      newObj[key] = addOrReplacePrefix(obj[key], newPrefix)
    }
  }
  return newObj
}

// -------------------- 主请求处理函数 --------------------
async function handleRequest(request, event) {
  // 从环境变量 'vod' 中读取默认目标 API URL
  const defaultVodUrl = event.env.vod;

  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
  }

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders })
  }

  const reqUrl = new URL(request.url)
  const targetUrlParam = reqUrl.searchParams.get('url')
  const configParam = reqUrl.searchParams.get('config')
  const prefixParam = reqUrl.searchParams.get('prefix')
  const encodeParam = reqUrl.searchParams.get('encode')

  const currentOrigin = reqUrl.origin
  const defaultPrefix = currentOrigin + '/?url='

  // -------------------- 功能一：JSON 配置处理 --------------------
  if (configParam !== null) {
    const jsonUrl = 'https://raw.githubusercontent.com/hafrey1/LunaTV-config/main/jingjian.json'
    try {
      const response = await fetch(jsonUrl)
      if (!response.ok) throw new Error(`Failed to fetch config: ${response.statusText}`)
      const data = await response.json()
      const finalData = (configParam === '1') ? addOrReplacePrefix(data, prefixParam || defaultPrefix) : data

      if (encodeParam === 'base58') {
        return new Response(base58Encode(finalData), { headers: { 'Content-Type': 'text/plain;charset=UTF-8', ...corsHeaders } })
      } else {
        return new Response(JSON.stringify(finalData), { headers: { 'Content-Type': 'application/json;charset=UTF-8', ...corsHeaders } })
      }
    } catch (err) {
      return new Response(JSON.stringify({ error: 'Config processing failed', message: err.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json; charset=utf-8', ...corsHeaders },
      })
    }
  }

  // -------------------- 功能二：通用 API 代理 --------------------
  if (targetUrlParam) {
    let fullTargetUrl = targetUrlParam
    const urlMatch = request.url.match(/[?&]url=([^&]+(?:&.*)?)/)
    if (urlMatch) fullTargetUrl = decodeURIComponent(urlMatch[1])
    
    const finalTargetUrl = resolveFinalUrl(fullTargetUrl);

    try {
      const proxyRequest = new Request(finalTargetUrl, {
        method: request.method,
        headers: request.headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.arrayBuffer() : undefined,
      })

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)
      const response = await fetch(proxyRequest, { signal: controller.signal })
      clearTimeout(timeoutId)

      const responseHeaders = new Headers(corsHeaders)
      const excludeHeaders = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'keep-alive', 'set-cookie']
      for (const [key, value] of response.headers) {
        if (!excludeHeaders.includes(key.toLowerCase())) responseHeaders.set(key, value)
      }

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders
      })
    } catch (err) {
      return new Response(JSON.stringify({
        error: 'Proxy Error', message: err.message, target: finalTargetUrl, timestamp: new Date().toISOString()
      }, null, 2), {
        status: 502,
        headers: { 'Content-Type': 'application/json; charset=utf-8', ...corsHeaders }
      })
    }
  }

  // -------------------- 功能三：根路径默认代理 --------------------
  if (reqUrl.pathname === '/') {
    if (defaultVodUrl) {
      const finalTargetUrl = resolveFinalUrl(defaultVodUrl);
      try {
        const proxyRequest = new Request(finalTargetUrl, { method: request.method, headers: request.headers, body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.arrayBuffer() : undefined, })
        const response = await fetch(proxyRequest)
        const responseHeaders = new Headers(corsHeaders)
        const excludeHeaders = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'keep-alive', 'set-cookie']
        for (const [key, value] of response.headers) { if (!excludeHeaders.includes(key.toLowerCase())) responseHeaders.set(key, value) }
        return new Response(response.body, { status: response.status, statusText: response.statusText, headers: responseHeaders })
      } catch (err) {
        return new Response(JSON.stringify({ error: 'Default Proxy Error', message: err.message, target: finalTargetUrl, timestamp: new Date().toISOString() }, null, 2), { status: 502, headers: { 'Content-Type': 'application/json; charset=utf-8', ...corsHeaders } })
      }
    } else {
      const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>API 中转代理服务</title><style>body{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto;padding:20px;line-height:1.6}h1{color:#333}code{background:#f4f4f4;padding:2px 6px;border-radius:3px}pre{background:#f4f4f4;padding:15px;border-radius:5px}</style></head><body><h1>🔄 API 中转代理服务</h1><p>此 Worker 已部署，但未设置默认代理目标。</p><h2>设置默认代理</h2><p>在 Cloudflare Workers 的环境变量中添加一个名为 <code>vod</code> 的变量，其值为一个 API 地址。</p><pre><code>Variable name: vod
Value: https://api.example.com/v1</code></pre><p>设置后，访问根路径将直接代理到该地址。</p><h2>其他用法</h2><p>代理任意 API: <code>?url=目标地址</code></p><p>获取配置: <code>?config=0</code> 或 <code>?config=1</code></p></body></html>`
      return new Response(html, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', ...corsHeaders } })
    }
  }

  // -------------------- 其他情况返回 404 --------------------
  return new Response(JSON.stringify({ error: 'Not Found' }), {
    status: 404,
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  })
}
