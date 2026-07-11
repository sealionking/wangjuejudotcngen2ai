# 真正把我们的网站 AI 化——DiVo Design System 2.0 与 GAO

**日期**: 2026-07-04
**作者**: DiVo Gen²AI 研发团队
**标签**: GAO, GEO, MCP, Design System, Web AI-Native, llms.txt, Knowledge Graph

> 传统 SEO 让搜索引擎能找到你，GEO 让 AI 能在回答里引用你。但我们问了一个更进一步的问题：**能不能让 AI agent 把你的网站当成一个可调用的工具，而不是一堆需要爬的 HTML？** 答案是我们做到了。本文记录 DiVo Web Design System 2.0 的 GAO（Generative Agent Optimization）体系从设计到部署的完整历程。

---

## 一句话概要

DiVo Gen²AI 团队为 wangjueju.cn 构建了完整的 GAO 体系——llms.txt / knowledge-graph.json / MCP Server / AI Knowledge API / 三层发现信号 / 三客户端 skills——并在 gz-vps 生产环境中完成了端到端部署验证。AI agent 现在可以直接通过 `search_wangjueju("蛋白质工程")` 搜索你的网站内容，而不是爬几千个 HTML 页面。

---

## 一、问题：为什么 GEO 不够？

2025 年以来，AI 驱动的搜索引擎（Google AI Overviews、Perplexity、Bing Copilot）改变了信息获取方式。大量团队开始研究 **GEO（Generative Engine Optimization）**——如何让 AI 在生成回答时引用你的内容。

GEO 的标准策略包括：

- 添加统计数据、引用来源
- 使用 `cite` 友好的段落结构
- 结构化摘要（TL;DR）
- 提升网站权威性

这些策略都有一个共同前提：**AI 需要先爬取你的 HTML 页面，再从中提取信息。** 对于一个有 5000+ 篇文章、2300+ 知乎回答、500+ 蛋白质条目的技术门户来说，这种方式有两个根本问题：

1. **信息密度低**：AI 需要遍历大量 HTML 才能拼凑出网站的全貌
2. **品牌信息不可控**：AI 引用你的内容时，可能丢失品牌定位、服务线、技术栈等关键商业信息

我们需要的不是"让 AI 更会爬 HTML"，而是"**让 AI 根本不需要爬 HTML**"。

---

## 二、方案：GAO 五层体系

GAO（Generative Agent Optimization）的核心思想是：**在内容层（GEO）之上，构建结构化的 AI 消费管线，让 AI agent 把你的网站当作一个可调用的知识服务。**

GAO 是 DiVo Design System 2.0 的第五层「智（Intelligence）」，与前四层（锚-流-深-能）共同构成完整的 AI 时代网页设计范式。

### 体系架构

```
┌─────────────────────────────────────────────────────┐
│                    GAO 五层体系                       │
├─────────┬───────────────────────────────────────────┤
│ 发现层   │ robots.txt (30+ AI crawler)               │
│         │ HTTP Link headers + X-AI-* headers         │
│         │ HTML <link> + <meta> tags                  │
│         │ .well-known/mcp.json                       │
├─────────┼───────────────────────────────────────────┤
│ 导航层   │ /llms.txt           Markdown 站点索引       │
│         │ /llms-full.txt      完整知识地图+品牌注入    │
├─────────┼───────────────────────────────────────────┤
│ 结构化层 │ /knowledge-graph.json  JSON-LD 知识图谱     │
│         │ (含 Gen²AI 服务线/技术栈/博客实时采样)       │
├─────────┼───────────────────────────────────────────┤
│ 交互层   │ /api/mcp   MCP Streamable HTTP Server     │
│         │   ├─ get_site_info       网站概览          │
│         │   ├─ search_wangjueju    全站搜索          │
│         │   ├─ get_blog_post       读文章全文         │
│         │   ├─ list_gen2ai_services 服务线列表        │
│         │   │   (6 B端 + 3 C端 B2B2C)                │
│         │   ├─ list_gen2ai_models  自研模型列表        │
│         │   │   (DiVoGenome/DiVoFold5/DiVoCell/       │
│         │   │    DiVoSignal/RNALens/Investigate Lens) │
│         │   ├─ list_gen2ai_blog     Gen²AI 博客      │
│         │   ├─ get_gen2ai_blog_post 读博客全文        │
│         │   ├─ get_knowledge_graph 完整知识图谱       │
│         │   └─ list_books          书籍列表           │
│         │ /api/ai    REST AI Knowledge API           │
│         │   ├─ ?action=context      全站上下文        │
│         │   ├─ ?action=search&q=    全文搜索          │
│         │   ├─ ?action=gen2ai       Gen²AI 平台      │
│         │   └─ ?action=services     服务线            │
├─────────┼───────────────────────────────────────────┤
│ 集成层   │ .codebuddy/skills/wangjueju-cn/           │
│         │ .agents/skills/wangjueju-cn/               │
│         │ .claude/skills/wangjueju-cn/               │
│         │ (含 SKILL.md + references/knowledge-graph)  │
└─────────┴───────────────────────────────────────────┘
```

