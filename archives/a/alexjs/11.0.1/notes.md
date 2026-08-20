# alexjs 11.0.1 适配笔记

## 编译环境
- 构建系统: custom（npm / Node.js ESM 应用）
- 编译日期: 2026-08-19
- 运行时: node v24.13.0（/data/service/hnp/node.org/node_v24.13.0）
- 状态: built

## 编译步骤

1. 源码：npm registry 官方 tarball `alex-11.0.1.tgz`（get-alex/alex 上游，纯 JS ESM：index.js/cli.js/filter.js）
2. `node npm-cli.js install --ignore-scripts --no-audit --no-fund --no-package-lock --no-save` — 完整安装依赖（含 dev 依赖供测试，1001 包）
3. 上游测试：`NODE_OPTIONS=--jitless --no-deprecation node test/index.js` — 47/47 全部通过（tape：test/api.js + test/cli.js）
4. 打包：源码 + node_modules 全部进 `libexec/alexjs/`，`bin/alex` launcher 以 `env -i` 干净环境 + `node --jitless` 运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | hnp 的 `npm` wrapper 每次调用崩溃（Signal 5，V8 `Check failed: 12 == (*__errno_location())`） | hnp node 自带 npm wrapper 在 OHOS 上损坏；/data/service/hnp/lib 为空、npm-cli.js 需经 node 直接调用 | 定位 `<node 前缀>/lib/node_modules/npm/bin/npm-cli.js`，`node npm-cli.js` 直接调用；`NODE_OPTIONS=--jitless` 规避 V8 errno DCHECK |
| 2 | 首次 `npm install --omit=dev` 后 `supports-color` 缺失（chalk/debug/vfile-reporter 的传递依赖） | OHOS 上 npm 的 omit/prune 对传递依赖处理有误 | 不做 --omit=dev/prune，完整安装并整树打包 node_modules |
| 3 | 上游测试 `custom formatter that isn't installed` 失败 | Node v24 的 `DEP0180: fs.Stats constructor is deprecated` 警告污染 stderr，与测试期望的精确 stderr 不符 | 测试环境 `NODE_OPTIONS=--no-deprecation` 抑制（仅测试环境，不改上游代码） |
| 4 | 上游测试 `profanity (default)` 失败 | 最初从 GitHub API 拉 fixtures 时误下载了 404 页（`profanity/.alexrc` 上游目录并不存在，是我方误建） | 按上游目录真实文件清单对齐 fixtures，删除误建文件 |
| 5 | node 继承 OHOS 特定环境变量（AppSpawn/ALACRITTY/UBSAN 等）时可能 Signal 5 崩溃 | 同 aicommits/acorn 先例 | launcher 用 `env -i PATH/HOME/TMPDIR` 干净环境执行 |

## 源码修改

无（无补丁，上游源码未改动；上游测试文件 test/ 目录随配方携带用于 build 内验证）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| node | 24.13.0 | hnp 预装运行时，launcher 经 PATH 调用 |
| npm | 11.6.2 | npm-cli.js 直接调用（wrapper 损坏） |
| 运行时 npm 包 | 21 个直接依赖 | meow/rehype-parse/remark-*/retext-*/unified/vfile 等，随 node_modules 整树打包 |
| 测试依赖 | tape 等 dev 包 | 仅 build 内测试使用，随 node_modules 打包（不 prune，见问题 #2） |

## 验证结果

```bash
node npm-cli.js install ...            # 完整安装 1001 包
NODE_OPTIONS=--jitless --no-deprecation node test/index.js   # 上游测试 47/47 PASS
echo "The boogeyman is a he." | bin/alex --stdin             # 功能验证：2 条 warning，exit 1
```
---

**编译结束**: 2026-08-19 23:02
**最终状态**: built
