# DRAFT-wagyu-0.6.1-rust-legacy-lockfile-ohos-port：Rust 老锁文件（2015–2019）在 OHOS/modern rustc 上的组合修复，外加「未签名 libstd 在 loader 加载阶段被拒」盲区（预留条目 E674）

> Status: DRAFT（Reserved entry id **E674**，`tools/knowledge_id.py --claim --task wagyu-0.6.1`）  
> Source: wagyu 0.6.1 HarmonyOS PC 适配（任务卡 11791，2026-09-23）  
> Related: `DRAFT-below-ohos-unsigned-rust-toolchain`（同族前作，本条为三处增量）、E105/E154、E318、E509

## 背景

wagyu 0.6.1（https://github.com/howardwu/wagyu ）是 2019-09 发布的 Rust workspace
（根 crate + bitcoin/ethereum/model/monero/zcash + 内嵌过程宏 crate `field_derive`），
`Cargo.lock` 是 v1 格式、锁死在 libc 0.2.61 / cc 1.0.40 / getrandom 0.1.9 /
rustc-serialize 0.3.24。在 HarmonyOS PC（rustc 1.97.1，目标
`aarch64-unknown-linux-ohos`）上一次 `cargo build --locked` 会依次暴露**四个编译期
问题**，随后 `cargo test` 还会踩到**第五个运行期盲区**（与前四个正交）。

同族前作 `DRAFT-below-ohos-unsigned-rust-toolchain` 覆盖的是「预编译工具链的
**bin** 与 `librustc_driver` 签名 + cargo 运行库/CA」；below 的锁文件是现代的、
workspace 里也没有 in-tree 过程宏 crate，所以本条的五个问题它一个都没遇到。

## 现象（错误面，按暴露顺序）

```text
1) error[E0425]: cannot find type `c_char` in the crate root   （libc 0.2.61，662 个错误）
   error[E0573]: expected type, found `__SIZEOF_PTHREAD_COND_T` / missing `__SIZEOF_PTHREAD_RWLOCK_T`
2) getrandom-0.1.9/src/lib.rs: compile_error!("target is not supported, for more
   information see: https://docs.rs/getrandom/#unsupported-targets")
3) error[E0310]: the parameter type `T` may not live long enough
   --> rustc-serialize-0.3.24/src/serialize.rs: `impl<'a, T: ?Sized> Decodable for Cow<'a, T>`
4) rust-crypto 的 build script（gcc-0.3.55）: Internal error occurred:
   Failed to find tool. Is `cc` installed?
5) 测试期：Error loading shared library libstd-6cb83eb787a5e858.so: (needed by .../field_derive-*)
   随后一串 `Error relocating ...: ... symbol not found` → 测试 harness exit 127
   ——该 .so **就在 LD_LIBRARY_PATH 的目录里、可读、mode 0755**，路径排查全部徒劳
```

## 根因

1. **libc 0.2.61 没有 `target_os=ohos` 分支**——类型与常量定义整段不参与编译。
   必须 bump（`0.2.x` semver 兼容，ohos 支持自 0.2.13x 起）；同批把 cc
   1.0.40→1.0.41。**保持 v1 锁格式手改**（20 行改动、diff ±40 行；`cargo update` 会把整文件
   重写成 v4 格式，`--locked` 行为要重新验证、diff 面上千行）。metadata checksum
   直接取 `registry/cache` 里 `.crate` 文件的 sha256。
2. **getrandom 0.1.x（rand 0.7 传递依赖）没有 ohos 支持且 bump 无解**——0.1 系列
   最高 0.1.14 也没有；升 rand 0.8 牵动上游 API 属过度修改。正解：`cargo fetch`
   （fetch 即解包进 `registry/src`）之后、编译之前，对 registry 解包源打 7 处
   最小补丁（`lib.rs` 三处目标门 + `util_libc.rs` 三处 + `use_file.rs` 一处加
   `target_os="ohos"`，走 linux 的 `syscall(SYS_getrandom)` 路径）。补丁落**构建
   目录内的 CARGO_HOME**：不污染共享 `~/.cargo`，不碰 `.crate`（sha256 受锁文件
   校验），锚点找不到即抛错（不许静默未生效）。
3. **rustc-serialize 0.3.24 `Decodable for Cow` 缺 `'static` 约束**——modern rustc
   直接 E0310，0.3.25 仍未修，rust-crypto 0.2.36 传递依赖绕不开。impl 头补
   `+ 'static` 一行（rustc 自己给出的最小修复）。
4. **老 `gcc-0.3.55` build script 不认 `CC_<target>` 环境命名**，只在 PATH 找裸名
   `cc`（设备没有）。host==target==ohos 时把通用 `CC/CXX/AR/RANLIB` **和**
   `CC_aarch64_unknown_linux_ohos` 都指向 OHOS SDK clang 即可。
