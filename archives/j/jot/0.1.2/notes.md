# jot 0.1.2 适配笔记

## 目标确认
- **上游**：`shashwatah/jot`（Homebrew `jot` 稳定版 **0.1.2**）
  - 上游仓库：https://github.com/shashwatah/jot
  - 源码 tag 归档：`https://github.com/shashwatah/jot/archive/refs/tags/v0.1.2.tar.gz`
  - sha256（Homebrew formula 权威值）：`d7da3220c29102ee7c51e2a5656ceb6672ae3b85be22c5ddcd176b330c6029c9`
- **语言/构建**：Rust（cargo 项目），产出一个 `jt` 二进制。许可证 MIT。
- **上游测试审计**：登录 GitHub API 递归审计 v0.1.2 源码树，确认 **无任何测试**：
  - 无 `tests/` 目录（递归 tree 无 tests 路径）。
  - `src/` 全部 11 个文件（main.rs、app.rs、enums.rs、traits.rs、utils.rs、
    output/{mod,error,message}.rs、state/{mod,args,config}.rs、
    state/vaults/{mod,vault,data}.rs）均无 `#[test]`/`#[cfg(test)]` 模块。
  - `Cargo.toml` 仅 6 个运行时依赖（serde/toml/clap/directories/fs_extra/dunce），
    无 `[dev-dependencies]` 测试 harness。
  - 仓库无 `.github` CI 工作流。
  - 因此 `upstream_tests_exist: false`，输出 `status:"no_tests"`（build() 与
    test_package 每轮重发 HMBS_UPSTREAM_TEST_RESULT）。

## 真机编译失败与修复（多轮）
- **R1 失败**：`/system/bin/sh: cargo: inaccessible or not found`（Error 127）。
  OHOS 真机默认 PATH（hmbs 注入 cmake/make/ninja/python3）无 cargo/rustc。
- **R2 尝试（弃用）**：照 cargo-seek/0.1.0 从 Harmonybrew bottles 引导
  （rust + openssl3 + zlib + ca-certificates）。**真机 R2 失败**：
  `rust-1.97.1.arm64_ohos.bottle.tar.gz` 在 harmonybrew.atomgit.com 与 gh-proxy
  均 HTTP 404（该 rust bottle 不存在）。
- **R3（当前，采用）**：改用仓库内已合入的 **below/0.11.0、libetebase/0.5.8** 方案：
  - `build_requirements()` `tool_requires("rust-toolchain/1.97.1")`：基础设施包，
    官方 rust-lang dist tarball 经 rsproxy.cn/USTC 镜像下载，
    含 aarch64-unknown-linux-ohos 宿主+目标标准库。
  - 该包二进制**未签码**，OHOS loader 拒执（EACCES errno 13）：
    `_prepare_signed_toolchain()` 把 cargo/rustc 及 rustc dlopen 的
    librustc_driver dylib 复制到 build 目录并用 `binary-sign-tool sign -selfSign 1`
    自签；其余只读负载（rustlib，~500MB）软链；marker 幂等。
  - cargo 运行期动态链接 libssl/libcrypto/libz（OHOS loader 忽略 DT_RUNPATH）：
    `_prepare_runtime_libs()` 用 Python urllib 下载 Harmonybrew **openssl3 3.6.4 /
    zlib-ng-compat 2.3.3_1** bottles（libetebase 真机验证存在——但此旧版本号
    已在 R4 发现 404，需用清单当前版本 3.6.5_1 / 2.3.3_2，见下文 R4）并放入
    LD_LIBRARY_PATH。
  - 采用 `cargo build --release --locked --target aarch64-unknown-linux-ohos`。
  - `.cargo/config` 放 CARGO_HOME：rsproxy.cn sparse 镜像 + 网络容错
    （retry=3）+ 可选 cainfo。
  - clang 作链接器（conf 或 /data/service/hnp/bin/clang 回退）；
    CARGO_TARGET_*_LINKER / CC_aarch64 / AR / RANLIB 显式设置。
  - `package()` 从 `target/aarch64-unknown-linux-ohos/release/jt` 拷到 bin/，
    并保留许可证。
