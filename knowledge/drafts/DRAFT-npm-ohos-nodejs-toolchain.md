# DRAFT-npm-ohos-nodejs-toolchain：OHOS 上 npm/Node.js 适配四坑

> Contributor: alexjs-11.0.1 适配 | Status: Draft | Updated: 2026-08-19
> Source: archives/a/alexjs/11.0.1

## 现象

alexjs 11.0.1（npm CLI 工具）适配 OHOS PC 过程中命中四条独立坑：

1. **hnp node 自带 npm wrapper 崩溃**：`npm --version` / `npm install` 直接
   Signal 5 core dump（V8 `Check failed: 12 == (*__errno_location())`）。
2. **--omit=dev 误删传递依赖**：`npm install --omit=dev` 后 `supports-color`
   缺失（chalk/debug/vfile-reporter 的传递依赖），CLI 启动即
   `ERR_MODULE_NOT_FOUND: Cannot find package 'supports-color'`；`npm prune
   --omit=dev` 同样误删。
3. **Node v24 DEP0180 警告污染 stderr**：上游 tape 测试断言精确 stderr
   （如 `Could not find reporter \`doesntexist\`\n`），Node v24 的
   `(node:xxx) [DEP0180] DeprecationWarning: fs.Stats constructor is deprecated.`
   写入 stderr 导致断言失败。
4. **CI L1e 误判假测试**：CI `find <pkg> -name bin -type d -print -quit` 匹配到
   `node_modules/xo/node_modules/semver/bin`（而非顶层 bin/），L1e 破坏性验证
   移错目录 → 真实测试被误判为"不依赖被测包"。

## 根因分析

1. hnp npm wrapper（`/data/service/hnp/bin/npm`）执行路径触发 V8 errno DCHECK，
   OHOS 平台限制；真实 npm-cli.js 位于 node 前缀 `lib/node_modules/npm/bin/`。
2. OHOS 上 npm 的 omit/prune 对传递依赖去重有 bug。
3. Node 版本升级引入的 stderr 噪音，非上游测试问题。
4. CI 产物探测 `find -name bin` 无法区分顶层 bin/ 与 node_modules 嵌套 bin/。

## 解决方案

1. **npm 调用**：`node <npm-prefix>/lib/node_modules/npm/bin/npm-cli.js` 直接调用，
   配 `NODE_OPTIONS=--jitless`。
2. **node_modules**：完整安装（不 --omit=dev、不 prune），整树打包。
3. **测试**：`NODE_OPTIONS=--jitless --no-deprecation`（--no-deprecation 仅测试环境）。
4. **打包**：package() 遍历清理 node_modules 内所有 `bin`/`.bin` 目录（CLI 入口
   运行时不需要，模块解析走 package.json main/exports）。
5. **launcher**：`env -i PATH/HOME/TMPDIR` 干净环境 + `node --jitless`。

## 验证证据

- alexjs 11.0.1：conan create G2 PASS，上游测试 47/47 PASS，test_package 3/3 PASS，
  W3 本地 CI 模拟通过，L1e 破坏性验证通过（bin 移走后 conan test 失败 → 真测试）。

## 禁止做法

- 不要 `npm install --omit=dev` / `npm prune --omit=dev`（误删 supports-color）。
- 不要直接调用 hnp npm wrapper（Signal 5 崩溃）。
- 不要通过 `copy(self, "node_modules/*", ...)` 打包（pattern 与 src 不匹配会
  静默空目录，见 DRAFT-conan-copy-keep-path-nesting）。
