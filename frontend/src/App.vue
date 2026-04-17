<template>
  <div class="app">
    <header class="app-header">
      <div class="header-content">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          <h1>SmartDoc</h1>
        </div>
        <p class="tagline">智能文档问答助手</p>
      </div>
    </header>

    <main class="app-main">
      <div class="container">
        <FileUpload
          :uploading="uploading"
          :upload-status="uploadStatus"
          @upload="handleUpload"
        />

        <div class="chat-container">
          <div class="chat-header">
            <div class="chat-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>智能问答</span>
            </div>
            <div v-if="allMessages.length > 0" class="message-count">{{ allMessages.length }} 条消息</div>
          </div>

          <div class="messages-wrapper" ref="messagesContainer">
            <div v-if="allMessages.length === 0" class="empty-state">
              <div class="empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </div>
              <p class="empty-title">开始对话</p>
              <p class="empty-desc">导入文档后，您可以向 AI 提问关于文档内容的任何问题</p>
              <div class="example-questions">
                <button v-for="(q, i) in examples" :key="i" class="example-btn" @click="handleExampleAsk(q)">
                  {{ q }}
                </button>
              </div>
            </div>

            <template v-else>
              <template v-for="(msg, idx) in allMessages" :key="idx">
                <!-- 普通消息 -->
                <ChatMessage
                  v-if="!msg.isStreaming"
                  :role="msg.role"
                  :content="msg.content"
                  :sources="msg.sources"
                  :timestamp="msg.timestamp"
                />
                <!-- 流式消息 -->
                <StreamMessage
                  v-else
                  :ref="el => setStreamRef(msg.id, el)"
                  :role="msg.role"
                  :content="msg.content"
                  :sources="msg.sources"
                  :timestamp="msg.timestamp"
                  :is-thinking="msg.isThinking"
                />
              </template>

              <div v-if="asking && !currentStreamMessageId" class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
              </div>
            </template>
          </div>

          <div class="chat-footer">
            <ChatInput
              v-model="question"
              v-model:topK="topK"
              :disabled="asking"
              :show-clear="allMessages.length > 0"
              placeholder="输入你的问题，例如：这份文档讲了什么？"
              @send="ask"
              @clear="clearChat"
            />
          </div>
        </div>
      </div>
    </main>

    <footer class="app-footer">
      <p>基于 RAG 技术构建 · 支持多格式文档智能解析</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue';
import FileUpload from './components/FileUpload.vue';
import ChatMessage from './components/ChatMessage.vue';
import ChatInput from './components/ChatInput.vue';
import StreamMessage from './components/StreamMessage.vue';

interface SourceInfo {
  source: string;
  page?: number | null;
  snippet?: string | null;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[];
  timestamp?: Date;
  isStreaming?: boolean;
  isThinking?: boolean;
}

const uploading = ref(false);
const uploadStatus = ref('');
const messages = ref<Message[]>([]);
const question = ref('');
const topK = ref(6);
const asking = ref(false);

// 当前流式消息ID
const currentStreamMessageId = ref<string | null>(null);

const messagesContainer = ref<HTMLDivElement | null>(null);

const examples = [
  '这份文档的主要内容是什么？',
  '请总结一下关键要点',
  '文档中提到了哪些重要数据？',
];

// 流式消息组件引用
const streamRefs = reactive<Record<string, any>>({});

function setStreamRef(id: string, el: any) {
  if (el) {
    streamRefs[id] = el;
  }
}

// 所有消息（包括普通消息和流式消息）
const allMessages = messages;