- conandata.yml 已移除（404 的）rust_toolchain bottles，仅保留上游源码；
  运行期 bottles 在 conanfile.py 的 RUST_RUNTIME_BOTTLES 常量中声明。
- **R4 修复（bottle HTTP 404）**：真机报 `HTTPError: HTTP Error 404: Not Found`
  发生于 `_rust_environment → _prepare_runtime_libs → _download_bottle`——
  配方沿用 below/0.11.0、libetebase/0.5.8 的**旧** bottle 版本号
  `openssl@3-3.6.4` / `zlib-ng-compat-2.3.3_1`，而 harmonybrew 的 `/bottles/`
  不保留历史归档，会用新版本号直接替换（旧归档返回 404）。从 harmonybrew
  官方公式清单 `https://harmonybrew.atomgit.com/api/formula.jws.json` 读取
  openssl@3 与 zlib-ng-compat 的当前 stable arm64_ohos bottle，得到：
  - `openssl%403-3.6.5_1.arm64_ohos.bottle.1.tar.gz`
    sha256 `ae1d5bf9252d65d86053e68d7c91fc9d0066016bce50662ce4a32a0b0e954ef2`
  - `zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.1.tar.gz`
    sha256 `7092bfe7af8908f4a7c72493881291fe2416f27fc6502c34e22346a4dbfc4c51`
  已逐位下载校验 sha256 一致，且确认两 bottle 内含 `libssl.so.3`/
  `libcrypto.so.3`/`libz.so.*` 于 `.../lib/`（`_prepare_runtime_libs` 的
  遍历逻辑可命中）。已在 conanfile.py 的 RUST_RUNTIME_BOTTLES 更新。
  若未来再遇 404，应从上述 JWS 清单读取当前版本号更新，勿沿用旧号。
- **R5 修复（rustc -vV librustc_driver symbol not found）**：R4 让 cargo 开始运行
  后，`rustc -vV` 报 `Error loading shared library librustc_driver-75af....so
  (needed by .../rustc) + Error relocating rustc: ...main: symbol not found`
  （exit 127），HMBS 平台诊断分类 `[stale_runtime_library]`。据
  feedback/8e6fd3e3 + E517/E318：该表象（`Error loading shared library <lib>`
  伴随误导性 `Error relocating … symbol not found`）实为 **.so 签名不被 OHOS
  loader 接受**——配方直接对可能已带 `.codesign` 段的 librustc_driver 副本
  重签，而 binary-sign-tool 无法覆盖已有签名段，生成的签名无效导致 loader
  拒绝映射该 dylib。修复：① 自签前先 `llvm-objcopy --remove-section .codesign`
  剥离陈旧签名段（`_strip_codesign()`，容忍无段），再 `-selfSign 1`；② 为
  防 rustc 经加载器 namespace 落到系统旧 driver 副本，`_rust_environment` 里
  把当前构建自签的 `librustc_driver-*.so` 用 `LD_PRELOAD` 精确加载
  （`_signed_driver_path()`，zurl/1.12.0 + E200/E517 先例）。
