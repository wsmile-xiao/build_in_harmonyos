# DRAFT-zig-build-ohos-consumption

> conan 配方消费 zig/ 工具包的完整模式（L2 主条，域=toolchain）：tool_requires 按上游 minimum_zig_version 硬 pin、build() 清 CC/CXX 系规避 0.15.x sysroot 探测、wrapper 自动签名 + AccessDenied 重试、package() _sign_elf、zon 依赖 vendored 本地 .path 零网络构建、zig 版本 pin 纪律。

## 问题特征（真实日志片段/标记）

OHOS 上 Zig 构建体系的包反复命中四类结构性问题（非单库偶发）：

1. **ELF 签名面**：OHOS 内核拒绝执行无签名 ELF；zig 构建期持续生成并派生宿主可执行（build runner、gen exe、lsp-codegen、测试二进制），首轮 spawn 报错：

   ```
   error: failed to spawn build runner zig-local-cache/o/<hash>/build: AccessDenied
   error: failed to spawn and capture stdio from ./zig-local-cache/o/<hash>/zls_gen: AccessDenied
   Build Summary: 5/10 steps succeeded; 2 failed
   ```

   （wrapper 签名后自动重跑同一命令，紧接 `Build Summary: 10/10 steps succeeded` ——两次 Build Summary 属预期，非构建失败。zls 0.15.1 实测 `runs/zls-0.15.1/logs/conan-create-3.log`：build 5/10→10/10，test 11/49→49/49。）

2. **sysroot 探测**：zig 在 OHOS 的宿主 libc 探测 consult 系统 OHOS SDK clang，注入的 sysroot 缺 musl `bits/alltypes.h`（C 依赖编译报 `'bits/alltypes.h' file not found`）。
3. **构建期网络抓取**：build.zig.zon 的 url 依赖由 zig build 在线 fetch，runner/worker 到 github 的连通性不可控（flow-control 记录过 ConnectionTimedOut/HttpConnectionClosing 反复重试史）。
4. **版本 pin**：上游以 `minimum_build_zig_version`/`minimum_zig_version` 硬 pin major.minor，跨 pin 直接 `@compileError`（zls 0.15.1 对 0.16.x/0.14.x 均 compileError）。

## 模式内容（rec，五件套，全部真机验证）

1. **工具链声明与版本 pin 纪律**：`build_requirements()` 里 `self.tool_requires("zig/<pin>")`；pin 唯一依据是上游 `build.zig`/`build.zig.zon` 的 minimum 版本声明——0.15.x pin → 仓内 `zig/0.15.2`，0.16.x pin → `zig/0.16.0.1`。禁止跨 major.minor 复用（0.15.x 与 0.16.x 构建系统 API、libc 探测行为互不通用）。
2. **build() 环境整备**：
   - 清空 `CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS/CPATH/C_INCLUDE_PATH/CPLUS_INCLUDE_PATH`，让 zig 回落自带 musl 头。**该路径对 zig/0.15.x 有效**（flow-control/0.7.2 21/21 步、zls/0.15.1 49/49 步双实证）；**对 zig/0.16.x 无效**（探测与 env 无关，须 `-Dtarget=aarch64-linux-musl` 或文件级 vendor 头，见 odiff 条目）。
   - `ZIG_GLOBAL_CACHE_DIR`/`ZIG_LOCAL_CACHE_DIR` 钉进 conan build_folder（隔离全局缓存、可复现）。
   - `ZIG_OHOS_SIGN_ROOTS` 覆盖双缓存 + `<source>/zig-out`，zig/0.15.2 wrapper 据此对构建期生成的每个 ELF 自动签名，AccessDenied→签名→自动重跑是 wrapper 内建行为，配方层不要叠加自己的重试循环。
3. **zon 依赖 vendoring（零网络构建）**：`source()` 内对 build.zig.zon 的每个非 lazy 依赖，以 pinned tarball（conandata.yml 固定 URL+SHA256，附 gh-proxy 回退 URL）下载并解包到 `<source>/deps/<name>`，再以 conandata patch 把 zon 条目改写为本地 `.path` 引用。lazy 依赖（如 tracy）不启用即不抓取，无需处理。minizign/0.1.13（patches/0001-use-zig-clap-tarball-url.patch）与 zls/0.15.1（patches/0001-vendor-zig-dependencies-as-local-paths.patch）两例实证。
4. **产物签名**：`package()` 内 `_sign_elf`：`llvm-objcopy --remove-section .codesign` 后 `binary-sign-tool sign -inFile … -outFile … -selfSign 1`，回移动并 chmod 0755（minizign/flow-control/zls 三处同范式；工具路径探测带 env 覆盖 + which + 绝对路径回退）。
5. **上游测试内嵌**：`build()` 直接 `zig build test -Doptimize=ReleaseSafe --summary all`（在 conan create 内真实执行，供 CI L1 从日志核验）。host 目标下 build-runner 类步骤照常运行：上游以 `b.graph.zig_exe`（= wrapper 路径）spawn zig build，缓存根已在 ZIG_OHOS_SIGN_ROOTS 内，签名传播成立（zls 10 个 build-runner 用例全过实证）。测试计数诚实上报：skipped>0 记 incomplete 不记 passed。

