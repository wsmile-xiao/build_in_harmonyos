# libsignal-core 0.103.1 — 鸿蒙PC适配记录

## 任务与上游

- 任务: libsignal-core 0.103.1（平台 lang 标注 cpp，实为 Rust——平台语言标注不可信，
  但仓库已有 rust-toolchain/1.97.1 工具链包 + 8 个已合入 Rust 包先例，R47 预检可过）
- 上游: signalapp/libsignal monorepo，tag v0.103.1；本包 = rust/core crate
  （crate 名 libsignal-core，AGPL-3.0-only）
- workspace 根在仓库根：rust/core 不在 [workspace].members 列表（25 成员均未含它），
  靠 workspace.dependencies path 依赖隐式入图 → 必须 `cargo build -p libsignal-core`
  切片选建，避免构建 25 个成员（bridge/* 等）
- 上游 rust-toolchain 文件要求 1.98.1；crate rust-version=1.93.1，edition 2024。
  直接调用 cargo 二进制（不经 rustup）时 rust-toolchain 文件被忽略；
  自举 bottle 即 1.98.1（= 上游钉的版本，真机验证记录见下）

## R37 版本检查

- archives/l/ 仅有 libsignal-protocol-c（无关包）；libsignal-core 目录不存在 → 用任务版本
  0.103.1 起步，无递增

## 适配路径

- 适配路径只写最高层：**C（源码级适配，1 库 = 100 分冲刺）**
- 工具链处理沿用 archives/a/argc/1.24.0（已合入）：探测已知 cargo 位置，无则 Python
  urllib 下载 Harmonybrew bottles（rust-1.98.1_2 + openssl@3-3.6.4_1 +
  zlib-ng-compat-2.3.3_2）自举，修复 Cellar 路径 wrapper 脚本，LD_LIBRARY_PATH 补
  libssl/libcrypto/libz
- generate() 写 .cargo/config.toml：clang 链接器（OHOS 无 cc 符号）+ rsproxy.cn
  sparse 镜像（设备无 crates.io CA bundle）+ net 容错（retry 10 / timeout 600 /
  low-speed-limit 1）

## 补丁 0001 — workspace 缩容 + 随附锁文件（第 6 轮定稿）

- 演进史：v1 只删 4 个零引用 dev-deps（boring/boring-sys/clap/criterion，rust/core/src
  全树 grep 实证零引用）；v2 加删根 [patch.crates-io] 段（第 4 轮真机实证 patch 的
  git 源在每次 cargo 依赖解析时都 git fetch，卡在 "Updating git repository
  signalapp/boring"）；v3（定稿）再缩 workspace + 随附 Cargo.lock
- **根因链（第 5 轮真机实证）**：上游 workspace 有 25 个成员，bridge/* 经
  workspace.dependencies 直接 git 依赖 boring-signal/tokio-boring-signal
  （signalapp/boring，含 boringssl 子模块）与 spqr（SparsePostQuantumRatchet）。
  Cargo.lock 是 workspace 级锁：只要 manifest 与锁有任何失配，cargo 就重解析
  **整个 workspace**，解析器必克隆上述 git 仓库读 manifest（设备/CI 无法访问
  github，卡死在 "Updating git submodule https://github.com/google/boringssl.git"）。
  第 5 轮实证：patch 段已删、dev-deps 已删，cargo build 仍去拉 boring——因为
  随附的原版锁与改动后的 manifest 失配，触发了全 workspace 重解析
- 定稿方案（三件套，缺一不可）：
  1. members 缩到 ["rust/core"]（default-members 同缩）+ 删 3 个 git workspace
     依赖行 + 删 [patch.crates-io] 段 + 删 4 个零引用 dev-deps
     → 解析图零 git 依赖，即使重解析也只走 rsproxy registry（真机可达）
  2. 随附重生成的 Cargo.lock：Windows 侧（rustup 1.98.1 + rsproxy sparse）从
     上游原锁抽 libsignal-core 依赖闭包（98 包），再 cargo update --precise 把
     cargo 抬高的 27 个包逐包钉回上游原锁版本（feature 集收缩正当剔除 18 包），
     `cargo check --locked -p libsignal-core` + `cargo test --locked --lib
     --release` 25/25 实证锁即当前
     → 真机零重解析、依赖版本与上游锁零漂移
  3. 全链加 --locked：一旦失配立即报错，而不是静默去克隆 github 卡死
- 补丁不触及任何被测代码；test_package 对重新下载的 pristine tarball 应用同一补丁
- **行尾坑（破案）**：上游 tarball 的 Cargo.toml/rust/core/Cargo.toml 是 CRLF、
  Cargo.lock 是 LF。早前手写补丁（LF 上下文对 CRLF 文件）被 git apply 以
  "patch does not apply" 拒绝——行尾混写就是那个"未解之谜"的根因。定稿：补丁
  全文 LF，主配方 source() 与 test_package 打补丁前先把 3 个待补丁文件统一成
  LF（LF↔LF 在 git apply/GNU patch/patch-ng 三系 patcher 下全部实证通过）。
  另：patch-ng 1.19.x 解析 git 格式补丁时路径已预剥 a/ 前缀，conan 默认
  strip=1 会二次剥离导致失败 → 补丁采用纯 unified 格式（无 diff --git/index
  头，保留 --- a/X +++ b/X），三系 patcher + strip=1 全兼容

## rlib 交付设计（仓库首个 Rust 库包）

- package() 交付 lib/：liblibsignal_core.rlib + liblibsignal_debug.rlib + deps/ 下
  全部传递依赖 rlib（哈希后缀名，rustc -L dependency 按 crate 名解析），
  **哈希 rlib 平铺进 lib/ 顶层**：conan copy 保序会把 deps/ 子目录一并带进
  package（真机第 6 轮实证 → probe 报 rlib closure incomplete），而 rustc
  -L dependency 只在单一目录解析哈希名、deps/ 子目录不会被搜索 → 增加
  `copy(self, "*.rlib", src=target_dir/deps, dst=lib/)` 平铺拷贝（第 7 轮定稿）
- **proc-macro .so 必须同交付**（第 7 轮真机破案）：deps/ 里还有
  zerocopy_derive/derive_more_derive/thiserror_impl 等 proc-macro crate 的
  哈希后缀 .so（--crate-type proc-macro 只产 .so、元数据在 .so 内）。消费者
  rustc 解析 rlib 闭包时对每个传递依赖做全图元数据加载：只拷 *.rlib 时
  probe 报 "can't find crate for `zerocopy_derive` which `libsignal_core`
  depends on"（use 式代码里报错会被掩蔽成顶层 crate 名——第 7 轮用
  `extern crate` 改写 + RUSTC_LOG=rustc_metadata=info 逐层定位）。定稿：
  `copy(self, "*.so", src=target_dir/deps, dst=lib/)` 一并平铺；test.sh 闭包
  检查加 libzerocopy_derive-*.so 探针
- **裸 rustc 不读 RUSTFLAGS**（第 8 轮真机破案）：RUSTFLAGS 是 cargo 的
  变量（cargo 转递给 rustc），直接调 rustc 时被完全忽略。第 8 轮 probe
  编译全闭包解析通过、链接阶段 rustc 回退默认链接器 cc → EACCES
  （OHOS 无 cc 符号）。定稿：test.sh 显式传 `-C linker=$CC`
  （test_package _build_env 已把 CC 解析为 clang）
- Rust 消费者：
  `rustc --edition 2024 --extern libsignal_core=<pkg>/lib/liblibsignal_core.rlib -L dependency=<pkg>/lib probe.rs`
- C/C++ 消费者不能直接链 rlib（需 Rust 运行时/panic 处理）——package_info 仅声明 libdirs
- probe.rs 只使用上游公开 API（lib.rs pub use 面 + curve pub 模块），不依赖任何外部
  crate 类型命名，25 项断言覆盖 VERSION/try_scoped/derive_arrays/E164/DeviceId/
  ProtocolAddress/ServiceId(Aci/Pni 下转+字符串解析)/curve(KeyPair 生成+X25519 一致性+
  序列化往返)

## 上游测试（test_package 阶段）

- `cargo test -p libsignal-core --lib --release`：25 个 src 单测
  （address 12 + curve 7 + curve/curve25519 4 + e164 2），core 无 tests/ 目录
- --lib 天然排除 doc-tests 空阶段（OHOS Harmonybrew 工具链无 rustdoc，martin/1.13.0
  同仓库先例判定平台限制；core 0 doctest）
- 补丁应用在 test_package 用 conan.tools.files.patch（patch-ng，纯 Python，
  与主配方 source() 的 apply_conandata_patches 同机制同参数；设备 git 虽实证
  可用，但 CI worker 的 git 加载 libz.so 失败——见下节第 13 轮）
- HMBS 标记：HMBS_TEST_PACKAGE_RESULT 由 test.sh 打印（rustc-probe 25 断言）；
  HMBS_UPSTREAM_TEST_RESULT 由 test_package/conanfile.py 打印（cargo 框架输出解析，
  discovered==executed==passed+failed 对账口径）

## CI 门禁 L0d — test() 必须经 self.run 执行（第 10 轮整改）

- CI 首次构建（#63369）L0d 挂：`test() method has no self.run() call — likely a
  stub`（stub_test_method）。门禁是**静态检查**：test() 源码里没有 `self.run(`
  调用即判 stub，即使 subprocess.run 实际执行了测试也照样挂。
- 整改：消费者探针（test.sh）改经 `self.run('<CONFIG_SHELL> "test.sh" "<libdir>"',
  env=None)` 执行，与已合入先例 2048.c/1.0.3 同款包法（CONFIG_SHELL 包住脚本，
  self.run 经 shell=True 走 /bin/sh -c）。
- **conan 2.29 run() 参数语义（真机第 10 轮实证）**：env 只接受 env-file 名
  列表（"conanbuild"/"conanrun" 或自定义 env 文件），传 dict 直接
  `AssertionError: env argument to ConanFile.run() should be a list`；且默认
  ignore_errors=False——非零退出码 run() 自己 raise，不用手工查 rc。环境注入
  改走 `os.environ.update(env) + env=None`（不触发 conan env-file 机制，
  PATH/CC/TMPDIR 全部原样生效）。
- 上游 cargo test 保留 subprocess.run：self.run 的输出只进 conan 输出流，无法
  交回 Python 解析 "test result:" 行（HMBS_UPSTREAM_TEST_RESULT 标记必须由
  配方代码解析真实 passed/failed 数，不能委托）。
- 连带观察：AI 检视因 diff 过大跳过（9 文件 14930 行，主体 = 补丁随附的
  重生成 Cargo.lock），属预期；人工审查不受影响。

## cargo config 发现语义 — generate() 必须写进 source_folder（CI #63478 实证，第 12 轮整改）

- CI 首次真正执行构建（#63478，SHA d9ec4d37）在 build() 阶段挂：cargo 回退
  **官方 crates.io registry**（日志 "Updating crates.io index" 无镜像名 +
  下载 URL 直指 static.crates.io），syn v2.0.118 下载 "transfer too slow:
  failed to transfer more than 10 bytes in 30s"（0 字节）连挂 30 次重试
  → cargo exit 101 → build() check_call 抛错
- 根因：build() 用 `cwd=self.source_folder` 调 cargo，而 generate() 把
  .cargo/config.toml 写进 **build_folder**——cargo 只从 cwd 及祖先目录发现
  项目级 config，build_folder 不是 source_folder 的祖先，镜像配置永不生效
- 真机此前 11 轮全绿是假象：device ~/.cargo 无 config.toml（第 12 轮前实测
  确认，只有 registry/git 缓存目录），build() 阶段同样走官方 crates.io——
  设备链路好（_build_env 已指 SSL_CERT_FILE + 网络可达）所以一直侥幸通过；
  ls-create9.log 里的 `rsproxy-sparse` 下载行全部来自 **test_package 阶段**
  （其 config 写在 src_root=cwd，发现语义正确，一直生效）
- 整改：generate() 把 .cargo/config.toml 同时写进 **source_folder** 与
  build_folder（后者保留兼容不同 conan 版本布局）
- 验证口径（第 12 轮）：`CARGO_HOME=$HOME/tmp/ls-cargo-home12`（全新空目录）
  下真机 conan create——屏蔽任何用户级配置 + 冷 registry 缓存，等价 CI 条件，
  必须全链走 rsproxy 才证明整改有效（若只复用暖缓存真机验证，会把假象带进 CI）
- 第 12 轮实录：首跑冷缓存 rsproxy 全量下载成功（报错路径
  `ls-cargo-home12/registry/src/rsproxy.cn-e3de039b2554c837/...` 实证镜像
  生效），编译中挂共享设备进程配额 fork EAGAIN（os error 11，记忆坑位：
  孤儿吃满进程配额；ps 540 进程属他人任务，勿杀）；`CARGO_BUILD_JOBS=2`
  重跑 → RC=0 + 双 HMBS passed 25/25 + package created。EAGAIN 为设备环境
  问题、与配方无关（CI 无此限制），不改配方

## test_package 补丁改用 patch-ng — CI #63565 git 无法加载 libz.so（第 13 轮整改）

- CI #63565（SHA 4854b3a3 整改后首次重跑）：build 阶段全绿（rsproxy 镜像生效、
  编译+打包通过，generate() 双写整改 CI 实证 ✓），消费者探针 25/25 ✓，但挂在
  test_package 的上游测试：`_upstream_source()` 里 subprocess git apply 报
  rc=127 "Error loading shared library libz.so: (needed by /data/service/hnp/bin/git)"
  ——CI worker 的 git 二进制缺 libz.so，而设备 git 可用（环境分叉的又一实证）
- 整改：test_package 打补丁改走 `conan.tools.files.patch`（patch-ng 纯 Python，
  无外部二进制依赖），与主配方 source() 的 apply_conandata_patches 同机制
- **conan 2.29 patch() 源码实证（设备侧 inspect）**：默认 strip=0；
  apply_conandata_patches 不传 strip → 主配方实际以 strip=0 应用补丁
  0001，在 CI #63565 build 阶段与真机第 6-12 轮全部成功。故 test_package
  必须同样不传 strip（strip=1 会二次剥离 a/ 前缀导致失败）
- 早前 notes 记"conan 默认 strip=1"有误，已纠正：conan 2.29 patch()
  签名默认 strip=0（设备读 conan/tools/files/patches.py 原文确认）；
  纯 unified 格式补丁 + strip=0 是 CI/真机双实证的稳妥组合
- 连带纪律：test_package 的 conan create 必须 `-pr ohos-aarch64`
  （~/.conan2/profiles/，os.version=6.0），裸跑会落到 default 自动探测
  profile（无 os.version），缓存的第 12 轮二进制被判
  "Invalid: settings.os.version value not defined"（第 13 轮首跑实录）
- 第 13 轮实录（带 -pr ohos-aarch64）：全量重建（Forced build from
  source，generate()+source()+build()+package() 一并复验）RC=0；
  conan 日志 `(test package): Apply patch (file)` 实证 patch-ng 打补丁
  路径生效；PROBE_ASSERTS=25 FAILS=0 + HMBS_TEST_PACKAGE_RESULT passed
  25/25 + upstream "test result: ok. 25 passed; 0 failed" +
  HMBS_UPSTREAM_TEST_RESULT passed 25/25
- 第 14 轮实录（锁补丁拆分后首个全量轮，2026-09-29，日志 ~/tmp/
  ls-create14.log）：全量重建 RC=0；source() 与 test_package 各一次
  Apply patch（84 行 manifest 补丁，patch-ng），随附锁覆盖后 cargo
  build/test --locked 零失配零 git 解析（build 28.69s / test 57.01s，
  Finished 无 Updating 行）；PROBE_ASSERTS=25 FAILS=0 +
  HMBS_TEST_PACKAGE_RESULT passed 25/25 + upstream "test result: ok.
  25 passed; 0 failed" + HMBS_UPSTREAM_TEST_RESULT passed 25/25。
  日志 grep error/fail 的 uboot 报错经核对为共享 PTY 串扰（另一用户
  构建 uboot/2026.07 的 stderr 混入会话输出，grep -c uboot 日志文件
  =0），本包区段内无任何 error

## Harmonybrew bottle 镜像换代（真机首轮 404 实录）

- 首轮真机 build() 阶段 _bootstrap_rust_toolchain 404：argc/1.24.0 先例里的
  rust-1.97.1 / openssl@3-3.6.3 bottle 已被镜像清理（zlib-ng-compat-2.3.3_1 尚存）
- 镜像无目录列表（S3 NoSuchKey），版本爆破低效；权威来源 = Harmonybrew 的
  homebrew-core formula 仓库（atomgit.com/Harmonybrew/homebrew-core）：
  Formula/r/rust.rb、Formula/o/openssl@3.rb、Formula/z/zlib-ng-compat.rb 的
  stable version + revision + bottle sha256 即 bottle 文件名（版本_修订号）
- 换代后当前（2026-09-28）：rust-1.98.1_2、openssl@3-3.6.4_1、zlib-ng-compat-2.3.3_2，
  三个 URL 均 200 实证
- 教训：bottle URL 的版本号必须跟 formula 仓库 current revision 走；先例配方里的
  旧 URL 过期是常态，真机轮会原形毕露（CI 沙盒自带工具链，自举路径只跑真机）
- 连带发现：新瓶（1.98.1_2）bin/ 直接放 ELF（cargo 23MB ELF），不再有旧瓶
  （1.97.1）的 wrapper 脚本 + cargo.real 拆分层 → 自举搜索逻辑须兼容两种布局：
  先找 cargo.real（旧），回退到非 #! 的 cargo（新）；wrapper 修复循环天然跳过
  ELF 与无 .real 同级的 #! 脚本（rust-gdb 等辅助脚本不受影响）
- 最终取 rust-1.98.1 **r0** 而非 formula current revision r2：真机实测 r2 的
  cargo NEEDED = libgit2.so.1.9/libssh2.so.1/libssl.so.3/libcurl.so.4/
  libsqlite3.so.0（rc=127 + 逐条 loader 报错），要补 curl→nghttp2/nghttp3/
  ngtcp2/brotli/libidn2/zstd 等 12+ 个 bottle 传递闭包；r0 的 cargo.real NEEDED
  仅 libc/libcrypto/libssl/libz（Windows 侧 strings 实测），3 瓶集全覆盖。
  版本号同为 1.98.1 = 上游 rust-toolchain 钉的版本，r0 镜像仍 200 在服；
  若未来 r0 被清，需按 curl 闭包补齐或改选新 revision（记录于此）

## sha256 说明

- conandata sha256 = codeload 下载（github.com/archive 302 重定向到 codeload，
  字节一致）；真机轮用 github.com 直连复核 sha256 后确认（记录于此）

## 路径 B 知识草稿（计划）

- 草稿1: Rust workspace 切片构建（-p 选成员、path 依赖隐式入图、[patch.crates-io]
  git 补丁源规避）
- 草稿2: Rust rlib 闭包交付语义（哈希后缀 rlib + --extern/-L dependency 消费者链接）
- 草稿3: rust-toolchain 文件与 MSRV（cargo 直调忽略 rust-toolchain；rust-version 声明
  为编译下限）
- 草稿4: workspace 级锁的失配陷阱（manifest 改动 → 全 workspace 重解析 → git
  依赖克隆；对策 = 缩 workspace + 随附重生成锁 + --locked）

## 锁补丁拆分（mm-yy rule6 整改，2026-09-29）

- 背景：mm-yy pc-pr-review FAIL 三项——rule1 上游测试用例通过率字段缺失、
  rule4 解析 0/25（prose 数字不可机读）、rule6 AI 检视跳过（14930 可审行，
  9 文件，预估 13 轮分片超出处理范围）
- rule6 根因：老补丁 0001 = 6718 行（其中 6575 行锁替换 hunk），主配方与
  test_package 各一份 = 14280 行，占可审行 95%+
- 整改：锁与补丁拆分——
  - patches/0001 瘦身为 84 行纯 manifest hunk（members 缩容/删 git 依赖/
    [patch.crates-io]/dev-deps）
  - Cargo.lock（80 包 701 行）作为独立文件随配方 exports_sources 交付：
    主配方 source() 打补丁后 shutil.copy 覆盖上游锁（export_sources_folder
    → source_folder/Cargo.lock）+ package() 把锁随包分发到 package 根；
    test_package 从打包产物取锁（package_folder/Cargo.lock →
    src_root/Cargo.lock，与主配方字面上同一份文件——MR 里锁只有一份副本）
  - 语义不变性实证（verify_lock_split.py）：老全量补丁 patch-ng strip=0 在
    pristine 锁上的应用结果 vs 随附锁逐字节一致（18141 字节，
    LOCK_BYTE_IDENTICAL=True）；84 行新补丁在 pristine manifest 上应用
    True、members 只剩 rust/core（检查须限定 members 正则——裸 grep
    "rust/bridge" 会命中根 Cargo.toml 注释行造成误报）
- 二轮缩容（AI 检视 7874 行仍跳过后）：删 test_package 自带锁副本
  （-702 行），test_package 改读 self.dependencies["libsignal-core"]
  .package_folder/Cargo.lock（test() 早已用该通路取 libdir，成熟路径）
- 三轮缩容（AI 检视仍在 7874 行量级——破案：可审行大头不是锁而是
  **test_package 自带的老全量补丁副本**（test_package/patches/0001 仍为
  7140 行老版，二轮缩容没动到它）：同步替换为主配方同款 84 行
  manifest-only 补丁（md5 6face3ee 逐字节相同，-7056 行）。语义不变：
  test_package 应用老补丁时，锁 hunk 的效果随后就被 package_folder 取来
  的重生成锁整体覆盖抵消，换成 manifest-only 版净效果完全一致
- 第 16 轮实录（三轮缩容后首个全量轮，2026-09-30，日志
  ~/tmp/ls-create16b.log，日志 ~/tmp/ls-create16.log 为 v1 失败轮）：
  v1 挂 test_package 自举——`_find_cargo` 一个候选都未命中（设备
  harmonybrew/usr/local/.cargo/hnp 均无 cargo），走了 bootstrap 路径，
  在重写 bottle wrapper 时报 PermissionError EACCES（bottle 的 bin/cargo
  等包装脚本带 **0555 无写位**，OHOS 对 owner 也严格按权限位拒绝写入）；
  根因=此前 14 轮 test_package 从未真正自举过（_find_cargo 一直命中
  预装工具链，bootstrap 只在主配方 build 里跑过且当时环境不同），
  wrapper 重写代码对只读文件不设防。修复=重写前
  `os.chmod(wrapper, st_mode | 0o200)` 补写位（主配方与 test_package 同
  改）；v2 全量重建全绿：主配方因 conanfile 变更重建（新包目录
  libsi873aff93e6f72）并**走 bootstrap 实证修复**——重写后 wrapper
  mode=rwxrwx---、内容为 "repaired by libsignal-core recipe" exec 本地
  .real，build 用该 cargo.real 完成；test_package 探针 25/25 + 上游
  25/25 双 HMBS passed、Apply patch (file) 实证 84 行补丁生效、
  --locked 零失配
- 第 15 轮实录（单一锁副本 + package_folder 取锁后首个全量轮，
  2026-09-29，日志 ~/tmp/ls-create15.log）：全量重建 RC=0；探针 25/25 +
  上游 25/25 双 HMBS passed（build 28.22s，--locked 零失配）；包目录
  libsidd88c500150bc/p/Cargo.lock md5=10829be0… 与导出锁完全一致——
  package() 随包分发生效、test_package 从包内取锁路径实证（上游测试
  --locked 通过即证明锁复制进 src_root 且内容正确，否则必失配报错）
- 抽取踩坑：老补丁锁区实际有**两个 hunk**——hunk1 新侧以上下文行
  [[package]] 收尾，hunk2（@@ -6579,112 +700,3 @@ name = "zeroize"）删
  112 行老尾包；`name = "zeroize"` 落在两个 hunk 之间（hunk2 的 section
  header 即证），patch-ng 对 hunk 外行按上下文直传保留，行级抽取必丢 →
  抽完断言 [[package]] 紧跟 version = "1.9.0" 的锚点恰一个，插回夹缝行
- 净效果：可审 diff 约 -19750 行（-14280 补丁 -7056 test_package 旧补丁
  副本 +2×701 锁文件），AI 检视可完成（rule6 整改）；rule1/rule4 由 PR
  正文加显式通过率字段整改