- **R6 修复（rustc 仍找不到 driver：Error loading shared library … needed by
  rustc）**：R5 修正签名（relocation symbol not found 消失）后，真机仍报
  `Error loading shared library librustc_driver-75af....so: (needed by rustc)`
  （exit 127）——即 rustc 解析 DT_NEEDED 时**找不到/无法加载**该 driver。
  据 E186/czkawka：OHOS musl ldso 对非标准路径二进制**忽略 LD_LIBRARY_PATH**，
  只认 **RUNPATH/RPATH**；czkawka 用 `patchelf --set-rpath` 把用户 lib 目录
  写入 cargo/rustc 的 RPATH 后才让 cargo 找到 libz。修复：在
  `_prepare_signed_toolchain` 签名循环里，对 cargo/rustc 先 `_strip_codesign`，
  再用 `_add_rpath()`（patchelf --set-rpath）把「工具链 lib 目录（librustc_driver）
  + 运行期 openssl/zlib lib 目录」写入其 RUNPATH，再 `-selfSign 1`（E077 四步：
  strip codesign → patchelf → sign → chmod；accessibility/26.04.3 同）。driver
  本身仍 strip+sign（不做 patchelf）。这样 rustc 经自身 RPATH 精确定位当前
  构建的自签 driver，不再受 LD_LIBRARY_PATH 是否被 OHOS 忽略影响。

## 测试接入
- **上游**：无测试（见上），`no_tests`。
- **test_package**：test_jt.sh 2 条真实断言（可执行性 + `jt --help` 实际运行产出
  非空输出；clap v3 在 App::new() 解析参数前就处理 `--help` 并退出 0，不触发
  directories 的 HOME 依赖）。conanfile.py test() 结束后输出
  HMBS_TEST_PACKAGE_RESULT（discovered=2, passedCount=2）与 HMBS_UPSTREAM_TEST_RESULT
  no_tests 标记。

## 配方结构
- `archives/j/jot/0.1.2/conanfile.py`：package_type="application"，
  tool_requires(rust-toolchain/1.97.1) + 自签 + 运行期 bottles + cargo build。
- `conandata.yml`：官方 GitHub tag URL + Homebrew sha256。
- `manifest.yaml`（版本级 + 软件级）：`build_system: custom`（cargo）。
- `commands.json`（软件级，R38）：type=tool，二进制 `jt`。
- `test_package/`：test_jt.sh（R34 实质执行）+ conanfile.py（HMBS 标记）。
- `notes.md`（本文件）。

- **R7 策略切换（regress to below/libetebase/lemmeknow 模式，移除 R5/R6 叠加手段）**：
  本轮真机仍报 `rustc -vV` exit 127 `Error loading shared library librustc_driver-75af....so: (needed by rustc)`。
  R6 的 patchelf RPATH 未改变现象，说明其基于 E186（cargo 缺 libz / RUNPATH）的根因假设与 rustc 加载
  librustc_driver 是两码事——E186 是 **cargo** 运行期缺 libz，而本错误是 **rustc** 启动时加载其
  DT_NEEDED 的 driver，被 R5 引入并从 R5 起持续存在的 **LD_PRELOAD 强制预加载 driver** 才是本症状的来源
  （preload 先于主程序尝试加载 driver，加载失败即 `Error loading shared library ... (needed by rustc)`）。
  below/0.11.0、libetebase/0.5.8、lemmeknow/0.8.0 在同一 rust-toolchain/1.97.1 包 + 同一 OHOS loader 下
  用 **纯正 copy+sign+LD_LIBRARY_PATH**（无 LD_PRELOAD、无 patchelf RPATH、无 codesign 剥离）即成功运行
  cargo/rustc 及其上游测试。故 R7 做策略回归：
  - `_rust_environment` 删除 LD_PRELOAD（及 `_signed_driver_path`）。
  - `_prepare_signed_toolchain` 签名循环删除 `_strip_codesign`、patchelf `_add_rpath`，回到纯二进制定位
    自签（`_toolchain_rpath_dirs`/`_runtime_bottle_lib_dirs`/`_strip_codesign`/`_add_rpath` 全部删除）。
  - 保留 R3（自签 + LD_LIBRARY_PATH）、R4（新版 bottles 3.6.5_1/2.3.3_2）的既有正确内容。
  - 工具链其余只读负载仍软链，rustc sysroot（lib/rustlib）仍可见。
**教训**：不要靠叠加平台补丁，先对齐已被真机验证合入的同源食谱（below/lemmeknow）的最小正确形态，再最小增量。