## 证据（仓内 6 处 tool_requires 实例 + 本 run 日志）

| 配方 | tool_requires 位置 | pin |
|---|---|---|
| archives/f/flow-control/0.7.2/conanfile.py | line 44 | zig/0.15.2 |
| archives/n/ncdu/2.9.2/conanfile.py | line 42 | zig/0.15.2 |
| archives/n/nkt/0.3.1/conanfile.py | line 89 | zig/0.15.2 |
| archives/z/zls/0.15.1/conanfile.py | line 56 | zig/0.15.2 |
| archives/m/minizign/0.1.13/conanfile.py | line 29 | zig/0.16.0.1 |
| archives/o/odiff/4.5.0/conanfile.py | line 61 | zig/0.16.0.1 |

- 本 run vendoring/零网络实证（E1 修复后，patch 真实生效）：`runs/zls-0.15.1/logs/conan-create-3.log` **L98** `Apply patch (portability): Reference the pinned Zig package dependencies from vendored local paths ...`；零网络三重证据——build 目录 `build.zig.zon` 实际改写为 `.path = "deps/{known-folders,diffz,lsp-kit}"`（L18/L23/L28，仅剩 tracy lazy url）、`build-release/zig-global-cache/p/` 0 项（联网 fetch 必留依赖包缓存项）、全日志无任何 zig fetch/download 行。
- 本 run 测试与门禁证据：`runs/zls-0.15.1/logs/conan-create-3.log`（AccessDenied→wrapper 重试两次 Build Summary、src 92/92、主套件 409+8skipped+0failed、analysis 23/23、build-runner 10/10、`add codesign section success`）；权威 CI `runs/zls-0.15.1/logs/ci-run-5.log`（最终 tree，L0-L5 全 pass，计数同上）与 `worktree/.ci_logs/conan_build_zls_0.15.1.log`。
- zls 配方对应实现：`archives/z/zls/0.15.1/conanfile.py`（`_zig_env`/`_sign_elf`/`source()` vendoring）、`patches/0001-vendor-zig-dependencies-as-local-paths.patch`、`conandata.yml`（`zig_dependencies` SHA256 + gh-proxy 回退）。

## 禁止策略

- 禁止使用 pin 区间外的 zig 工具包（0.14.x/0.17.x 或跨 0.15/0.16 混用）：上游 minimum 版本声明是硬约束，跨 pin `@compileError` 或行为错配。
- 禁止把 wrapper 的 AccessDenied→重试当构建失败处理：首轮 Build Summary 部分失败 + 自动重跑成功属预期路径，叠加自定义重试会造成双重签名/重复计时；重试判定若必须自写，须基于捕获的 zig 输出而非 `str(exc)`（conan self.run 异常消息不含 zig stderr）。
- 禁止在 build() 依赖 zig 联网 fetch：一律 source() 阶段 pinned vendoring；确需镜像时按 flow-control 先例改写 URL 为 gh-proxy 并预拉缓存。
- 禁止省略 package() 二次签名：wrapper 只覆盖 ZIG_OHOS_SIGN_ROOTS 内的构建期产物，打包复制的最终 ELF 必须重新 _sign_elf。
- 禁止把 zig/0.16.x 的探测失效归咎于清 env 不彻底：0.16 探测与 env 无关，正确出路是 -Dtarget 或文件级 vendor（odiff 条）。

## 与相近条目的边界（查重）

- **DRAFT-odiff-4.5.0-zig-ohos-libc-probe-incomplete-sysroot-global-bypass**：相邻但不同——该条是 zig/0.16.x 特有的「探测注入不完整 sysroot + access→statFile」**故障修复**条；本条是跨版本通用的 zig 工具链**消费模式**主条（0.15.x 清 env 即可 vs 0.16.x 须 target/vendor 的版本边界也由本条承载）。
- **DRAFT-flow-control-zig-env-clearing-ohos-sysroot**（odiff kv similar_to 引用）：flow-control 的 0.15.x 清 env 单点验证；本条将其纳入完整五件套模式并以 zls 0.15.1 第二次实证（含 vendoring、wrapper 重试、test 内嵌等 flow-control 配方之外的面）。
- codeload/无扩展名 tarball 的 BadZipFile 坑不出本条：knowledge/graph E276/E483 已沉淀，本条仅在 rec_command 中体现 `filename=` 显式后缀的写法。

## 适用判断

适用于：任何构建体系为 Zig（build.zig/build.zig.zon）的 conan 配方在 OHOS runner 上的新建/升级——按上游 minimum 版本选 zig 工具包，按五件套组织 build()/source()/package()，并把上游 `zig build test` 内嵌进 build()。含 C 依赖的 zig 项目（@cImport/独立 C compile step）在 0.15.x 上先试清 env，不干净再按 odiff 条升级处理；在 0.16.x 上直接走 target/vendor 路径。
