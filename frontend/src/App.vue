<template>
  <div class="container">
    <h2 style="margin: 0 0 16px">智能文档问答助手</h2>

    <div class="panel" style="margin-bottom: 16px">
      <div class="row" style="justify-content: space-between">
        <div>
          <div style="font-weight: 600; margin-bottom: 16px; font-size: 20px;">文档导入</div>
          <div style="font-size: 20px; color: #6b7280">
            支持格式：txt / md / pdf。导入后即可问答。
          </div>
        </div>
        <div class="row">
          <input
            class="btn"
            type="file"
            multiple
            accept=".txt,.md,.pdf"
            @change="onFileChange"
          />
          <button class="btn" :disabled="uploading || filesToUpload.length === 0" @click="uploadDocs">
            {{ uploading ? "导入中..." : "开始导入" }}
          </button>
        </div>
      </div>

      <div style="margin-top: 10px; font-size: 20px; color: #6b7280">
        {{ uploadStatus }}
      </div>
    </div>

    <div class="panel">
      <div style="font-weight: 600; margin-bottom: 10px; font-size: 20px;">对话</div>
      <div class="messages">
        <div v-for="(m, idx) in messages" :key="idx" class="msg" :class="m.role === 'user' ? 'msg-user' : 'msg-assistant'">
          <div style="font-size: 20px; color: #6b7280; margin-bottom: 6px">
            {{ m.role === "user" ? "你" : "助手" }}
          </div>
          <div style="white-space: pre-wrap">{{ m.content }}</div>

          <div v-if="m.role === 'assistant' && m.sources && m.sources.length" class="sources">
            <div style="margin-bottom: 6px">来源片段：</div>
            <div v-for="(s, i) in m.sources.slice(0, 6)" :key="i">
              {{ s.source }}{{ s.page !== null && s.page !== undefined ? ` (page=${s.page})` : "" }}
              <span v-if="s.snippet">：{{ s.snippet }}</span>
            </div>
          </div>
        </div>
      </div>

      <div style="margin-top: 14px; font-size: 20px;" class="row">
        <textarea
          v-model="question"
          class="textarea"
          placeholder="输入你的问题，例如：‘这份文档讲了什么？’"
        ></textarea>
      </div>

      <div style="margin-top: 12px" class="row">
        <div class="row" style="gap: 8px">
          <span style="font-size: 20px; color: #6b7280">返回片段数</span>
          <input
            class="btn"
            style="width: 90px; text-align: center"
            type="number"
            min="1"
            max="20"
            v-model.number="topK"
          />
        </div>

        <div style="margin-left: auto" class="row">
          <button class="btn" :disabled="asking || !question.trim()" @click="ask">
            {{ asking ? "生成中..." : "发送问题" }}
          </button>
          <button class="btn" :disabled="asking" @click="clearChat">清空</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

type SourceInfo = {
  source: string;
  page?: number | null;
  snippet?: string | null;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
};

const filesToUpload = ref<File[]>([]);
const uploading = ref(false);
const uploadStatus = ref("尚未导入文档。");

const messages = ref<Message[]>([]);
const question = ref("");
const topK = ref(6);
const asking = ref(false);

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const list = input.files ? Array.from(input.files) : [];
  filesToUpload.value = list;
}

async function uploadDocs() {
  if (filesToUpload.value.length === 0) return;
  uploading.value = true;
  uploadStatus.value = "上传中...";

  try {
    const formData = new FormData();
    for (const f of filesToUpload.value) formData.append("files", f);

    const resp = await fetch("/api/docs/ingest", {
      method: "POST",
      body: formData,
    });

    const data = await resp.json().catch(() => null);
    if (!resp.ok) {
      throw new Error(data?.detail?.failed_files ? JSON.stringify(data.detail) : data?.detail || resp.statusText);
    }

    const ok = data?.ingested_files || [];
    const failed = data?.failed_files || [];
    uploadStatus.value = `导入完成：${ok.length} 个文件，失败：${failed.length} 个文件。`;
    filesToUpload.value = [];
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
  const userMsg: Message = { role: "user", content: q };
  messages.value.push(userMsg);
  question.value = "";

  try {
    const resp = await fetch("/api/chat/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, top_k: topK.value }),
    });

    const data = await resp.json().catch(() => null);
    if (!resp.ok) {
      throw new Error(data?.detail || resp.statusText);
    }

    const answer = (data?.answer as string) ?? "";
    const sources = (data?.sources as SourceInfo[] | undefined) ?? [];
    messages.value.push({
      role: "assistant",
      content: answer,
      sources,
    });
  } catch (err: any) {
    messages.value.push({
      role: "assistant",
      content: `出错：${err?.message || String(err)}`,
    });
  } finally {
    asking.value = false;
  }
}

function clearChat() {
  messages.value = [];
}
</script>