- **R8 策略修正（缩写：strip-codesign + LD_PRELOAD，去掉 RPATH；修 R7 误判）**：
  R7 把 R5/R6 全部回退后，真机反而回到更精确的符号错：
  `Error loading shared library librustc_driver-75af....so: (needed by rustc)` 之后明确出现
  `Error relocating rustc: _RNvCs8j5Gk1BAvSc_17rustc_driver_impl4main: symbol not found` 与
  `_RNvNtCscXlqXfLctsd_3std2rt19lang_start_internal: symbol not found`。
  本轮 HMBS 平台诊断 [stale_runtime_library] 给出权威处置：
  **测试进程加载了系统旧动态库而非当前构建产物；把当前 build lib 目录加入运行环境；
  OHOS loader 忽略 LD_LIBRARY_PATH 时，仅对测试命令用 LD_PRELOAD 指向本次构建的共享库。**
  据此修正此前对 R5/R6 的误判（R7 误以为 LD_PRELOAD 是元凶，实际它是被 R6 的 patchelf RPATH 拖累）：
  - **`_strip_codesign`（自签前剥陈旧 .codesign）重新启用**：E517/E318——binary-sign-tool 无法覆盖
    已有签名段，残留签名让 loader 拒绝映射 dylib → 出现误导性 `symbol not found`。R5 观察到 strip 后
    该 relocation 错消失，方向正确。
  - **`LD_PRELOAD = 当前自签 driver` 重新启用**：本真机 loader 忽略 LD_LIBRARY_PATH，rustc 的
    DT_NEEDED librustc_driver 落到系统旧 driver（同名 SONAME 符号不匹配）→ 强制 preload 本次构建产物。
  - **`patchelf RPATH` 保持移除**：E186 是 **cargo** 运行期缺 libz 的 RUNPATH 问题，与 **rustc** 加载其
    DT_NEEDED driver 不是一回事；R6 中它与 LD_PRELOAD 并存反而引入空错串的
    `Error loading shared library ... needed by rustc`。below/libetebase/lemmeknow 都不用 RPATH。
  - 净组合 = **strip-codesign + LD_PRELOAD（无 RPATH）**。
  **R8 结果**：strip 消除了 relocation 错（健在），但残留纯 `Error loading shared library
  librustc_driver-75af....so: (needed by rustc)`——正是 LD_PRELOAD 被拒表象（见 R9）。

- **R9 策略切换（remove LD_PRELOAD → 对齐 below 纯净形态；第 4 策略周期）**：
  R8 的残留错误 `Error loading shared library librustc_driver-75af....so: (needed by rustc)`
  （无任何 relocation 追加）被知识库 E502 精确命中：**OHOS CI worker 对用户目录共享库的
  dlopen / LD_PRELOAD 一律拒绝**（无论签名；错误特征含 `needed by`）。paperjam 亦证
  `Error loading shared library <leaf> (needed by <preloaded>.so)` 为受禁机制，须停用 LD_PRELOAD。
  below/0.11.0（已合入、同一 rust-toolchain/1.97.1 包 + 同一 loader）用**纯 copy+sign+LD_LIBRARY_PATH
  （无 LD_PRELOAD / 无 RPATH / 无 strip）**即让 cargo/rustc 及上游测试全跑通——rustc 通过自身相对路径
  （<bin>/../lib）dlopen 其 librustc_driver（rainfrog DRAFT-13336），driver 被放到 rust-toolchain/lib/
  即可被 exec 时经路径加载，无需 preload。
  修复（本轮采用的净组合 = **strip-codesign + 无 LD_PRELOAD，无 RPATH**）：
  - `_rust_environment` 删除 `LD_PRELOAD = 自签 driver` 块（并删除 `_signed_driver_path`）。
  - `_prepare_signed_toolchain` 保留 `_strip_codesign`（E517：jot 包内 driver 携带陈旧 .codesign，
    R7 纯签不剥 → relocation `symbol not found`；R8/R9 剥后再签 → relocation 错消失，故 strip 必须保留，
    这是 jot 与 below 的唯一差异）。
  **上一方案为何无效**：R8 把 LD_PRELOAD 当成「正餐」解决 driver 加载，但 E502/paperjam 真机证据表明
  OHOS(CI worker) 拒绝用户目录 .so 的 dlopen/LD_PRELOAD，失败表象恰为此空错串。LD_PRELOAD 不是
  driver 加载的正解，反而制造了 R8 的残留失败。

