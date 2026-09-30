# DRAFT-roblox-ts-3.0.0-ohos-node-jitless-npm-cli

> Contributor: OpenDesk Agent | Status: Draft | Updated: 2026-09-29
> Source: roblox-ts 3.0.0 HarmonyOS PC 适配（npm / Node.js CLI）
> 领域：OHOS 运行时（E400）/ conan 构建期 node 交互 / npm 打包

## 背景

roblox-ts 是纯 TypeScript/Node.js 命令行工具（`rbxtsc`）。适配过程中 `conan create`
在 `build()` 阶段连续 4 次以 `Native stack trace / Signal 6 (core dumped)`（rc=134）
失败，且同机对照实验显示：**已并入 main 的 `archives/a/acorn` 强制重建时，在同一位置
（`npm ci`）以完全相同的 SIGABRT 失败**。因此该现象不是单个配方缺陷，而是
npm/Node CLI 类包在 OHOS + conan 构建期的通用坑。

## 错误签名

```text
Native stack trace
Signal 6 (core dumped)
ConanException: Error 134 while executing
# 单独执行 node 时：
Fatal error in , line 0
Check failed: 12 == (*__errno_location())      # rc=133
# 关闭 stdio 重定向后暴露出的真实 npm 错误：
npm error code EACCES
npm error syscall symlink
npm error path ../resolve/bin/resolve
npm error dest .../node_modules/.bin/resolve
```

## 根因（三段，逐段实测）

1. **V8 JIT 崩溃（E400）**：本机 OHOS 镜像 node v24.13.0 一旦执行 JS 即崩。
   实测 6/6：

   | 命令 | 退出码 |
   |---|---|
   | `node -e '1+1'` | 133（SIGTRAP，`Check failed: 12 == (*__errno_location())`） |
   | `node --jitless -e '1+1'` | 0 |

   而 `node --version`（不执行 JS）在两种模式下都可能正常 —— 这解释了「有时看起来
   node 没问题」的假象。npm 自身是 node 程序，故构建期必须
   `NODE_OPTIONS=--jitless` + `--jitless`。

2. **`node_modules/.bin` 软链接被拒**：把 npm 的 stdio 重定向到文件后，SIGABRT
   消失，真实错误变为 `EACCES: permission denied, symlink '../resolve/bin/resolve'
   -> .../node_modules/.bin/resolve`。加 `--no-bin-links` 后 `npm install` 通过。
   （运行期 `rbxtsc` 直接 require 模块，不依赖 `.bin`。）

3. **node 不能继承 C/C++ buildenv**：conan `self.run()` 默认套 `conanbuild.sh`，
   其中 `LD_LIBRARY_PATH` 指向 OHOS SDK 的 `.../native/llvm/lib`。同一条 node
   命令在 `env=None`（不套 env 文件）时正常，套上 buildenv 时 `Native stack trace`。

## 解决方案（配方侧三件事，已在 roblox-ts 3.0.0 配方落地）

1. **npm 入口用真实 npm-cli.js**：`os.path.realpath(node)` 同级的
   `../lib/node_modules/npm/bin/npm-cli.js`，不要用 PATH 上的 npm —— PATH 首位可能是
   另一套 node 的 shell 包装脚本（本机为 `.../cmd-pkgs/bin/npm`），交给本配方选定的
   node 执行会报 `EACCES: ... lstat '/data/service/hnp/bin/npm'`。
2. **构建命令**：
   ```sh
   PATH="<node_dir>:/data/service/hnp/bin:/usr/bin:/bin" NODE_OPTIONS=--jitless \
     "<node>" --jitless "<npm-cli.js>" install --omit=dev --ignore-scripts \
     --no-bin-links --no-audit --no-fund --no-save --no-package-lock
   ```
   并以 `self.run(..., env=None)` 执行（不继承 C/C++ buildenv）。
3. **stdio 重定向 + 失败回显**：`... > "<log>" 2>&1 || { rc=$?; cat "<log>"; exit $rc; }`
   —— 直接继承 conan 的 stderr 时只能看到 `Native stack trace`，重定向后才能拿到
   npm 的真实报错（本条是定位 #2 的关键手段）。

## 验证

- `conan create archives/r/roblox-ts/3.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
  → **exit 0**（test_package 26 passed / 0 failed / 2 skipped）；
- `ohc-run.py conan-verify roblox-ts 3.0.0` → G1/G2/G3/G4/L2/L4/L5 全 PASS；
- `ohc-run.py finish roblox-ts 3.0.0 built` → W3 本地 CI 模拟通过，写 `.ci-result.json`（exit_code=0）；
- 对照实验：`archives/a/acorn`（已并入 main）强制重建在同一位置同样 SIGABRT，
  证明非本配方特有。

## 适用边界

- 适用：任何在 OHOS 上以 npm 发布包为 source、构建期跑 `npm install` 或 node 的配方；
  以及 test_package 中执行 node 的消费者测试。
- 不适用：目标平台为 Linux/macOS 的正常 CI（无需 `--jitless`，但加上无害）。
- 若上游 CLI 依赖 `node_modules/.bin`（如通过 `npx` 调用自身 bin），则不能简单
  `--no-bin-links`，需改为在允许建软链的环境构建或改写调用点为直接 require。

## 查重差异

- `exact_duplicate`：false（drafts/index.tsv 无 roblox-ts / npm --jitless 条目）。
- `causal_duplicate`：partial —— 与 **E400**（Node.js CLI JITless 能力边界）同源；
  本条新增 E400 未覆盖的两段：npm 在构建期作为 node 程序的 `--jitless` 传递、
  以及 `node_modules/.bin` 软链被拒与 buildenv 继承两个 conan 构建期坑。
- `trigger_overlap`：partial（E400 触发于 CLI 运行期；本条触发于 conan build() 阶段）。
- `solution_overlap`：partial（都落到 `--jitless`；本条另加 `--no-bin-links` + `env=None` + 真实 npm-cli.js）。
- `combination_novelty`：true。
