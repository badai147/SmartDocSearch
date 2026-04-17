<template>
  <div class="chat-input">
    <div class="input-wrapper">
      <textarea
        v-model="inputText"
        class="input-field"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="1"
        @keydown.enter.prevent="handleEnter"
        @input="autoResize"
        ref="textareaRef"
      />
      <div class="input-actions">
        <div class="top-k-selector">
          <label>引用片段:</label>
          <select v-model.number="topKValue" :disabled="disabled">
            <option v-for="n in 10" :key="n" :value="n">{{ n }}</option>
          </select>
        </div>
        <button
          class="send-btn"
          :disabled="disabled || !inputText.trim()"
          @click="send"
        >
          <svg v-if="disabled" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="10"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9"/>
          </svg>
        </button>
      </div>
    </div>
    <div class="input-footer">
      <span class="hint">按 Enter 发送，Shift + Enter 换行</span>
      <button v-if="showClear" class="clear-btn" @click="$emit('clear')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
        清空对话
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';

const props = defineProps<{
  modelValue: string;
  topK: number;
  disabled?: boolean;
  placeholder?: string;
  showClear?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  'update:topK': [value: number];
  send: [];
  clear: [];
}>();

const textareaRef = ref<HTMLTextAreaElement | null>(null);
const inputText = ref(props.modelValue);
const topKValue = ref(props.topK);

watch(() => props.modelValue, (val) => {
  inputText.value = val;
});

watch(inputText, (val) => {
  emit('update:modelValue', val);
});

watch(topKValue, (val) => {
  emit('update:topK', val);
});

function autoResize() {
  nextTick(() => {
    const el = textareaRef.value;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  });
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey) {
    inputText.value += '\n';
    autoResize();
  } else {
    send();
  }
}

function send() {
  if (!inputText.value.trim() || props.disabled) return;
  emit('send');
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto';
    }
  });
}
</script>