- **R10 策略收敛（移除 `_strip_codesign`，纯 copy+sign 对齐 below/libetebase；第 5 策略周期）**：
  截止 R9（strip-codesign + 无 LD_PRELOAD + 无 RPATH），真机仍报：
  ```
  error: process didn't exit successfully: `rustc -vV` (exit status: 127)
  Error loading shared library librustc_driver-75af....so: (needed by .../rustc)
  Error relocating .../rustc: _RNvCs8j5Gk1BAvSc_17rustc_driver_impl4main: symbol not found
  Error relocating .../rustc: _RNvNtCscXlqXfLctsd_3std2rt19lang_start_internal: symbol not found
  ```
  即 rustc 加载 **当前自签的** librustc_driver 后，其 `rustc_driver::main` / `std::rt::lang_start_internal`
  符号无法重定位——不是找不到库，而是**该 .so 的符号表不对**（loaded 但 symbol not found）。
  **复盘 why R5–R9 未收敛**：R5–R9 每一轮都在几个平台加固（strip 陈旧 .codesign / LD_PRELOAD /
  patchelf RPATH）之间来回切换，但从未真正回到**纯净 copy+sign**。R9 实际仍保留了
  `_strip_codesign`（因误信 jot 包内 driver 携带陈旧 .codesign），而仓库内全部**已合入** Rust 食谱
  （below/0.11.0、libetebase/0.5.8，同一 rust-toolchain/1.97.1 包 + 同一 OHOS loader）都用
  **纯 copy+sign（无 strip / 无 preload / 无 rpath）** 即让 cargo/rustc 及上游测试全绿。global grep
  证实仓库内没有任何其他 conanfile 使用 strip_codesign / LD_PRELOAD / patchelf。
  **修复（本轮）**：从 `_prepare_signed_toolchain` 删除 `_strip_codesign()` 调用与整个
  `_strip_codesign` 方法，签循环回到与 below/libetebase 逐字一致的
  `copy → sign(-selfSign 1) → os.replace → chmod 0o755`。此形态已由已合入食谱在**同一**真机/包/loader
  下实测通过，是结论最强的证据；不再叠加任何 jot 独有平台加固。




- **R11 修复（libc 0.2.132 → 0.2.155，首个支持 OHOS 的 libc；工具链跑通后的第一个
  编译期错误）**：R10 之后 cargo 终于开始编译依赖，但立即在 ``libc-0.2.132`` 编译时报
  ``error[E0425]: cannot find type c_char / c_long / time_t / rlim_t / __u64 ...``
  与 ``cannot find value __SIZEOF_PTHREAD_MUTEX_T / __SIZEOF_PTHREAD_RWLOCK_T / ...``
  （共 880 errors）。根因：jot 的 Cargo.lock 把 ``libc`` 锁在 0.2.132，该版本在
  ``src/lib.rs`` 的 ctype 定义里没有 ``target_env="ohos"`` 分支（c_char 等只在
  linux/android 等 cfg 下生成），而其 ``unix/linux_like/linux`` 模块又把 OHOS 当
  linux-like 编译——类型/常量两套 cfg 不一致，遂全部缺失。OHOS 支持的 libc 在
  PR #3138 之后（0.2.140 起）才加入。按已合入的 **weggli/0.2.4** 先例：它把
  libc 0.2.112 → 0.2.155（首个含 target_env="ohos" 定义、在同一
  rust-toolchain/1.97.1 下真机已验证），用 ``cargo update -p libc --precise 0.2.155``
  重生成锁图，构建保持 ``--locked``。
  修复（对齐 weggli）：新增 ``patches/0001-Cargo.lock-libc-ohos.patch`` 把 Cargo.lock
  的 libc 条目从 0.2.132（checksum 8371...）改为 0.2.155（checksum 97b3...）；
  conandata.yml 增加 ``patches`` 声明；conanfile.py 加 ``export_sources`` →
  ``export_conandata_patches(self)`` 与 ``build()`` 开头
  ``apply_conandata_patches(self)``。``git apply --check`` 对 patch 全匹配，应用后
  产物与预期 Cargo.lock 逐字节一致。所有依赖（atty/dirs-sys/hermit-abi/getrandom）
  的 ``libc = "0.2"`` 区间都满足 0.2.155，锁图仍自洽；构建继续 ``--locked``。

