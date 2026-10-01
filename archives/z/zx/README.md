# zx

## 简介

[zx](https://github.com/google/zx) 是 Google 维护的 JavaScript 脚本运行时与命令行工具，
用 JS 取代 bash 编写脚本：模板字面量执行命令（`` $`cmd` ``）、内建 `cd`/`sleep`/`fetch`/
`question`/`retry`/`spinner` 等工具函数、自动引号转义与错误处理。

- 包类型：CLI 工具（`package_type = "application"`），产物含 `bin/zx` 可执行入口
- 运行时：node v24.13.0（`zx` 无任何运行时 npm 依赖，npm 包的 `dependencies` 为 null）
- 构建系统：custom（npm；无 C/C++ 编译）

## OHOS 适配

| 要点 | 说明 |
|------|------|
| node 必须 `--jitless` | 本机 node v24.13.0 不加该参数即 `Check failed: 12 == (*__errno_location())` → Signal 5 core dump |
| npm 须直接调 CLI | hnp 的 `npm` wrapper 同样 Signal 5；用 `node <node 前缀>/lib/node_modules/npm/bin/npm-cli.js` |
| 测试前用 tsc 预处理 TS | `--jitless` 关闭 WebAssembly，node 自带 TS transform（amaro）不可用；用包内 typescript（devDependency）编译 4 个 `.ts` 测试 |
| FORCE_COLOR=1 | 设备 TERM=dumb，chalk 自动关色会让上游颜色断言失败；显式给彩色能力而非改断言 |
| whoami shim | `/system/bin/whoami` 对应用 uid 恒报 `bad uid`（/etc/passwd 无记录），上游 fixture `markdown.md.mjs` 因而退出 127；runner 在 PATH 前置等价 shim |
| launcher 干净环境 | node 继承 OHOS 容器变量（AppSpawn/UBSAN/ALACRITTY）会崩溃；`bin/zx` 用 `env -i PATH/HOME/TMPDIR` 执行 |
| 平台限制豁免 | 无外网出口、`/tmp` 只读 erofs、OHOS toybox `ps -lx` 无列边界导致 `@webpod/ps` 解析失败——以 `EXPECTED_ENV_FAILURES` 清单显式列出并打印原因，清单之外任何失败都会让 `conan create` 失败 |

## 依赖

- 无 Conan 依赖（纯 JS，无 C/C++ 库依赖）
- 构建/运行时前提：node >= 18（本机 v24.13.0）、npm（经 npm-cli.js 调用）

## 功能验证

```bash
zx --version                      # 8.8.5
zx -e 'const o = await $`echo hi`; console.log(o.stdout.trim())'
zx ./script.mjs                   # 脚本文件执行（fs/$/cd 均可用）
```

本地 CI 模拟结果：`L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=pass: zx --version OK`，
`test_package 4/4 checks passed`，上游 12 个测试文件 259 用例实跑（235 pass / 23 平台豁免 / 1 skip）。

## 版本

- 8.8.5: built (2026-09-30)，conan 配方；上游测试套件实跑，`EXPECTED_ENV_FAILURES` 清单外零失败

## 参考

- 官网: https://google.github.io/zx/
- 上游仓库: https://github.com/google/zx
