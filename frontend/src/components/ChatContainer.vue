<template>
  <div class="chat-container">
    <div class="chat-header">
      <div class="chat-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span>智能问答</span>
      </div>
      <div v-if="messages.length > 0" class="message-count">{{ messages.length }} 条消息</div>
    </div>

    <div class="messages-wrapper" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
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
          <button v-for="(q, i) in examples" :key="i" class="example-btn" @click="$emit('ask', q)">
            {{ q }}
          </button>
        </div>
      </div>

      <template v-else>
        <ChatMessage
          v-for="(msg, idx) in messages"
          :key="idx"
          :role="msg.role"
          :content="msg.content"
          :sources="msg.sources"
          :timestamp="msg.timestamp"
        />
        <div v-if="isTyping" class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </template>
    </div>

    <div class="chat-footer">
      <slot name="input"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import ChatMessage from './ChatMessage.vue';

interface SourceInfo {
  source: string;
  page?: number | null;
  snippet?: string | null;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[];
  timestamp?: Date;
}

const props = defineProps<{
  messages: Message[];
  isTyping?: boolean;
}>();

const emit = defineEmits<{
  ask: [question: string];
}>();

const messagesContainer = ref<HTMLDivElement | null>(null);

const examples = [
  '这份文档的主要内容是什么？',
  '请总结一下关键要点',
  '文档中提到了哪些重要数据？',
];

watch(() => props.messages.length, () => {
  scrollToBottom();
});

function scrollToBottom() {
  nextTick(() => {
    const container = messagesContainer.value;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
}
</script>
