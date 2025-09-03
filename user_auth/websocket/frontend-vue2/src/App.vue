<template>
  <div class="wrap">
    <h2>WebSocket 实时进度演示</h2>

    <div class="row">
      <label>进度：</label>
      <input type="range" min="0" max="100" v-model.number="percent" @input="sendPercent" />
      <span class="label">{{ percent }}%</span>
      <button @click="togglePlay">{{ playing ? "暂停" : "播放" }}</button>
    </div>

    <div class="row">
      <label>窗口（秒）</label>
      <input type="number" v-model.number="windowSec" min="1" max="120" @change="sendPercent" />
      <span class="status" :class="{ on: connected }">{{ connected ? "WS已连接" : "WS未连接" }}</span>
    </div>

    <div class="panel">
      <h3>当前点</h3>
      <pre>{{ point | pretty }}</pre>
    </div>

    <div class="panel">
      <h3>窗口数据（{{windowSec}}s）</h3>
      <pre>{{ series | pretty }}</pre>
    </div>
  </div>
</template>

<script>
import { connectWS } from "./ws";

export default {
  data() {
    return {
      ws: null,
      connected: false,
      percent: 0,
      windowSec: 10,
      playing: false,
      tick: null,
      point: null,
      series: [],
      wsError: null // 添加错误信息字段
    };
  },
  filters: {
    pretty(v){ return JSON.stringify(v, null, 2); }
  },
  created() {
    // 在 K8s/Ingress 下：ws(s)://<host>/ws/data/
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    // 修改为使用当前主机和Ingress配置的路径
    const url = `${proto}://${window.location.host}/ws/data/`;
    console.log(`[Frontend] 尝试连接 WebSocket: ${url}`);
    this.ws = connectWS(url, {
      onOpen: () => { 
        console.log(`[Frontend] WebSocket 连接已建立`);
        this.connected = true; 
        this.wsError = null; // 连接成功时清空错误
        this.sendPercent(); 
      },
      onClose: () => { 
        console.log(`[Frontend] WebSocket 连接已关闭`);
        this.connected = false; 
        // 如果有错误信息，保留显示；否则显示连接关闭
        if (!this.wsError) {
          this.wsError = "WebSocket 连接已关闭";
        }
      },
      onMessage: (msg) => {
        console.log(`[Frontend] 收到服务器消息:`, msg);
        
        // 修改消息处理逻辑，适配后端返回的数据格式
        if (typeof msg === 'object') {
          // 检查是否是后端返回的错误消息
          if (msg.error) {
            console.error("[Frontend] 服务器错误:", msg.error);
            this.wsError = `服务器错误: ${msg.error}`;
            return;
          }
          
          // 处理后端返回的数据格式
          if (msg.data && Array.isArray(msg.data)) {
            // 从data数组中提取当前点和窗口数据
            this.series = msg.data;
            // 取最后一个数据点作为当前点
            this.point = msg.data.length > 0 ? msg.data[msg.data.length - 1] : null;
            console.log(`[Frontend] 更新数据 - 当前点:`, this.point, `窗口数据点数:`, this.series.length);
          } else {
            console.warn(`[Frontend] 未找到有效的数据字段:`, msg);
          }
        } else {
          console.error(`[Frontend] 接收到非对象格式的消息:`, msg);
        }
      },
      onError: (error) => { // 添加错误处理回调
        console.error("[Frontend] WebSocket 连接错误:", error);
        // 根据错误事件类型提供更具体的错误信息
        let errorMsg = "WebSocket 连接失败";
        if (error.code === 1006) {
          errorMsg = "连接被意外关闭，请检查网络或服务器状态";
        } else if (error.message) {
          errorMsg = `连接错误: ${error.message}`;
        }
        this.wsError = errorMsg;
      }
    });
  },
  beforeDestroy() {
    console.log(`[Frontend] 组件即将销毁，清理资源`);
    if (this.tick) clearInterval(this.tick);
    if (this.ws) this.ws.close();
  },
  methods: {
    sendPercent() {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        console.log(`[Frontend] WebSocket 未连接，无法发送数据`);
        return;
      }
      const data = {
        progress: this.percent,
        window_sec: this.windowSec
      };
      console.log(`[Frontend] 发送进度数据:`, data);
      this.ws.send(JSON.stringify(data));
    },
    togglePlay() {
      this.playing = !this.playing;
      console.log(`[Frontend] 切换播放状态: ${this.playing ? '播放' : '暂停'}`);
      if (this.playing) {
        this.tick = setInterval(() => {
          this.percent = (this.percent + 1) % 101;
          this.sendPercent();
        }, 1000);
      } else {
        if (this.tick) clearInterval(this.tick);
        this.tick = null;
      }
    }
  }
};
</script>

<template>
  <div class="wrap">
    <h2>WebSocket 实时进度演示</h2>

    <div class="row">
      <label>进度：</label>
      <input type="range" min="0" max="100" v-model.number="percent" @input="sendPercent" />
      <span class="label">{{ percent }}%</span>
      <button @click="togglePlay">{{ playing ? "暂停" : "播放" }}</button>
    </div>

    <div class="row">
      <label>窗口（秒）</label>
      <input type="number" v-model.number="windowSec" min="1" max="120" @change="sendPercent" />
      <span class="status" :class="{ on: connected }">
        {{ connected ? "WS已连接" : "WS未连接" }}
      </span>
    </div>
    
    <!-- 添加错误信息显示区域 -->
    <div v-if="wsError" class="error-message">
      <strong>错误信息：</strong>{{ wsError }}
    </div>

    <div class="panel">
      <h3>当前点</h3>
      <pre>{{ point | pretty }}</pre>
    </div>

    <div class="panel">
      <h3>窗口数据（{{windowSec}}s）</h3>
      <pre>{{ series | pretty }}</pre>
    </div>
  </div>
</template>

<style>
.wrap { max-width: 900px; margin: 24px auto; font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial; }
.row { display:flex; align-items:center; gap:12px; margin:12px 0; }
.label { width:60px; text-align:right; }
.panel { background:#f7f7f8; border:1px solid #e5e7eb; padding:12px; border-radius:8px; margin-top:12px; }
.status { padding:2px 8px; border-radius:12px; background:#eee; }
.status.on { background:#d1fae5; }
button { padding:6px 12px; cursor:pointer; }
.error-message { color:#dc2626; background:#fee2e2; padding:8px 12px; border-radius:4px; margin:8px 0; font-size:14px; }
</style>