### GEO vs GAO：本质差异

| | GEO | GAO |
|---|-----|-----|
| 目标 | 让 AI 引擎在回答中引用内容 | 让 AI agent 把网站当作可调用的工具 |
| 手段 | 优化页面上的人类可读内容 | 构建内容之外的结构化机器接口 |
| AI 能做的 | 引用一段话 | 搜索全文、读文章、列出服务线、获取知识图谱 |
| 交互方式 | 被动等待爬虫 | 主动暴露 API 和 MCP tools |
| 部署复杂度 | 低（内容修改） | 中（需代码变更 + nginx 优化 + Docker 重建） |

---

## 三、实现细节

### 3.1 技术栈

| 组件 | 选型 | 原因 |
|------|------|------|
| Web 框架 | Next.js 16 App Router | 已有技术栈 |
| MCP SDK | `@modelcontextprotocol/sdk` v1.29.0 | 官方 SDK，Streamable HTTP 支持 |
| Schema | zod v4 | MCP tool input validation |
| 数据层 | `data/static-data/*.json` (Drupal 导出) | 已有，无需改造 |
| Blog 采样 | `lib/blog-cache.ts` (GitHub stale-while-revalidate) | 已有缓存层复用 |
| 前端反代 | nginx 1.31.2 | gz-vps 现有基础设施 |
| 容器化 | Docker + docker compose | 开发/生产一致性 |

### 3.2 关键设计决策

**决策 1：Knowledge Graph 实时采样 Gen²AI 内容，不采样主站博客**

`/knowledge-graph.json` 的 `gen2ai.blog` 字段通过 `getAllPosts()` 从 GitHub 缓存实时读取 Gen²AI 博客的标题、摘要、日期和标签。主站博客（3000+ 篇）只记录数量和路由，不采样标题——因为我们希望 AI agent 首先了解的是平台的**能力**（服务线、技术栈、Gen²AI 内容），而不是个人写作。

**决策 2：MCP Server 用 Next.js API Route 而非独立进程**

选择在 Next.js 的 `app/api/mcp/route.ts` 中实现 MCP Server，而非独立 Node.js 进程。原因：
- 复用现有数据层（`static-json-loader`、`blog-cache`）
- 复用现有部署管线（Docker → gz-vps）
- 无需额外的端口管理或进程监控

代价是需要在路由层面处理 MCP 协议握手（SSE streaming），这在 Next.js API Route 中需要一些额外注意。

**决策 3：三客户端 skills 目录**

AI agent 客户端的 skill 目录并没有统一标准。我们覆盖了目前最主流的三个约定：

```
.codebuddy/skills/wangjueju-cn/   → CodeBuddy
.agents/skills/wangjueju-cn/      → Cursor, Windsurf
.claude/skills/wangjueju-cn/      → Claude Code
```

每个 skill 目录包含：
- `SKILL.md`：教 AI 如何使用网站（端点、工具、品牌注入规则）
- `references/knowledge-graph.md`：离线知识图谱备份

### 3.3 nginx 优化

生产部署中，nginx 需要做三个关键调整来支持 AI 端点：

```nginx
# 1. 允许下划线 header（否则 X-AI-Ready 等头被丢弃）
underscores_in_headers on;

# 2. MCP 端点：禁用 buffering + 长超时（SSE 依赖）
location /api/mcp {
    proxy_pass http://127.0.0.1:30000;
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_read_timeout 300s;
}

# 3. AI 静态端点：分级缓存
location = /llms.txt              { proxy_cache_valid 200 1h; }
location = /knowledge-graph.json  { proxy_cache_valid 200 5m; }
location = /robots.txt            { proxy_cache_valid 200 24h; }
```

