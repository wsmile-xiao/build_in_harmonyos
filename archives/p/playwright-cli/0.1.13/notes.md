# playwright-cli 0.1.13 适配笔记

## 编译环境
- 构建系统: npm (Node.js package)
- 编译日期: 2026-06-08
- Node.js 版本: v24.13.0
- npm 版本: 10.x
- 状态: published

## 编译步骤

由于 playwright-cli 是一个 npm 包，不需要传统意义上的编译。主要步骤如下：

1. 下载 npm 包：`npm pack @playwright/cli@0.1.13`
2. 全局安装：`npm install -g playwright-cli-0.1.13.tgz`
3. 验证安装：`playwright-cli --version` → 0.1.13

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | "Unsupported platform: openharmony" | playwright-core 只支持 linux/darwin/win32，不认识 openharmony 平台 | 修改 playwright-core/lib/tools/cli-client/registry.js，添加 openharmony 支持（视为 linux） |
| 2 | 同上，另一个文件报错 | serverRegistry.js 也需要修改 | 修改 playwright-core/lib/serverRegistry.js，添加 openharmony 支持 |

## 源码修改

修改了两个文件以支持 openharmony 平台：

1. `node_modules/playwright-core/lib/tools/cli-client/registry.js`
   - 在第 128 行后添加：`if (process.platform === "openharmony") localCacheDir = ...`
   - 将 openharmony 视为 linux，使用 XDG_CACHE_HOME 或 ~/.cache 作为缓存目录

2. `node_modules/playwright-core/lib/serverRegistry.js`
   - 在第 7286 行附近添加：`if (process.platform === "openharmony") return ...`
   - 同样将 openharmony 视为 linux

补丁文件：0001-add-openharmony-platform-support.patch

## 依赖版本

- playwright: 1.61.0-alpha-1778188671000
- playwright-core: 1.61.0-alpha-1778188671000
- Node.js: >= 18

## 验证结果

```bash
$ playwright-cli --version
0.1.13

$ playwright-cli list
(no browsers)
```

## 交付物

由于是 npm 包，交付物为已安装的包：
- 位置：~/.opendesk/interpreters/npm-global/lib/node_modules/@playwright/cli/
- 可执行文件：playwright-cli

## 注意事项

1. playwright-cli 是浏览器自动化工具，需要在 openharmony 上安装浏览器驱动才能完整使用
2. 此补丁仅解决了平台检测问题，可能还需要处理浏览器驱动下载和安装的问题
3. 修改直接应用于已安装的 npm 包，如需重新安装，需要重新应用补丁
---

**编译结束**: 2026-06-08 17:43
**最终状态**: built
