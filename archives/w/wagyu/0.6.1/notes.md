# wagyu 0.6.1 适配笔记

## 软件信息
- 上游仓库: https://github.com/howardwu/wagyu （GitHub 现名；`ArgusHQ/wagyu`、`AleoHQ/wagyu` 为同仓 301 重定向别名，三个 URL 的 tag archive 字节一致）
- 上游 tag: `v0.6.1`（轻量 tag → 提交 `9d2bd3aab61657553c562ba8436f4379c7893a87`），源码 sha256 `2458b3d49653acd5df5f3161205301646527eca9f6ee3d84c7871afa275bad9f`
- 语言: Rust（edition 2018，100%；workspace 7 个 crate：根 wagyu + bitcoin/ethereum/model/monero/zcash + zcash 内嵌过程宏 crate field_derive）
- 构建系统: cargo workspace（无 configure/cmake/make 入口 → manifest `build.system: custom`）
- 编译环境: HarmonyOS PC（aarch64，HongMeng Kernel），rustc 1.97.1（`rust-toolchain/1.97.1`，host target = aarch64-unknown-linux-ohos），clang 15（OHOS SDK `aarch64-unknown-linux-ohos-clang`）
- 编译日期: 2026-09-23

## 产物形态澄清：不是 header-only
任务卡「领前必补」提示「header 为主先确认库产物」。**实核结论**：wagyu 是 Rust workspace，
根 crate 同时声明 `[lib] path = "wagyu/lib.rs"` 与 `[[bin]] name = "wagyu"`——**交付物是单个
OHOS aarch64 可执行文件 `bin/wagyu`（约 6.0 MB），不产出 .h/.a/.so**（G4/L2/L4 均按可执行产物
口径检查）。上游不存在 header-only 形态；「库产物」由成员 crate 的 rlib 承担，仅在构建树内出现，
不进包。

### 取源陷阱（版本实核必读）
上游**同时存在同名 tag 与 branch**：`refs/tags/v0.6.1` = `9d2bd3a`（发行内容，201 文件），
`refs/heads/v0.6.1` = `70250ad`（不同内容，含额外测试/文档差异）。`git clone --branch v0.6.1`
会**优先命中 branch**，实测 clone 出的树与 tag archive 逐文件 diff 不一致。取源必须用
`archive/refs/tags/v0.6.1.tar.gz` 并以该 tarball 的 sha256 为准（`git archive` 出的 tag 树与
该 tarball 201 文件逐文件 sha256 一致，已自证）。

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态统计 + 框架注册，双口径）

| 测试类型 | 用例数 | 来源 |
|----------|--------|------|
| 单元测试（`#[test]`） | 608 | 全 workspace 各 crate `src/` 内嵌测试模块 |
| 集成测试（`tests/` 目录） | 0 | 上游无独立 `tests/` 集成测试目录 |
| doc-tests | 0 | 7 个 Doc-tests 套件注册 0 个用例（探索轮用含 rustdoc 的完整工具链实跑取证；配方内因 rust-toolchain 包缺 rustdoc 组件改用 `--all-targets`，cargo 明示该模式不含 doctest——注册 0 故不漏用例） |
| **合计** | **608** | |

按 crate 分布（源码 `#[test]` 宏数 = 框架注册数）：

| crate | 源码宏数 | 框架注册（`running N tests`） | 结果 |
|-------|---------|------------------------------|------|
| wagyu-bitcoin | 175 | 175 | 175 passed |
| wagyu-ethereum | 74 | 74 | 74 passed |
| wagyu-model | 12 | 12 | 12 passed |
| wagyu-monero | 91 | 91 | 91 passed |
| wagyu-zcash（含内嵌 field_derive 过程宏 crate） | 256 | 255 + 1（field_derive 单独套件） | 256 passed |
| wagyu（根 lib / bin） | 0 | 0 + 0 | 0 |
| **合计** | **608** | **608** | **608 passed** |

> 两种口径（源码宏数 / 框架注册数）**完全一致（608 = 608），无差额需归因**。
> 取数命令：
> - 源码宏数：`grep -rn '#\[test\]' --include='*.rs' <src> | wc -l` → 608
> - 框架注册数：`cargo test --workspace` 日志逐套件 `running N tests` 求和 → 608
>   （取自含 rustdoc 的完整工具链全量运行：`test result:` 共 15 行 = 8 个单元套件 + 7 个 Doc-tests 套件；
>    配方内 `--all-targets` 运行的是其中 8 个单元套件，doctest 注册 0 已另行实证）

### 2. 上游测试实际运行（本机 = HarmonyOS PC）

