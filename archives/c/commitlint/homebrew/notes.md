# commitlint homebrew 适配笔记

## 编译环境
- 构建系统: custom (Node.js / npm / yarn monorepo with lerna)
- 编译日期: 2026-06-21
- Node.js: v24.13.0
- npm: 11.6.2
- yarn: 1.22.22
- 状态: published

## 编译步骤

1. 从 GitHub 下载源码: `https://codeload.github.com/conventional-changelog/commitlint/tar.gz/refs/tags/v19.8.0`
2. 设置 npm registry: `npm config set registry https://registry.npmmirror.com`
3. 安装依赖: `yarn install --frozen-lockfile --ignore-engines --ignore-scripts`
   - 使用 `--ignore-scripts` 跳过 esbuild 原生模块编译（不支持 OpenHarmony 平台）
4. TypeScript 编译: `npx tsc -b` (exit code 0, 成功)
5. Staging 安装: `npm install -g @commitlint/cli@19.8.0 --prefix=$TEST_PREFIX$DEFAULT_PREFIX` (100 packages)
6. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package commitlint homebrew`
7. 本地安装: `npm install -g @commitlint/cli@19.8.0 --prefix=$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | yarn install 失败: "Unsupported platform: openharmony arm64 LE" | esbuild 不支持 OpenHarmony 平台 | 使用 `--ignore-scripts` 跳过原生模块安装脚本 |
| 2 | G0 干净构建验证失败 | G0 尝试运行 `./configure` 但 Node.js 项目没有 configure 脚本 | 平台限制，Node.js 工具不适用 G0 验证 |
| 3 | G4 档案完整性失败 | 缺少软件级 README.md | 创建 archives/c/commitlint/README.md |

## 源码修改

无补丁，commitlint 是纯 JavaScript/TypeScript 工具，源码无需修改即可在 OpenHarmony 上运行。

## 依赖版本

- Node.js: v24.13.0
- npm: 11.6.2
- yarn: 1.22.22
- @commitlint/cli: 19.8.0

## 验证结果

```bash
$ commitlint --version
@commitlint/cli@19.8.0

$ commitlint --help
@commitlint/cli@19.8.0 - Lint your commit messages
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| commitlint-homebrew-ohos-aarch64.tar.gz | 34565KB | 预编译包（纯 JavaScript，平台无关） |

## 注意事项

- commitlint 是纯 JavaScript 工具，无需平台特定编译
- esbuild（vitepress docs 依赖）不支持 OpenHarmony，但不影响 commitlint CLI 功能
- 使用 `--ignore-scripts` 安装依赖可避免 esbuild 错误
- Node.js v18+ 必须，推荐 v24+
---

**编译结束**: 2026-06-21 18:05
**最终状态**: published