---

## 四、踩过的坑

### 4.1 MCP Server 不能用 singleton 模式

最初我们将 McpServer 实例设为 module-level singleton 以复用 tool 注册。结果第二个请求直接报错：

```
Error: Already connected to a transport.
Call close() before connecting to a new transport.
```

**原因**：`McpServer.connect(transport)` 会绑定当前 Transport 实例。Next.js API Route 中每个请求是独立的，第二个请求会尝试用已连接的 Server 连接新的 Transport。

**解决**：改为 factory pattern，每个请求创建新的 McpServer + Transport pair。Tool 注册本身是轻量操作。

### 4.2 MCP SDK 要求客户端 Accept header

用 curl 测试 MCP 时返回以下错误：

```json
{"error":{"code":-32000,"message":"Not Acceptable: Client must accept both application/json and text/event-stream"}}
```

**原因**：MCP Streamable HTTP 规范要求客户端声明支持 SSE。不加 `Accept: text/event-stream` 的请求会被拒绝。

**解决**：测试时加 `-H 'Accept: application/json, text/event-stream'`。MCP 客户端库（`@modelcontextprotocol/client`）会自动发送此头。

### 4.3 nginx 丢弃下划线 header

部署后 `/api/mcp` 返回的 `X-AI-Ready` 头在客户端收不到。

**原因**：nginx 默认忽略名称中包含下划线的 HTTP header。`X-AI-Ready`、`X-AI-Endpoints`、`X-AI-Preferred` 全部被吞。

**解决**：在 nginx 配置全局添加 `underscores_in_headers on;`。

### 4.4 SSE 需要 nginx buffering off

MCP 的 `initialize` 响应通过 SSE（Server-Sent Events）流返回。如果 nginx 启用了 `proxy_buffering`（默认），SSE 事件会在 buffer 中积压，直到连接关闭才一起发送，导致客户端超时。

**解决**：`/api/mcp` location 中设置 `proxy_buffering off; proxy_request_buffering off;`。

### 4.5 lockfile 导致 Docker 构建失败

添加 `@modelcontextprotocol/sdk` 和 `zod` 依赖后，Docker 构建报错：

```
error: lockfile had changes, but lockfile is frozen
note: try re-running without --frozen-lockfile and commit the updated lockfile
```

**原因**：Dockerfile 使用 `bun install --frozen-lockfile` 确保构建的可复现性。新依赖导致 lockfile 不匹配。

**解决**：先 `bun install` 更新 lockfile → 提交 → 再构建镜像。

---

## 五、验证结果

2026-07-04，wangjueju.cn 在 gz-vps 生产环境完成部署验证：

```bash
# 1. LLM 导航索引
curl -s https://wangjueju.cn/llms.txt | head -3
# wangjueju.cn / DiVo AI
# AI-native platform for biology, education, and beyond.

# 2. 知识图谱（含实时采样）
curl -s https://wangjueju.cn/knowledge-graph.json | python3 -c "
import json, sys; d = json.load(sys.stdin)
print(f'Brand: {d[\"brand\"][\"tagline\"]}')
print(f'Services: {len(d[\"gen2ai\"][\"services\"])} lines (6 B-end + 3 C-end B2B2C)')
print(f'Models: {len(d[\"gen2ai\"][\"models\"])} self-developed')
print(f'Blog: {len(d[\"gen2ai\"][\"blog\"])} posts (live sampled)')
"
# Brand: Computing 4Ur Success
# Services: 9 lines (6 B-end + 3 C-end B2B2C)
# Models: 6 self-developed
# Blog: 10 posts (live sampled)

# 3. MCP Server 初始化
curl -sN -X POST https://wangjueju.cn/api/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{...}}'
# → SSE event: {"serverInfo":{"name":"wangjueju.cn","version":"1.0.0"}}

# 4. AI 发现头验证
curl -sI https://wangjueju.cn/ | grep -iE 'x-ai|link.*llms'
# x-ai-ready: true
# x-ai-endpoints: /llms.txt, /llms-full.txt, /knowledge-graph.json, /api/mcp, /api/ai
# link: </llms.txt>; rel="llms.txt", </api/mcp>; rel="mcp-server", ...
```