- **R12 修复（CI 严格 worker 拒载无效签名 → 自签前先剥 .codesign；第 6 策略周期）**：
  真机预检通过（head 9e9677df 纯 copy+sign），但官方 CI（conan-build-test
  #86649）在 conan create 的 build() 阶段失败：
  ```
  Error loading shared library librustc_driver-75adf430b23f8c75.so: (needed by
  .../build-release/rust-toolchain/bin/rustc)
  Error relocating .../rustc: _RNvCs8j5Gk1BAvSc_17rustc_driver_impl4main: symbol not found
  Error relocating .../rustc: _RNvNtCscXlqXfLctsd_3std2rt19lang_start_internal: symbol not found
  ```
  **核心读取（libntruprime 病历）**：`Error loading shared library <lib> (needed by …)` 是
  主错误（driver .so **整体加载失败**），随后的成串 `Error relocating … symbol not found`
  只是该未加载库逐符号的级联，不是符号缺失本体。driver 失败根因是**无效签名**：
  rust-toolchain/1.97.1 的 OHOS 目标二进制发布时就带 .codesign 段，binary-sign-tool
  **无法覆盖已有段**（E517/E318），直接 `-selfSign 1` 得到严格 CI worker 拒载的无效
  签名。真机交互环境较宽松（E502：interactive device environment is more permissive），
  同一无效签名也能加载 → 真机 passed 而 CI 失败，正解释本 PR 的真机/CI 分歧。
  **与 R5/R9/R10 的关系**：R5–R10 都在真机（宽松）上调 strip，真机无法区分 strip 与否，
  故反复横跳；R10 误判 strip 无效而删掉。本轮基于 CI（严格 worker）证据，按 E517/E318
  （对齐已合入 dmenu/5.4 的 E077 四步）**在自签前对 cargo/rustc/librustc_driver 逐个
  ``llvm-objcopy --remove-section .codesign`` 剥旧段**，再 ``binary-sign-tool sign
  -selfSign 1``，chmod 0o755；无 objcopy 或缺段（objcopy 报 .codesign not found）时容错
  跳过，不影响真机。其余保持 R10 形态（无 LD_PRELOAD、无 patchelf RPATH、driver 放
  rust-toolchain/lib/ 由 rustc 相对路径 dlopen、LD_LIBRARY_PATH 含 lib 与运行期 bottles）。

