<template>
  <div class="message" :class="role">
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
      <div class="message-body" v-html="formatContent(content)"></div>

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
}>();

const showSources = ref(false);

function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function formatContent(text: string): string {
  // Simple markdown-like formatting
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
</script>
