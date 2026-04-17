<template>
  <div class="thinking-stream" :class="{ collapsed: !expanded }">
    <div class="thinking-header" @click="toggleExpand">
      <div class="thinking-title">
        <svg class="thinking-icon" :class="{ spinning: isThinking }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6l4 2"/>
        </svg>
        <span>{{ currentStageLabel }}</span>
      </div>
      <svg class="expand-icon" :class="{ rotated: expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </div>

    <div v-show="expanded" class="thinking-content">
      <!-- 思考阶段 -->
      <div v-if="thinkingSteps.length > 0" class="thinking-steps">
        <div
          v-for="(step, idx) in thinkingSteps"
          :key="idx"
          class="thinking-step"
          :class="step.type"
        >
          <div class="step-indicator">
            <svg v-if="step.type === 'done'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span v-else-if="step.type === 'active'">•</span>
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <div class="step-content">
            <div class="step-header">{{ step.label }}</div>
            <div v-if="step.message" class="step-message">{{ step.message }}</div>
            <div v-if="step.thinking" class="step-thinking" v-html="formatThinking(step.thinking)"></div>
          </div>
        </div>
      </div>

      <!-- 当前处理中 -->
      <div v-if="isThinking" class="current-processing">
        <div class="processing-dots">
          <span></span><span></span><span></span>
        </div>
        <span>{{ currentMessage }}</span>
      </div>

      <!-- 检索阶段 -->
      <div v-if="searchingMessage" class="searching-status">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <span>{{ searchingMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

interface ThinkingStep {
  type: 'pending' | 'active' | 'done';
  label: string;
  message?: string;
  thinking?: string;
}

interface SourceInfo {
  source: string;
  page?: number | null;
  snippet?: string | null;
}

interface SSEThinkingData {
  stage?: string;
  message?: string;
  thinking?: string | null;
  rewrite_time?: number;
}

interface SSESearchingData {
  message?: string;
  query_count?: number;
}

interface SSEAnswerData {
  delta: string;
  is_first?: boolean;
}

interface SSESourcesData {
  sources: SourceInfo[];
  count: number;
}

interface SSEDoneData {
  total_time: number;
  source_count: number;
  answer_length: number;
}

interface SSEErrorData {
  message: string;
  code: string;
}

const props = defineProps<{
  isThinking?: boolean;
}>();

const expanded = ref(true);
const thinkingSteps = ref<ThinkingStep[]>([
  { type: 'pending', label: '问题分析' },
  { type: 'pending', label: '文档检索' },
  { type: 'pending', label: '生成回答' }
]);

const currentStage = ref(0); // 0: thinking, 1: searching, 2: answer
const currentMessage = ref('');
const searchingMessage = ref('');

const currentStageLabel = computed(() => {
  if (props.isThinking) {
    return ['正在分析问题...', '正在检索文档...', '正在生成回答...'][currentStage.value] || '处理中...';
  }
  return '思考过程';
});

function toggleExpand() {
  expanded.value = !expanded.value;
}

// SSE 事件处理器
function handleThinking(data: SSEThinkingData) {
  if (data.stage === 'query_rewrite') {
    thinkingSteps.value[0] = {
      type: 'active',
      label: '问题分析',
      message: data.message
    };
    currentStage.value = 0;
    currentMessage.value = data.message || '';
  } else if (data.stage === 'query_rewrite_done') {
    thinkingSteps.value[0] = {
      type: 'done',
      label: '问题分析完成',
      message: data.message,
      thinking: data.thinking
    };
    currentMessage.value = '';
  } else if (data.stage === 'no_sources') {
    thinkingSteps.value[1] = {
      type: 'done',
      label: '文档检索',
      message: data.message,
      thinking: data.thinking
    };
  }
}

function handleSearching(data: SSESearchingData) {
  thinkingSteps.value[1] = {
    type: 'active',
    label: '文档检索',
    message: data.message
  };
  currentStage.value = 1;
  searchingMessage.value = data.message || '';
  currentMessage.value = '';
}

function handleAnswer(data: SSEAnswerData) {
  if (data.is_first) {
    thinkingSteps.value[2] = {
      type: 'active',
      label: '生成回答'
    };
    currentStage.value = 2;
    searchingMessage.value = '';
  }
}

function handleSources(data: SSESourcesData) {
  thinkingSteps.value[2] = {
    type: 'done',
    label: '回答生成完成'
  };
  searchingMessage.value = '';
  currentMessage.value = '';
}

function handleDone(data: SSEDoneData) {
  currentMessage.value = '';
  searchingMessage.value = '';
}

function handleError(data: SSEErrorData) {
  currentMessage.value = `错误: ${data.message}`;
}

function reset() {
  thinkingSteps.value = [
    { type: 'pending', label: '问题分析' },
    { type: 'pending', label: '文档检索' },
    { type: 'pending', label: '生成回答' }
  ];
  currentStage.value = 0;
  currentMessage.value = '';
  searchingMessage.value = '';
}

function formatThinking(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
    .replace(/• /g, '• ');
}

// 暴露方法给父组件
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
.thinking-stream {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 12px;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  background: rgba(59, 130, 246, 0.05);
}

.thinking-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.thinking-icon {
  width: 16px;
  height: 16px;
  color: #3b82f6;
}

.thinking-icon.spinning {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.expand-icon {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  transition: transform 0.2s ease;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.thinking-content {
  padding: 12px 14px;
  border-top: 1px solid #e2e8f0;
}

.thinking-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.thinking-step {
  display: flex;
  gap: 10px;
}

.step-indicator {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  background: #e2e8f0;
  color: #64748b;
}

.thinking-step.pending .step-indicator {
  background: #f1f5f9;
  color: #94a3b8;
}

.thinking-step.active .step-indicator {
  background: #dbeafe;
  color: #3b82f6;
}

.thinking-step.done .step-indicator {
  background: #dcfce7;
  color: #22c55e;
}

.thinking-step.done .step-indicator svg {
  width: 12px;
  height: 12px;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-header {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 2px;
}

.step-message {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.step-thinking {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}

.current-processing {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
}

.processing-dots {
  display: flex;
  gap: 3px;
}

.processing-dots span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
  animation: pulse 1.4s ease-in-out infinite;
}

.processing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.processing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes pulse {
  0%, 80%, 100% { opacity: 0.4; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.searching-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
  padding: 8px 0;
}

.search-icon {
  width: 14px;
  height: 14px;
  animation: search-pulse 1s ease-in-out infinite;
}

@keyframes search-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
</style>
