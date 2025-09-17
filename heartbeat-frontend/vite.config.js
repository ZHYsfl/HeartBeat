import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isProduction = mode === 'production'
  
  return {
    plugins: [
      vue(),
      // 只在开发环境启用devtools
      !isProduction && vueDevTools(),
    ].filter(Boolean),
    
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
    
    // 生产环境优化
    build: {
      // 输出目录
      outDir: 'dist',
      // 生成sourcemap用于调试
      sourcemap: !isProduction,
      // 压缩代码
      minify: isProduction ? 'terser' : false,
      // Terser压缩选项
      terserOptions: isProduction ? {
        compress: {
          drop_console: true, // 移除console.log
          drop_debugger: true, // 移除debugger
        },
      } : {},
      // 代码分割
      rollupOptions: {
        output: {
          // 分离vendor代码
          manualChunks: {
            vendor: ['vue', 'vue-router'],
            vant: ['vant'],
          },
          // 文件命名
          chunkFileNames: 'js/[name]-[hash].js',
          entryFileNames: 'js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name.split('.')
            const ext = info[info.length - 1]
            if (/\.(mp4|webm|ogg|mp3|wav|flac|aac)(\?.*)?$/i.test(assetInfo.name)) {
              return `media/[name]-[hash].${ext}`
            }
            if (/\.(png|jpe?g|gif|svg)(\?.*)?$/i.test(assetInfo.name)) {
              return `images/[name]-[hash].${ext}`
            }
            if (ext === 'css') {
              return `css/[name]-[hash].${ext}`
            }
            return `assets/[name]-[hash].${ext}`
          },
        },
      },
      // 设置chunk大小警告限制
      chunkSizeWarningLimit: 1000,
    },
    
    // 开发服务器配置
    server: {
      host: '0.0.0.0',
      port: 5173,
      // API代理
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/static': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    
    // 预览服务器配置
    preview: {
      host: '0.0.0.0',
      port: 4173,
    },
    
    // 环境变量
    define: {
      __VUE_PROD_DEVTOOLS__: false,
    },
  }
})
