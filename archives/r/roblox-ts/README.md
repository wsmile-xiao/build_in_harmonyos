# roblox-ts (rbxtsc) — TypeScript → Luau 编译器

## 一句话说明
roblox-ts 把 TypeScript 编译为 Roblox 平台使用的 Luau 代码，命令行入口为 `rbxtsc`。

## 功能概述
- 将 TypeScript 项目（`tsconfig.json` + `src/`）编译为 Luau（`.lua` / `.luau`）
- 类型安全 + 宏（compiler-types）驱动的 Roblox API 映射
- `--watch` 增量编译、`--rojo` 对接 Rojo 项目、`--luau` 输出 `.luau` 扩展名
- 随包分发 Luau 运行时（`include/RuntimeLib.lua`、`include/Promise.lua`），由 `copyInclude` 拷入项目

## OHOS 适配
- **包类型**：`application`。「无构建/打包族 · 脚本工具」范式——npm 官方发布包已含
  预编译 `out/**/*.js`（206 个 .js + 206 个 .d.ts），conan 侧无编译阶段：
  `out/` + `include/` + `package.json` + `README.md` → `libexec/roblox-ts/`，
  `LICENSE` → `licenses/`。
- **启动器（关键适配）**：上游 `out/CLI/cli.js` 的 shebang 是
  `#!/usr/bin/env node`。OHOS 上 `/usr/bin/env` 在部分运行 uid 下不可执行，且
  PATH 首位的 `node` 可能是构建工具链自带、启动即崩（`Native stack trace`，
  SIGABRT，实测 rc=134）的二进制。因此配方生成 `bin/rbxtsc` POSIX sh 启动器：
  按 `RBXTSC_NODE` → PATH 中的 `node` → `/data/service/hnp/bin/node` 顺序探测
  `node --version`，取第一个可用解释器后 `exec`。
- **运行时依赖**：系统 Node.js（OHOS 自带 hnp node v24.13.0，实测可运行）；
  不引入任何 npm 运行时依赖（发布包已自带全部依赖的打包产物）。

## 依赖关系
- 运行时：系统 `node`（环境提供，非 conan 包）
- 编译：无（npm 发布包即最终产物）；本仓库另有 `npm ci + npm run build`
  真实源码构建证据（见 `3.0.0/notes.md`）
- conan 依赖：无

## 测试
- 上游单元测试（mocha，`out/CLI/test.js`）：131 用例，OHOS 真机 131/131 通过
- 上游集成测试（rojo + lune，38 个 spec / 462 个 it）需 Rust 外部二进制，目标环境无法执行
- 消费者验证（`test_package/`）：32 条断言位（27 通过 / 5 项环境性 skip），其中 5 条鸿蒙特有用例（另 1 条为 node 门槛项）

## 参考资料
- 上游仓库：https://github.com/roblox-ts/roblox-ts
- 文档：https://roblox-ts.com/
- npm：https://www.npmjs.com/package/roblox-ts
- 版本：3.0.0（MIT）