function scrollToBottom() {
  nextTick(() => {
    const container = messagesContainer.value;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
}

function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

async function handleUpload(files: File[]) {
  uploading.value = true;
  uploadStatus.value = '上传中...';

  try {
    const formData = new FormData();
    for (const f of files) formData.append('files', f);

    const resp = await fetch('/api/docs/ingest', {
      method: 'POST',
      body: formData,
    });

    const data = await resp.json().catch(() => null);
    if (!resp.ok) {
      throw new Error(data?.detail?.failed_files ? JSON.stringify(data.detail) : data?.detail || resp.statusText);
    }

    const ok = data?.ingested_files || [];
    const failed = data?.failed_files || [];
    uploadStatus.value = `导入完成：${ok.length} 个文件成功${failed.length > 0 ? '，' + failed.length + ' 个失败' : ''}`;
  } catch (err: any) {
    uploadStatus.value = `导入失败：${err?.message || String(err)}`;
  } finally {
    uploading.value = false;
  }
}

async function ask() {
  const q = question.value.trim();
  if (!q) return;

  asking.value = true;

  // 添加用户消息
  const userMsgId = generateId();
  messages.value.push({
    id: userMsgId,
    role: 'user',
    content: q,
    timestamp: new Date()
  });

  // 创建空的 AI 流式消息
  const aiMsgId = generateId();
  currentStreamMessageId.value = aiMsgId;
  messages.value.push({
    id: aiMsgId,
    role: 'assistant',
    content: '',
    sources: [],
    timestamp: new Date(),
    isStreaming: true,
    isThinking: true
  });

  question.value = '';
  scrollToBottom();

  try {
    const resp = await fetch('/api/chat/ask/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, top_k: topK.value }),
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => null);
      throw new Error(data?.detail || resp.statusText);
    }

    // 获取流式消息组件引用
    const streamComp = streamRefs[aiMsgId];

    // 处理 SSE 流
    const reader = resp.body?.getReader();
    if (!reader) throw new Error('无法读取响应流');

    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = '';
    let currentData = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6);
        } else if (line === '') {
          // 事件结束，处理数据
          if (currentEvent && currentData) {
            try {
              const data = JSON.parse(currentData);
              handleSSEvent(aiMsgId, streamComp, currentEvent, data);
              scrollToBottom();
            } catch (e) {
              console.error('SSE parse error:', e);
            }
          }
          currentEvent = '';
          currentData = '';
        }
      }
    }

    // 处理剩余的 buffer
    if (buffer.trim()) {
      if (buffer.startsWith('data: ')) {
        currentData = buffer.slice(6);
        if (currentEvent && currentData) {
          try {
            const data = JSON.parse(currentData);
            handleSSEvent(aiMsgId, streamComp, currentEvent, data);
          } catch (e) {
            console.error('SSE parse error:', e);
          }
        }
      }
    }

  } catch (err: any) {
    // 更新消息为错误状态
    const aiMsg = messages.value.find(m => m.id === aiMsgId);
    if (aiMsg) {
      aiMsg.content = `出错：${err?.message || String(err)}`;
      aiMsg.isStreaming = false;
      aiMsg.isThinking = false;
    }
  } finally {
    // 完成流式消息
    const aiMsg = messages.value.find(m => m.id === aiMsgId);
    if (aiMsg) {
      aiMsg.isStreaming = false;
      aiMsg.isThinking = false;
    }
    currentStreamMessageId.value = null;
    asking.value = false;
    scrollToBottom();
  }
}

function handleSSEvent(msgId: string, streamComp: any, event: string, data: any) {
  const aiMsg = messages.value.find(m => m.id === msgId);
  if (!aiMsg) return;

  switch (event) {
    case 'thinking':
      streamComp?.handleThinking(data);
      if (data.message) {
        aiMsg.isThinking = true;
      }
      break;

    case 'searching':
      streamComp?.handleSearching(data);
      break;

    case 'answer':
      streamComp?.handleAnswer(data);
      aiMsg.content += data.delta || '';
      break;

    case 'sources':
      streamComp?.handleSources(data);
      aiMsg.sources = data.sources || [];
      break;

    case 'done':
      streamComp?.handleDone(data);
      aiMsg.isThinking = false;
      break;

    case 'error':
      streamComp?.handleError(data);
      aiMsg.content += `\n\n错误: ${data.message}`;
      aiMsg.isThinking = false;
      break;
  }
}

function handleExampleAsk(q: string) {
  question.value = q;
  ask();
}

function clearChat() {
  messages.value = [];
  // 清理流引用
  Object.keys(streamRefs).forEach(key => {
    delete streamRefs[key];
  });
}
</script>
