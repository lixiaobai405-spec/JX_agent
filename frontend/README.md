# JX-Agent 前端应用

基于 React + TypeScript + Vite 构建的绩效管理系统前端。

## 环境要求

- Node.js >= 18.0.0
- npm >= 9.0.0

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发环境运行

```bash
npm run dev
```

默认运行在 `http://localhost:5173`

### 生产环境构建

```bash
npm run build
```

构建产物输出到 `dist/` 目录

### 预览生产构建

```bash
npm run preview
```

## 生产环境部署

### 方式一：使用 Nginx

1. 构建项目：
```bash
npm run build
```

2. 将 `dist/` 目录内容部署到 Nginx 静态目录：
```bash
cp -r dist/* /usr/share/nginx/html/
```

3. Nginx 配置示例 (`/etc/nginx/conf.d/jx-agent.conf`)：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. 重启 Nginx：
```bash
nginx -s reload
```

### 方式二：使用 Docker

1. 创建 `Dockerfile`：
```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

2. 构建并运行：
```bash
docker build -t jx-agent-frontend .
docker run -d -p 80:80 jx-agent-frontend
```

### 方式三：使用静态托管服务

部署到 Vercel / Netlify / GitHub Pages：

```bash
npm run build
# 将 dist/ 目录上传到托管平台
```

注意配置路由重写规则，确保 SPA 路由正常工作。

## 环境配置

### 后端 API 配置

后端 API 基础路径配置在 `src/api/client.ts`，默认为 `/api/v1`。开发环境通过 `vite.config.ts` 将 `/api` 代理到 `http://localhost:8000`。

### 开发服务器配置

在 `vite.config.ts` 中配置：

```typescript
server: {
  host: '0.0.0.0',           // 监听所有网络接口
  port: 5173,                // 端口号
  allowedHosts: ['jx.yiriso.fun'],  // 允许的域名
  proxy: {
    '/api': 'http://localhost:8000',  // API 代理
  },
}
```

## 技术栈

- React 19 + TypeScript
- Vite (构建工具)
- TailwindCSS (样式)
- React Router (路由)
- Axios (HTTP 客户端)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
