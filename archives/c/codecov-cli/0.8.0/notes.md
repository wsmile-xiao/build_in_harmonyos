# codecov-cli 0.8.0 适配笔记

## 编译环境
- 构建系统: custom (Node.js + TypeScript)
- 编译日期: 2026-05-27
- 编译器: N/A (Node.js/TypeScript project)
- 状态: built

## 编译步骤

1. 源码已解压到 ~/tmp/builds/codecov-cli-0.8.0.work/
2. 安装全部依赖（含devDependencies）: `npm install --ignore-scripts`
3. 编译TypeScript: `npm run build` (tsc --build)
4. 剔除开发依赖: `npm prune --omit=dev`
5. 创建staging安装:
   - 复制 dist/ 到 $DEFAULT_PREFIX/share/codecov-cli/
   - 复制 node_modules/ 到 $DEFAULT_PREFIX/share/codecov-cli/
   - 复制 package.json 到 $DEFAULT_PREFIX/share/codecov-cli/
   - 创建 bin/codecov shell wrapper脚本
6. 验证: `codecov --version` 输出 `0.8.0`
7. 打包: ohc-run.py package codecov-cli 0.8.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub预编译aarch64二进制下载极慢(19KB/s) | 网络限制 | 改用本地npm/tsc构建+shell wrapper |
| 2 | npm install husky失败 | prepare脚本需要husky | 使用 --ignore-scripts 跳过 |
| 3 | tsc未安装 | devDependencies未安装 | 先npm install全部，再npm prune |

## 源码修改

- 0001-npm-shrinkwrap.json.patch: 修复 npm-shrinkwrap.json 中的 peer dependency 声明，移除 ts-node 等 optional peer 依赖项，确保 npm install 在 HarmonyOS 上正常工作

## 依赖版本

- Node.js: v24.13.0 (/data/service/hnp/bin/node)
- npm: 11.6.2
- TypeScript: (via npm devDependency)

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/codecov --version
0.8.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| codecov-cli-0.8.0-ohos-aarch64.tar.gz | 4940KB | Release包(bin/codecov + share/codecov-cli/) |
| codecov-cli-0.8.0-ohos-aarch64-debug.tar.gz | 10KB | Debug包(Node.js项目无ELF debug symbols) |

## 注意事项

- codecov-cli实际是codecov/uploader项目，是代码覆盖率上传工具
- 此项目是Node.js/TypeScript CLI工具，非传统C/C++项目
- 运行依赖系统Node.js (/data/service/hnp/bin/node)
- bin/codecov是shell wrapper脚本，不是ELF二进制
- NODE_PATH环境变量需要包含codecov-cli的node_modules路径
---

**编译结束**: 2026-08-06 04:18
**最终状态**: built