- 运行方式（配方 `build()` 内强制执行，非 PASS 即硬失败）：
  `cargo test --release --target aarch64-unknown-linux-ohos --workspace --locked --all-targets`
  （`--all-targets` = 全部单元/集成/bench/example 目标、不含 doctest，原因见问题表 #6b）
- 运行环境: HarmonyOS PC 真机（host target 即 aarch64-unknown-linux-ohos，产物本机直跑）
- **结果：608 通过 / 0 失败 / 0 忽略 / 0 未运行，通过率 608/608 = 100%**

### 3. 非 PASS 项技术原因

无（FAIL=0、SKIP=0、NOT_RUN=0）。测试集为纯内存计算（钱包生成、椭圆曲线、助记词、Base58/Bech32
编解码），不依赖网络、TTY、文件系统特权，设备上全量可跑。

## 编译过程与平台适配

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libc 0.2.61` 662 个 E0425/E0573（`cannot find type c_char in the crate root` 等） | 2019 年锁文件的 libc 不识别 `aarch64-unknown-linux-ohos`（`target_os=ohos` 分支尚不存在），类型/常量定义整段不参与编译 | `patches/0001-Cargo.lock.patch`：libc 0.2.61→0.2.189、cc 1.0.40→1.0.41（semver 兼容 bump，**保持 v1 锁格式：20 行改动（diff ±40 行、19 个 hunk）**，`cargo --locked` 实测接受且不重写锁文件） |
| 2 | `getrandom 0.1.9` 报 `compile_error! target is not supported` | rand 0.7 传递依赖 getrandom 0.1 系列，其 `cfg_if` 目标分支没有 ohos；0.1 系列（最高 0.1.14）**至今无 ohos 支持，无法靠 bump 解决** | 配方在 `cargo fetch` 后对 **registry 解包源**打 7 处最小补丁（lib.rs 三处目标门 + util_libc 三处 + use_file 一处加 `target_os="ohos"`，走 linux 的 `syscall(SYS_getrandom)` 路径）；补丁落构建目录内 CARGO_HOME，不碰 `.crate` 校验、不污染共享 `~/.cargo`，锚点缺失即硬失败 |
| 3 | `rustc-serialize 0.3.24` E0310（`impl Decodable for Cow<'a, T>` 缺 `'static`） | 现代 rustc 对该 impl 的生命周期检查收紧；0.3.25 仍未修，rust-crypto 0.2.36 传递依赖无法 bump 绕开 | registry 源补丁：impl 头补 `+ 'static`（rustc 给出的最小修复） |
| 4 | `rust-crypto` build script 报 `Failed to find tool. Is cc installed?` | 其 build script 用老 `gcc-0.3.55`，**不认 `CC_<target>` 环境命名**，只在 PATH 找裸名 `cc`（设备无 cc） | host==target==ohos：把通用 `CC/CXX/AR/RANLIB` 与 `CC_aarch64_unknown_linux_ohos` 等**都**指向 OHOS SDK clang |
| 5 | `rust-toolchain/1.97.1` 包内 cargo/rustc 直接执行报 `Permission denied` | rust-lang 官方 dist 二进制无 code signature，OHOS 拒绝 execve 未签名 ELF（errno 13） | 配方把 cargo/rustc/librustc_driver 复制进 build folder 用 `binary-sign-tool -selfSign 1` 签名（幂等：已带 `codesign` 标记则跳过），其余 rustlib 负载软链 |
| 5b | `cargo test` 第一个套件（host 侧 field_derive）报 `Error loading shared library libstd-*.so` + 一串 `symbol not found`（exit 127） | **OHOS loader 同样拒绝加载未签名的 .so**：官方 dist 的 `rustlib/<host>/lib/libstd-*.so` 无签名，而 proc-macro crate 的测试 harness 动态链接 libstd（目标侧产物静态链接 std，NEEDED 只有 libc.so，不受影响） | `_mirror_rustlib()`：在签名工具链目录内镜像 rustlib——目录建实、非 `.so` 软链、`*.so` 复制并自签名（本 dist 仅 libstd 1 个 .so）。签后同一 harness 立即可跑（实测 `test_exp: test`） |
| 6 | 签名后 cargo 报 `Error loading shared library libssl.so` | cargo DT_NEEDED = libssl/libcrypto/libz，OHOS loader **忽略 DT_RUNPATH** | conandata `rust_runtime`：Harmonybrew `openssl@3 3.6.4` + `zlib-ng-compat 2.3.3_2` bottle（sha256 设备下载复核）注入 `LD_LIBRARY_PATH` |
| 6b | 单元套件 608/608 全过后，`Doc-tests field_derive` 报 `could not execute process rustdoc ... No such file or directory`，整条 `cargo test` rc=101 | **`rust-toolchain/1.97.1` 基础设施包不含 `rustdoc` 组件**（`bin/` 实测无 rustdoc，只有 man 页），doc-test 阶段必然失败 | 测试命令改 `--all-targets`（cargo help 明示 "does not include doctests"）；并用含 rustdoc 的完整工具链（gitcode rust-1.95.0）在探索轮实证 **7 个 Doc-tests 套件注册 0 用例**——排除 doctest 不漏任何用例，N=608 不受影响；已反馈 backlog 建议补组件 |
| 7 | 历史配方 pin 的 bottle 全线 404 | Harmonybrew 对象存储随 bottle revision 更新对象（`zlib-ng-compat-2.3.3_1`、`ca-certificates-2026-08-13`、`rust-1.97.1` 实测 404；`_2`/`_1` 新版 200） | 只 pin **当日实测 200** 的对象并自下载复核 sha256，不照抄历史配方 pin |
| 8 | `/tmp` 只读（device-facts §一.1） | 平台限制 | cargo `TMPDIR/TMP/TEMP` 全部指向 build folder 内 `tmp/` |
| 9 | `os.cpu_count()=20` 而 affinity=8（device-facts §一.7） | 容器配额 | `CARGO_BUILD_JOBS=4` 限并发，防超订 |
| 10 | CLI 自报版本 `v0.6.0` 与打包版本 0.6.1 不符 | 上游 0.6.1 tag 忘 bump `main.rs` 硬编码 `.version("v0.6.0")`，且 `AppSettings::DisableVersion` 禁掉了 `--version` | `patches/0002-main.rs-version-string.patch`（1 行 bugfix），test_package A1 断言 help 头部 `wagyu v0.6.1` 做版本自证 |