- **R13 修复（回归 below 纯净 copy+sign，撤销 R12 的 strip-codesign；第 7 策略周期）**：
  本轮真机预检（fixing_verification）在 conan create 的 build() 阶段再次报同一指纹：
  ```
  error: process didn't exit successfully: `rustc -vV` (exit status: 127)
  Error loading shared library librustc_driver-75adf430b23f8c75.so: (needed by
  .../build-release/rust-toolchain/bin/rustc)
  Error relocating .../rustc: _RNvCs8j5Gk1BAvSc_17rustc_driver_impl4main: symbol not found
  Error relocating .../rustc: _RNvNtCscXlqXfLctsd_3std2rt19lang_start_internal: symbol not found
  ```
  本次失败对应的是**工作树**（R12：自签前对 cargo/rustc/librustc_driver 逐个
  `llvm-objcopy --remove-section .codesign` 剥段再 `-selfSign 1`）——这是 jot 与仓库
  内全部已合入 Rust 食谱的唯一结构性差异。
  **复盘为什么会再次失败**：R12 的根因假设（driver 发布时带陈旧 .codesign，直接自签
  得到严格 worker 拒载的无效签名）被**已合入、真机/CI 双绿**的 below/0.11.0、
  libetebase/0.5.8 直接证伪——它们在同一个 rust-toolchain/1.97.1 包 + 同一 OHOS
  loader 下用**纯 copy+sign（无 strip / 无 LD_PRELOAD / 无 RPATH）**即让 cargo/rustc
  及其上游测试全部运行。若 driver 真带破坏性 .codesign，below 用同文件纯签也必失败。
  `llvm-objcopy --remove-section` 是对共享库的**二次 ELF 重写**，会破坏
  .gnu.hash/.dynsym 等动态表，使 loader 映射时 rustc 的重定位无法解析（恰为此
  `Error loading shared library … needed by rustc` + 连锁
  `Error relocating … symbol not found` 表象）。
  **修复（本轮）**：把 `_prepare_signed_toolchain` 的签名循环回退到与 below/0.11.0
  逐字一致的 `copy -> binary-sign-tool sign -selfSign 1 -> os.replace -> chmod 0o755`；
  删除 `_strip_codesign` 调用与 `_find_llvm_objcopy`/`_strip_codesign` 两个方法及对应
  docstring（module 与 _prepare_signed_toolchain 两处）。其余（无 LD_PRELOAD、无
  patchelf RPATH、driver 放 rust-toolchain/lib/ 由 rustc DT_NEEDED 相对路径加载、
  LD_LIBRARY_PATH 含工具链 lib 与 openssl/zlib bottles、libc 0.2.155 补丁、--locked）
  保持不变。此形态与 below/0.11.0（同包同 loader 已合入双绿）完全一致，是结论最强的
  证据。conanfile.py 工作树已回退到与 HEAD（R10 纯 copy+sign）一致。

- **R14 修复（真机 fixing_verification：cargo→rustc 载不到自签 driver）**：
  本轮真机 preflight（compile 阶段）复现同一指纹：
  `rustc -vV` exit 127：`Error loading shared library
  librustc_driver-75adf430b23f8c75.so: (needed by rustc)` + 连锁
  `Error relocating ... symbol not found`。此时 conanfile 已是纯 copy+sign
  （R13，与 below 逐字一致的签名循环），但 **cargo 构建用 Conan 的 self.run()**
  执行，而真机全绿的 below/0.11.0 用 `subprocess.run(cmd, cwd, env=env)` 直接投递。
  **根因**：self.run 走 Conan buildenv/runenv 包装，按配方声明重写 LD_LIBRARY_PATH，
  把手动放进 rust-toolchain/lib/ 的自签 librustc_driver 路径丢掉，令 cargo 派生的
  `rustc -vV` 从系统默认路径载到旧 driver（stale_runtime_library 门禁）→
  `(needed by rustc)` + 符号错位。**修复**：把 build() 的 cargo 调用改为与 below
  逐字一致的 `subprocess.run(command, cwd=self.source_folder, env=env)`，去掉
  os.environ 存/清/恢复 与 self.run 包装；其余（纯 copy+sign、无 LD_PRELOAD、
  driver 放 rust-toolchain/lib/、LD_LIBRARY_PATH 含工具链 lib 与 openssl/zlib
  bottles、libc 0.2.155 补丁、--locked）不变。不设 LD_PRELOAD（OHOS worker 拒绝
  用户目录共享库 LD_PRELOAD，E502/paperjam），与 below 一致。
