<template>
  <div class="stream-message" :class="{ assistant: role === 'assistant' }">
    <div class="message-avatar">
      <svg v-if="role === 'user'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <line x1="12" y1="8" x2="12" y2="16"/>
        <line x1="8" y1="12" x2="16" y2="12"/>
      </svg>
    </div>
    <div class="message-content">
      <div class="message-header">
        <span class="message-author">{{ role === 'user' ? '你' : 'AI 助手' }}</span>
        <span v-if="timestamp" class="message-time">{{ formatTime(timestamp) }}</span>
      </div>

      <!-- 思考过程展示 -->
      <ThinkingStream
        v-if="role === 'assistant'"
        ref="thinkingStreamRef"
        :is-thinking="isThinking"
      />

      <!-- 答案内容 -->
      <div class="message-body" v-html="formatContent(content)"></div>

      <!-- 参考来源 -->
      <div v-if="sources && sources.length > 0" class="message-sources">
        <div class="sources-header" @click="showSources = !showSources">
          <svg :class="{ rotate: showSources }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
          <span>参考来源 ({{ sources.length }})</span>
        </div>
        <div v-show="showSources" class="sources-list">
          <div v-for="(s, i) in sources.slice(0, 6)" :key="i" class="source-item">
            <span class="source-number">{{ i + 1 }}</span>
            <div class="source-info">
              <div class="source-title">{{ s.source }}</div>
              <div v-if="s.snippet" class="source-snippet">{{ s.snippet }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ThinkingStream from './ThinkingStream.vue';

interface SourceInfo {
  source: string;
  page?: number | null;
  snippet?: string | null;
}

const props = defineProps<{
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[];
  timestamp?: Date;
  isThinking?: boolean;
}>();

const emit = defineEmits<{
  thinkingEvent: [data: any];
  answerEvent: [data: any];
  doneEvent: [data: any];
}>();

const showSources = ref(false);
const thinkingStreamRef = ref<InstanceType<typeof ThinkingStream> | null>(null);

function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function formatContent(text: string): string {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

// SSE 事件处理，暴露给父组件
function handleThinking(data: any) {
  thinkingStreamRef.value?.handleThinking(data);
}

function handleSearching(data: any) {
  thinkingStreamRef.value?.handleSearching(data);
}

function handleAnswer(data: any) {
  thinkingStreamRef.value?.handleAnswer(data);
}

function handleSources(data: any) {
  thinkingStreamRef.value?.handleSources(data);
}

function handleDone(data: any) {
  thinkingStreamRef.value?.handleDone(data);
}

function handleError(data: any) {
  thinkingStreamRef.value?.handleError(data);
}

function reset() {
  thinkingStreamRef.value?.reset();
  showSources.value = false;
}

defineExpose({
  handleThinking,
  handleSearching,
  handleAnswer,
  handleSources,
  handleDone,
  handleError,
  reset
});
</script>

<style scoped>
.stream-message {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.03);
}

.stream-message.assistant {
  background: rgba(16, 185, 129, 0.03);
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #e2e8f0;
}

.stream-message:not(.assistant) .message-avatar {
  background: #dbeafe;
}

.stream-message.assistant .message-avatar {
  background: #d1fae5;
}

.message-avatar svg {
  width: 18px;
  height: 18px;
  color: #64748b;
}

.stream-message.assistant .message-avatar svg {
  color: #059669;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.message-author {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.message-time {
  font-size: 11px;
  color: #94a3b8;
}

.message-body {
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  word-break: break-word;
}

.message-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-body :deep(code) {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.message-body :deep(strong) {
  font-weight: 600;
  color: #1e293b;
}

.message-sources {
  margin-top: 12px;
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  user-select: none;
}

.sources-header svg {
  width: 14px;
  height: 14px;
  transition: transform 0.2s ease;
}

.sources-header svg.rotate {
  transform: rotate(180deg);
}

.sources-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.source-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  color: white;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.source-info {
  flex: 1;
  min-width: 0;
}

.source-title {
  font-size: 12px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 2px;
}

.source-snippet {
  font-size: 11px;
  color: #64748b;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
