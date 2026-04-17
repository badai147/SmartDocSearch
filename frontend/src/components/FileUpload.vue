<template>
  <div class="upload-section">
    <div class="upload-header">
      <div class="upload-title">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="12" y1="18" x2="12" y2="12"/>
          <line x1="9" y1="15" x2="15" y2="15"/>
        </svg>
        <span>文档导入</span>
      </div>
      <p class="upload-desc">支持 PDF、Word、TXT、Markdown 格式</p>
    </div>

    <div class="upload-area" :class="{ 'drag-over': isDragOver }" @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false" @drop.prevent="handleDrop">
      <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx,.doc,.html,.pptx" @change="onFileChange" class="file-input"/>

      <div v-if="filesToUpload.length === 0" class="upload-placeholder" @click="fileInput?.click()">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="upload-text">点击或拖拽文件到此处上传</p>
        <p class="upload-hint">单个文件不超过 50MB</p>
      </div>

      <div v-else class="file-list">
        <div v-for="(file, idx) in filesToUpload" :key="idx" class="file-item">
          <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatFileSize(file.size) }}</span>
          <button class="file-remove" @click.stop="removeFile(idx)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div v-if="uploadStatus" class="upload-status" :class="{ error: hasError }">
      <svg v-if="hasError" class="status-icon error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      <svg v-else-if="uploadSuccess" class="status-icon success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <svg v-else class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      <span>{{ uploadStatus }}</span>
    </div>

    <button class="btn btn-primary" :disabled="uploading || filesToUpload.length === 0" @click="uploadDocs">
      <svg v-if="uploading" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="10"/>
      </svg>
      <span>{{ uploading ? '导入中...' : '开始导入' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  uploading: boolean;
  uploadStatus: string;
}>();

const emit = defineEmits<{
  upload: [files: File[]];
}>();

const fileInput = ref<HTMLInputElement | null>(null);
const filesToUpload = ref<File[]>([]);
const isDragOver = ref(false);

const hasError = computed(() => props.uploadStatus.includes('失败') || props.uploadStatus.includes('错误'));
const uploadSuccess = computed(() => props.uploadStatus.includes('完成') && !hasError.value);

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const list = input.files ? Array.from(input.files) : [];
  addFiles(list);
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false;
  const list = e.dataTransfer?.files ? Array.from(e.dataTransfer.files) : [];
  addFiles(list);
}

function addFiles(newFiles: File[]) {
  const validFiles = newFiles.filter(f => {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    return ['.txt', '.md', '.pdf', '.docx', '.doc', '.html', '.pptx'].includes(ext);
  });
  if (validFiles.length === 0) {
    return;
  }
  // 只保留第一个文件（单文件上传限制）
  const firstFile = validFiles[0];
  if (filesToUpload.value.some(f => f.name === firstFile.name)) {
    return; // 文件已存在
  }
  filesToUpload.value = [firstFile];
}

function removeFile(idx: number) {
  filesToUpload.value.splice(idx, 1);
}

async function uploadDocs() {
  if (filesToUpload.value.length === 0) return;
  emit('upload', [...filesToUpload.value]);
  filesToUpload.value = [];
  if (fileInput.value) fileInput.value.value = '';
}
</script>