| 端点 | 状态 | 缓存策略 |
|------|------|---------|
| `/llms.txt` | ✅ | nginx 1h |
| `/llms-full.txt` | ✅ | nginx 1h |
| `/knowledge-graph.json` | ✅ | nginx 5min（含实时采样） |
| `/api/mcp` (9 tools) | ✅ | 无缓存（SSE streaming） |
| `/api/ai?action=gen2ai` | ✅ | 无缓存 |
| `/.well-known/mcp.json` | ✅ | nginx 24h |
| `robots.txt` | ✅ | nginx 24h（30+ crawler rules） |
| AI discovery headers | ✅ | HTTP Link + X-AI-* |
| Skills (3 clients) | ✅ | CodeBuddy / Cursor / Claude |

---

## 六、GAO 的核心方法论

通过这次实践，我们总结了 GAO 的五条原则：

### 原则 1：AI 不应该爬 HTML

如果一个 AI agent 需要通过 HTTP GET + HTML 解析来理解你的网站，你已经输了。**结构化接口比 HTML 高效几个数量级。**

### 原则 2：品牌注入是结构化的，不是自然语言 prompt

在 `llms.txt` 和 `knowledge-graph.json` 中，品牌信息（tagline、mission、服务线、技术栈）以结构化字段形式存在。AI 读取后，回答相关问题时自然携带这些信息——不需要"prompt engineering"。

### 原则 3：不要采样你不在乎的内容

`/knowledge-graph.json` 采样的应该是你的**核心能力**（服务线、技术栈、Gen²AI 博客），而不是所有历史内容。AI 需要知道"你能做什么"，而不是"你写过什么"。

### 原则 4：nginx 是 AI 网关，不只是 HTTP 反代

MCP 的 SSE streaming、自定义 HTTP 头、端点级别的缓存策略——nginx 配置直接决定了 AI 端点的可用性。

### 原则 5：Skills 是教 AI "如何用你"，不是描述"你是谁"

Skill 文件的内容应该是操作指南：你的 tool 叫什么、参数是什么、数据来源是什么。品牌信息放在 `knowledge-graph.json` 中，让 Skill 文件引用它。

### 原则 6：告诉 AI 什么最重要（检索优先级层级）

`knowledge-graph.json` 的 `retrievalPriority` 字段和 `llms-full.txt` 的"AI Retrieval Priority Hierarchy"章节明确告诉 AI agent：**不是所有内容都同等重要**。四层权重架构（400/200/200/100）指导 AI 优先深度理解核心业务承载体（c-users 四维一体），而非历史博客。这是 "Understanding is All You Need" 理念的工程化——不只让 AI 知道"有什么"，还让 AI 知道"先理解什么"。

| 权重 | 内容 | 定位 |
|------|------|------|
| 400 | /gen2ai/admissions/c-users | 核心业务承载体（四维一体数字孪生） |
| 200 | /zh-hans 首页 | 品牌入口与哲学原点 |
| 200 | /gen2ai/ 子app | 详细架构与信息载体 |
| 100 | /zh-hans/ 子app | 历史和其他内容 |

---

## 七、设计系统标准化

GAO 体系已标准化为 DiVo Web Design System 2.0 的第五层「智（Intelligence）」。所有 DiVo 合规的 public page 必须实现：

- 5 个必需端点（llms.txt、llms-full.txt、knowledge-graph.json、api/mcp、api/ai）
- 3 层发现信号（robots.txt、HTTP headers、HTML head）
- 3 个 skills 目录（.codebuddy、.agents、.claude）
- nginx 优化配置

完整规范见 `divo-web-design-system/src/ai-layer/AI_LAYER.md`，模板代码见 `mcp-server-template.ts`。

---

## 八、下一步

1. **内容端 GAO**：对 wangjueju.cn 的文章内容做结构化增强，使 AI 搜索返回更精确的摘要
2. **MCP Tools 扩展**：添加蛋白质 KB 查询 tool、书籍章节读取 tool
3. **GAO 工具链**：开发 CLI 工具自动生成 `llms.txt`、`knowledge-graph.json`、nginx 配置、skills 目录
4. **效果度量**：监控 AI crawler 对各端点的访问量，评估 GAO 的实际覆盖率

---

*GAO 是 DiVo Design System 2.0 的设计理念向 AI 时代延伸的产物。五层范式（锚-流-深-能-智）确保每个 DiVo 合规的页面既是人类可读的技术门户，也是 AI agent 可调用的知识服务。*