### 源码修改（入库）
- `patches/0001-Cargo.lock.patch`：libc/cc 两处 bump（20 行改动、diff ±40 行，保持 v1 锁格式，避免整文件重写）
- `patches/0002-main.rs-version-string.patch`：CLI 自报版本 1 行

### 不入库的构建期源修改
- registry 解包源补丁（getrandom 7 处 + rustc-serialize 1 处）：在配方 `build()` 内、`cargo fetch`
  之后执行，幂等锚点校验、锚点缺失即失败。属「下载依赖源的 OHOS 兼容化」，与 below 配方
  patch libbpf-sys 的先例同口径。

## 依赖版本
- 构建期（tool_requires）: `rust-toolchain/1.97.1`（ohpcd 制品仓真实在档，`conan install
  --tool-requires=rust-toolchain/1.97.1 --build=never -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`
  rc=0 实测，包 id `6b129b068851896169fae42d399fa922d239ce8a` / os.version=6.0）
- 构建期（运行共享库）: `openssl@3 3.6.4`、`zlib-ng-compat 2.3.3_2` Harmonybrew bottle（LD_LIBRARY_PATH）
- 运行期（Conan requires）: 无——纯 Rust 依赖树（158 个 crate，rsproxy.cn 稀疏索引拉取，
  Cargo.lock `--locked` 钉死）；secp256k1 捆绑的 C 源由 cc 直接编译，不引入 Conan 库依赖

## 验证结果

```bash
# 上游测试（配方 build() 内强制，非 PASS 即失败）
cargo test --release --target aarch64-unknown-linux-ohos --workspace --locked --all-targets
# → 8 个单元套件（不含 doctest）；608 passed / 0 failed / 0 ignored（见 reports/test-report.md）

# 消费端（test_package，12 项断言）
PACKAGE_FOLDER=<pkg> python3 test_wagyu.py
# → A1-A8 消费冒烟+真实钱包生成 8 项、B1-B4 鸿蒙平台特性 4 项，全部通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/wagyu` | ≈6.0 MB | OHOS aarch64（musl loader）可执行文件，带 OHOS code signature |
| `licenses/LICENSE-MIT` / `LICENSE-APACHE` | — | 双许可证文件 |

## 注意事项
- 上游 `wagyu --help` 头部在补丁 0002 后自报 `wagyu v0.6.1`；`--version/-V` 被上游
  `AppSettings::DisableVersion` 禁用（属上游设计，不改）。
- 生成钱包走真随机（`rand 0.7` → `getrandom` → `getrandom(2)` 系统调用），补丁 2 若失效会直接
  在编译期报错、不会静默假绿；test_package A4-A8 真实生成钱包做端到端验证。