5. **未签名的 `rustlib/*/lib/libstd-*.so` 在 dlopen 加载阶段被 OHOS loader 拒绝**，
   但报错是 `Error loading shared library libstd-*.so`（文件明明在搜索路径里且
   可读），与 below 条目里 bin 的 `Permission denied`（errno 13，execve 阶段）是
   **两个不同的失败面、两种不同的误导**。只有 **host 侧 in-tree proc-macro crate
   （本工程 `field_derive`）的测试 harness** 动态链接 libstd 才会踩到——目标侧产物
   （`bin/wagyu`、各 crate 的 harness）静态链接 std，`NEEDED` 只有 `libc.so`，
   所以 below（无 in-tree 过程宏 crate）与最终交付物都不受影响。正解：镜像
   rustlib——目录建实、非 `.so` 软链、`*.so` 复制并自签（本类 dist 通常只有
   libstd 一个 `.so`，5.8MB），签名后同一 harness 立即可跑（实测
   `test_exp: test`）。

### 附带两个 W0 级陷阱（同条登记）

- **同名 tag 与 branch 并存**：`refs/tags/v0.6.1`（=9d2bd3a，发行内容，201 文件）
  与 `refs/heads/v0.6.1`（=70250ad）同名，`git clone --branch v0.6.1` **优先命中
  branch**，取到的树与发行内容逐文件不同且毫无告警。取源必须用
  `archive/refs/tags/<tag>.tar.gz` 并以该 tarball 的 sha256 为准。
- **Harmonybrew bottle pin 会随 revision 漂移 404**：历史配方 pin 的
  `zlib-ng-compat-2.3.3_1`、`ca-certificates-2026-08-13`、`rust-1.97.1`、
  `openssl@3-3.6.3` 实测 404，`_2`/`_1` 新版 200。pin 必须当日实测可达并自行
  下载复核 sha256，不能照抄历史配方（below 草稿里的 fallback URL 现已是 404）。

## 处置（方案层）

- `patches/0001-Cargo.lock.patch`：libc/cc 两个包的 semver 内 bump，保持 v1 格式
  （40 行 diff）；`patches/0002-main.rs-version-string.patch`：上游 0.6.1 tag 漏
  bump 硬编码 `.version("v0.6.0")`（且 `DisableVersion` 禁了 `--version`），产物
  help 头部自报版本必须与打包版本一致。
- 配方 `build()` 顺序：`apply patches → rust env（签工具链+镜像 rustlib+运行库
  bottle+CC 双保险+CARGO_HOME 内置）→ cargo fetch --locked → registry 补丁（锚点
  硬校验）→ cargo test（强制，逐套件解析，非 PASS 即失败）→ cargo build → 产物
  codesign 标记校验/补签`。
- 消费端（test_package）：A 组 8 项「真实生成钱包」端到端压 getrandom 补丁
  （bitcoin×2/ethereum/testnet × JSON 结构断言）+ 版本自证；B 组 4 项鸿蒙平台
  特性（AArch64 / musl loader / code signature / 产物完整性）。
- 上游测试口径：源码 `#[test]` 宏数 **608** = 框架注册数（逐套件 `running N tests`
  求和）**608**，两口径一致无差额；doc-tests 7 套件注册 0。

## 查重与增量

| 既有条目 | 覆盖内容 | 本条增量 |
|---|---|---|
| `DRAFT-below-ohos-unsigned-rust-toolchain` | bin/librustc_driver 的 exec/dlopen 签名、cargo 运行库 bottle、CA | ① rustlib **libstd** 加载期拒绝的误导性报错面；② 2019 锁文件依赖族 × modern rustc × ohos 的四连编译错与「getrandom 0.1 bump 无解」结论；③ 同名 tag/branch 取源 + bottle pin 漂移 404 |
| E105 / E154 | rustup 不识别 HarmonyOS（工具链来源） | 未重复，作为 fallback 链的上位事实引用 |
| E318 / E509 | go test 临时 ELF 未签名 / harmonybrew OpenSSL | 场景不同（loader 加载阶段 + 动态 std） |

## 验证

- 2026-09-23 设备探索轮（rust 1.95.0 本地工具链）：四步修复后
  `cargo build --release --locked` rc=0；`cargo test --workspace` **608/608 全过**
  （bitcoin 175 / ethereum 74 / model 12 / monero 91 / zcash 255 + field_derive 1，
  doc-tests 0），`wagyu --help` 与真实钱包生成 rc=0。
- 2026-09-23 `conan create archives/w/wagyu/0.6.1 -pr:h/-pr:b=ohos-aarch64`（配方
  完整路径：签名工具链 + 镜像 libstd + 运行库 bottle + registry 补丁 + 强制上游
  测试 + test_package 12/12）——见 PR 正文与采信轮日志（`reports/conan-create.log`）。
- 定案判据：`grep -ac codesign <toolchain>/lib/rustlib/*/lib/libstd-*.so > 0`
  且 `cargo test --workspace` 第一个套件（field_derive）不再 exit 127。
