# Renovate

## 简介

Renovate 是一个自动化依赖更新工具，帮助项目和团队保持依赖的最新状态。它支持多种包管理器和平台，包括 npm、yarn、pnpm、pip、Docker、GitHub、GitLab 等。

## OHOS 适配

### 适配要点

1. **Node.js 版本要求**：官方要求 Node.js ^20.15.1 或 ^22.11.0，鸿蒙系统使用 v24.13.0（超出官方范围，需注意兼容性）
2. **包管理器**：使用 pnpm 10.7.1，与官方要求一致
3. **原生模块 re2**：re2 是可选依赖（optionalDependencies），编译失败后会自动回退到 RegExp，不影响核心功能
4. **编译流程**：
   - `pnpm install --frozen-lockfile --ignore-scripts`（安装依赖，忽略原生模块编译）
   - `pnpm build`（编译 TypeScript 到 dist/）
   - 可能遇到 tsx pipe 文件权限问题，但不影响主要编译产物

### 已知问题

1. **re2 模块编译失败**：re2 是 C++ 原生模块，在鸿蒙上编译可能失败。这是预期行为，renovate 会自动回退到 RegExp
2. **create-json-schema 步骤失败**：tsx 工具尝试创建 pipe 文件，可能因权限问题失败。但 dist/ 目录已生成，不影响使用
3. **版本显示**：package.json 版本字段为 "0.0.0-semantic-release"，实际版本需从 Git tag 或其他方式获取

## 依赖

### 编译依赖

- Node.js 24.13.0+
- pnpm 10.7.1+

### 运行依赖

- Node.js 运行时
- 生产依赖（约 100+ npm 包）

## 功能验证

```bash
# 验证版本
node dist/renovate.js --version
# 输出：0.0.0-semantic-release

# 验证配置
node dist/config-validator.js --help
```

## 参考

- 官网：https://renovatebot.com
- GitHub：https://github.com/renovatebot/renovate
- 文档：https://docs.renovatebot.com