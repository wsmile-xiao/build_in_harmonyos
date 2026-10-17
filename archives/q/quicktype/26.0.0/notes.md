# quicktype 26.0.0 适配笔记

## 编译环境
- 构建系统: npm（纯 JavaScript CLI，无原生编译）
- 编译日期: 2026-10-01
- 运行时: Node.js v24.13.0 (OHOS, `/data/service/hnp/bin/node`), npm 11.6.2
- 编译器 settings: clang 15 / libc++ / Release（application 类型，无 C/C++ 编译）
- 状态: built

## 上游识别
- npm 包 `quicktype@26.0.0`（`dist-tags.latest`），上游 `https://github.com/glideapps/quicktype`
- 发布 tarball 仅含编译后的 `dist/`（`files: ["dist"]`），13 个文件
- `sha256(quicktype-26.0.0.tgz) = 55de624945e4f04fcc6d64c3ed6fcf2d1d6accd958e13c028deed8118b310c16`
- `engines.node >= 20.19.0`；运行时依赖 16 条，运行闭包 91 个 npm 包（无原生模块）

## 编译步骤
1. `get()` 下载 npm tarball（strip_root）
2. `npm install --omit=dev --ignore-scripts --no-audit --no-fund --no-package-lock --no-save --bin-links=false --registry=https://registry.npmjs.org`
   → 只安装 16 条运行时依赖（108 个包）
3. `package()` 先创建 `bin/quicktype` launcher，再复制 `dist/` + `node_modules/` + `package.json` 到 `res/quicktype/`
4. launcher 用 `exec node --jitless res/quicktype/dist/index.js "$@"` 运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `npm install`（不 omit dev）报 `ETARGET @biomejs/biome@^2.5.3` | 社区镜像 npm.cnb.cool 的 packument 版本不全（只有 2.5.1） | 显式 `--registry=https://registry.npmjs.org`（对齐 devcontainer 先例） |
| 2 | `npm install --omit=dev` 仍报 ETARGET | `--omit=dev` 只跳过安装、仍需解析 devDependencies | 同 #1 |
| 3 | 本机 `node`（cmd-pkgs 24.19.0）执行即 SIGABRT(134) | cmd-pkgs 二进制与环境不兼容 | 使用系统 HNP Node `v24.13.0` |
| 4 | conan build 内 node `Check failed: 12 == (*__errno_location())` / SIGABRT | OHOS 下 V8 JIT 无法映射可执行内存（mmap 返回 EACCES 而非 ENOMEM） | `NODE_OPTIONS=--jitless` |
| 5 | conan build 内 `npm` 报 `EACCES lstat .../bin/npm` | 经 `npm` 符号链接启动时 node realpath 失败 | 用 `readlink -f "$(command -v npm)"` 取真实 npm-cli.js，直接交给 node 执行 |
| 6 | node 在 conan 中偶发 SIGABRT | node 继承 conan 的 socket stdin/stdout/stderr | 子进程 stdio 重定向到日志文件 + `/dev/null` |
| 7 | `npm install` 报 `EACCES symlink node_modules/.bin/...` | OHOS 禁止创建符号链接（E046） | `--bin-links=false`（运行时不需要 .bin） |
| 8 | test_package 直接 exec launcher 报 126 | Conan 构建上下文在 OHOS 拒绝直接 exec 脚本文件 | test.sh 优先直接执行、失败回退 `sh <launcher>`；并断言 launcher 具可执行位 |
| 9 | L1e 破坏性反向验证误判「假测试」 | `find <pkg> -name bin -type d -print -quit` 命中 `node_modules/typescript/bin`（tmpfs readdir 按创建顺序） | `package()` 中最先创建顶层 `bin/`，使其成为首个命中 |
| 10 | W3 本地 CI heredoc 报 `read-only file system` | zsh 的 heredoc 临时文件用 `TMPPREFIX`（默认 `/tmp`，OHOS 只读） | 运行 W3/CI 前 `export TMPPREFIX=$HOME/tmp/zsh`（环境侧，非配方改动） |
| 11 | W3 junk_check 回退 full 模式误报其它包遗留文件 | 本地无已提交变更 → `git diff origin/main...HEAD` 为空 | 以 `JUNK_PR_DIFF=<pr.diff>` 复现真实 PR 的 prdiff 模式（只检查本包文件） |

## 上游测试（OHOS 实测结果）

上游测试入口：`npm test` = `npm run test:unit`（`vitest run`）+ `npm run test:fixtures`（`script/test`）。

- **上游构建**：原生 `typescript ~7.0.2` 在 OHOS 不可用（`Unable to resolve @typescript/typescript-openharmony-arm64`）；改用 JS 版 `typescript@5.9.3` 后 `npm run build` 等价流程全部成功（根 `dist/` + `packages/*/dist` CJS/ESM）。
- **上游单元套件**：vitest 4 的原生绑定在 OHOS 不可加载（`rolldown-binding.openharmony-arm64.node: Permission denied`；WASI 回退 `UVWASI_EBADF`）。以等价 runner（vitest shim + Node loader + esbuild，位于 `.plan/qt_build/unitrun/`，不进入本 PR）真实执行 → **25 文件 / 158 用例 / 158 通过 / 0 失败 / 0 跳过**。
- **fixture 矩阵**：运行器可启动（生成阶段正常），但逐语言编译执行所需工具链在 OHOS 缺失（仅 clang/clang++、python3、ruby、node；缺 go/java/dotnet/crystal/dart/elixir/swift/kotlin/rust/php/ghc），85 配置 / 30 语言未执行。

消费侧验证由 test_package（6 项断言，含 1 项 OHOS 专有）承担；详见 `reports/test-report.md`。

## 本地门禁结果
- `conan create`（ohos-aarch64）：**EXIT=0**，npm 安装 108 包，test_package 6/6 通过
- `conan-verify`：**EXIT=0**（G1/G2/G3/G4 + L2/L4/L5）
- `finish`（W3 本地 CI 模拟）：**通过**；`.ci-result.json` 写入（exit_code=0，log_sha256 已记录）
  - L0 pass / L1 pass（含 L1e 反向验证）/ L2 skip（Conan 上下文禁 exec，非阻塞）/ L4 pass / L5 pass
  - Step 6 finalize 警告：无 `packaging/` 与 release/debug tar.gz（npm application 无归档产物，同 bruno-cli 先例）
  - Step 8 `gen_summary` 报框架内部错误（`'str' object has no attribute 'append'`），**非本包问题**，非阻塞
- W2 PR 原子性：无框架文件混入；`git add archives/q/quicktype` 仅纳入本包文件

## 源码修改
无补丁，无需修改上游源码。

## 交付物
| 文件 | 说明 |
|------|------|
| `bin/quicktype` | Shell launcher，`node --jitless` 运行 dist/index.js |
| `res/quicktype/` | `dist/` + `node_modules/` + `package.json` |
| `licenses/LICENSE` | Apache-2.0 |
---

**编译结束**: 2026-10-01 16:32
**最终状态**: built
