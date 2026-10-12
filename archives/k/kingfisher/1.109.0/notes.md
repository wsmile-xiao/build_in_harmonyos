# kingfisher 1.109.0 适配笔记

## 编译环境

- 构建系统：cargo（Rust 2024 edition，`rust-version = 1.96`；工作区 4 个 crate）
- 编译日期：2026-09-29
- 编译器：rustc/cargo 1.98.1（Harmonybrew，host/target 均 `aarch64-unknown-linux-ohos`）+ clang 15.0.4
- 依赖：0 个 Conan 制品依赖（Rust crate 依赖由 `Cargo.lock` 从 crates.io 拉取）
- 状态：built

## R47 语言预检（双口径证据留档 reports/）

| 口径 | 命令 | rc | detected | 证据 |
|---|---|---|---|---|
| 默认（task=cpp） | `lang-preflight kingfisher 1.109.0 --src $BUILD_SRC_DIR` | 2 | `rust`（`build_system=cargo`，`Cargo.toml name="kingfisher"`，源文件 271 个主体占比 90%） | `reports/lang-preflight-default.log` |
| 如实（task=rust） | 同上 `--lang rust` | 0 | `rust` — 语言匹配，继续主流程 | `reports/lang-preflight-rust.log` |

判定说明：上游**仓库**确为 Rust（检测器结论正确，如实采纳 `--lang rust`；先例
`archives/c/crunch64/0.6.2`、`archives/c/cargo-bash-completions/1.97.0`）。
`vendor/vectorscan-rs/` 内的 C/C++ 是 vendored 第三方引擎（795 个文件全在该目录，
`vendor/` 之外仅 3 个 testdata 样例），不改变主体语言判定。

## 编译步骤

```bash
# 1) 工具链：Harmonybrew 安装 Rust（worker 无系统 Rust）
brew install rust          # cargo/rustc 1.98.1，自带 aarch64-unknown-linux-ohos std

# 2) 环境（配方 generate()/build() 内自动完成，此处为手工复现命令）
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export RUSTFLAGS="-C linker=/data/service/hnp/bin/clang"
export BOOST_ROOT=$HOME/.harmonybrew                     # vendored Vectorscan 需要 Boost>=1.61
export OHOS_SDK_NATIVE=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native
export AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos=<overlay>  # 见问题 #3

# 3) 构建 + 上游测试
cargo build --release --locked
cargo test --release --no-fail-fast
```

最终配方用 `CARGO_TARGET_DIR=<build>/target` + `cwd=source_folder`（cargo 会向上
搜索 `Cargo.toml`，不固定会落错目录），并把 `target/release/kingfisher` 安装到
包内 `bin/`，在 OHOS 上用 `binary-sign-tool` 签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cargo build` 在拉取 crates.io 稀疏索引时大量 `transfer too slow` 超时 | 直连 `index.crates.io` 在本机过慢 | 写入 `<src>/.cargo/config.toml` 使用 rsproxy 稀疏镜像（`sparse+https://rsproxy.cn/index/`）并指定 CA；`CARGO_NET_GIT_FETCH_WITH_CLI=true` 让 git 依赖走 git CLI |
| 2 | Vectorscan build.rs panic：`Failed to get C++ compiler version: No such file or directory` | 该脚本用 `Command::new("c++")` 探测编译器，OHOS 只有 `clang++` | 建 `cc`/`c++` 兼容别名（R5：`rm -f` 后 `ln -s`）加入 PATH |
| 3 | `ld.lld: error: undefined symbol: aws_lc_0_41_0_bignum_copy_row_from_table / ChaCha20_ctr32_neon / aes_hw_encrypt …`（最终链接失败） | ① SDK 工具链把 `CMAKE_SYSTEM_PROCESSOR` 设为普通变量、且 `set(UNIX TRUE CACHE BOOL FROCE)` 拼写错误（FROCE≠FORCE），CMake 最终没有系统处理器 → aws-lc 推导 `ARCH=generic` 并**静默丢弃全部 s2n-bignum `.S` 汇编**（CMake 输出实证：`Detected generic linux platform. No assembly files will be included.`）；② SDK 的 `llvm/bin` 缺 `llvm-ranlib` | 生成工具链 overlay：`include(ohos.toolchain.cmake)` 后把 `CMAKE_SYSTEM_PROCESSOR` 以 `CACHE ... FORCE` 钉为 `aarch64`、补 `UNIX TRUE`，并用 `llvm-ar s` 包装出 `llvm-ranlib`；通过 `AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos` 注入 |
| 4 | 构建成功但二进制一执行就 `SIGSEGV`（exit 139），`--version`/`--help` 全部崩溃；未签名执行则被拒 | 上游默认启用 mimalloc 的 **`override` feature** → `MI_MALLOC_OVERRIDE` 覆盖系统 malloc/free，与鸿蒙内存管理机制冲突（**知识条目 E210**） | 补丁 `0001-mimalloc-disable-override.patch` 去掉该 feature（mimalloc 仍作普通分配器）；实测 `rc=139 → rc=0`，`kingfisher --version` 输出 `kingfisher 1.109.0` |
| 5 | vendored Vectorscan CMake 报 `Boost 1.57.0 or later not found` | 系统无 Boost 头文件 | `brew install boost`（1.92.0）并以 `BOOST_ROOT`+`CPATH` 指向 |
| 6 | 二进制未签名时执行报 `Permission denied` | OHOS 要求 ELF 必须经 `binary-sign-tool` 签名 | `package()` 中对 `bin/kingfisher` 执行 `--remove-section .codesign` + `sign -selfSign 1` |
| 7 | 测试二进制加载失败：`git_error_last / git_error_clear: symbol not found` | `libgit2.so.1.9` 在 Harmonybrew 前缀，musl 加载器忽略 `DT_RUNPATH` | 运行/测试时把 `~/.harmonybrew/lib` 加入 `LD_LIBRARY_PATH`（配方在 build 前写入） |
| 8 | 测试报告 `repository path '…' is not owned by current user; code=Owner (-36)` | libgit2 的 `safe.directory` 所有权校验；worker 临时目录为组所有（uid 20001006 / gid 1006） | 测试环境设置 `safe.directory = *`（隔离 HOME 的 `.gitconfig`），不改用户全局配置 |
| 9 | `--offline` 的 `cargo generate-lockfile` 报 `no matching package named 'gix' found` | 本机 cargo registry 走 rsproxy 稀疏索引，`--offline` 索引缓存不完整（同一工作区自身也会报 `aws-config` 缺失） | 判定为环境能力限制，非适配缺陷；该用例在 MANIFEST 中声明豁免 |

## 源码修改

- `patches/0001-mimalloc-disable-override.patch`：`Cargo.toml` 中
  `mimalloc = { version = "0.1.52", features = ["override"] }` →
  `mimalloc = { version = "0.1.52" }`。**唯一源码改动，仅 1 行**。
  无平台宏注入（不违反 PF5/R8）；产品逻辑、API、上游测试用例均未修改。

## 依赖版本

- Rust 1.98.1（Harmonybrew；上游要求 `rust-version = 1.96`）
- Boost 1.92.0（仅头文件，供 vendored Vectorscan）
- clang/clang++ 15.0.4（OHOS SDK 26.0.0.18）
- crates.io 依赖按上游 `Cargo.lock` 锁定（`--locked`）
- Conan 制品依赖：0

## 验证结果

证据日志：`reports/conan-create-rerun.log`（完整 `build()` 阶段：cargo build + 上游测试）、
`reports/conan-create-rerun2.log`（以已产出的包复跑 `test_package`，`conan create` rc=0）、
`reports/upstream-test-run.log` / `upstream-test-run-round1.log`（首轮探测）、
`reports/upstream-test-report.md`（R51 三步法汇总）。

- 清点（R51 第 1 步）：上游 911 个 `#[test]`（`tests/` 44 文件 240 个 + src/各 crate 单元 671 个）
- 首轮全量实跑（R51 第 2 步，`cargo test --release --no-fail-fast` 不排除任何用例）：
  **785 passed / 2 failed / 2 ignored**
- 完整 `build()` 验证轮（`conan create` 干净构建 + `build()` 内上游测试）：
  **784 passed / 0 failed / 2 ignored**，包成功产出并入库
- `test_package` 验证轮（`conan create` rc=0，以已产出包执行消费者测试）：
  **PASS 4/4**；包引用 `kingfisher/1.109.0@ohpcd/stable#2c2f5d60…`，
  package_id `6b129b06…`（os=OHOS, arch=armv8, clang 15, libc++）
- 3 个外部环境依赖用例按 TEST_QUALITY_SPEC §3.3 以 `--skip` 排除，并在
  `test_package/MANIFEST.yml` 逐条声明豁免与具体技术原因；**未删除/未改写任何上游测试源码**：

| 用例 | 依赖 | 实测证据 |
|---|---|---|
| `int_github::test_github_remote_scan` | 外网 GitHub 克隆 | 单独复跑通过（1 passed, 12.95s）；全量并行时外网竞争致 findings=0 |
| `git_binary::tests::test_update_clone` | 外网 git 克隆 github.com:443 | TCP 被阻断：`curl 28`；已编译测试二进制单独复跑同样失败（96.21s）；`connect_ex(("github.com",443))` = EAGAIN。上游守卫只做 DNS 解析故未能自动跳过 |
| `library_crates_external_project::library_crates_work_from_external_project` | crates.io 离线索引 | `--offline` 解析报 `no matching package named 'gix' found`；同一工作区自身亦报 `aws-config` 缺失 |

- `test_package`（消费者视角，R34 实质调用）：**PASS 4/4**
  —— `--version` 报 1.109.0；合成凭据夹具实际检出 findings=1 且命中
  `AWS Secret Access Key`；干净输入 findings=0；规则引擎已加载 rules_applied=979
- 二进制冒烟：`kingfisher --version` → `kingfisher 1.109.0`（签名后 rc=0）

## 注意事项

- 二进制在 OHOS 上**必须签名**才能执行；`package()` 已内置签名步骤。
- `rustc` 的 `target_os` 在本目标上是 `linux`（`target_env=ohos`），因此上游
  `any(feature = "use-mimalloc", target_os = "linux", ...)` 条件恒真——**仅靠
  `--no-default-features` 无法关闭 mimalloc**，必须改造 `override` feature
  （这也是补丁生效点）。

## 反直觉坑：不要在配方里 `tool_requires("rust-toolchain/…")`

**实测结论（2026-10-01，不要重复尝试）**：为"不假设 CI 预置 Rust"而加入

```python
def build_requirements(self):
    self.tool_requires("rust-toolchain/1.97.1")   # ← 会直接构建失败
```

会让构建**在 `build()` 第一步就失败**：

```
/system/bin/sh: /storage/Users/currentUser/.conan2/p/rust-1b22ad19431ff/p/bin/cargo: Permission denied
ConanException: Error 126 while executing
```

根因：Conan 会把 tool_requires 依赖的 `bin/` 前插到 `PATH`，而该包存于 HMDFS
（`~/.conan2/p/rust-*/p/bin/`），**HMDFS 会丢可执行位**（E046 同类），于是
`cargo` 不可执行。要让这条路径可用，必须先按 `archives/l/libimagequant/4.4.1`
的做法用 `binary-sign-tool` 把 `cargo`/`rustc`/`librustc_driver*.so` 签名到私有副本，
再把 PATH 指向该副本——即"声明依赖"不能解决，还需配套的签名运行时。

因此本配方保持 Harmonybrew 方案（`_ensure_rust_toolchain`），并已验证：
worker 上只要 `brew install rust` 即可，本仓库已有多个 cargo 配方
（`hf-mount`、`crunch64`、`gigski` 等）经此路径 published。

## 外部网络依赖用例（无法在受限出网环境通过）

见 `test_package/MANIFEST.yml` 的 `upstream_test_exemptions`：三个用例分别依赖
外网 GitHub 并发克隆、`github.com:443` 直连克隆、以及 `cargo generate-lockfile --offline`
的完整 crates.io 离线索引。其中 `git_binary::tests::test_update_clone` 的上游守卫
`github_is_reachable()` 只做 DNS 解析，TCP 被阻断时不会跳过，故必须显式 `--skip`。
## CI 三次失败的原因各不相同（勿被 CI 顶部"网络问题"误报误导）

CI 机器人在失败评论顶部给出的「类别: 网络问题 / 源码下载超时」是**关键词误报**，三次
的真实原因各不相同，需以 `### 失败步骤完整日志` 为准：

| 轮次 | 构建 | 真实原因 | 排除误报的证据 |
|---|---|---|---|
| ① | #67997 | **构建超时**（默认 3600s 预算被 SIGKILL） | `cargo build` 已成功；`elapsedTime≈3563s`≈上限 |
| ② | #68984 | **worker SSH 不可达**（基础设施抖动） | `worker-prep`/`git-clone`/`cleanup` 三步 0.003s 退出、`SSH bridge exec failed: Connection refused`，与配方无关 |
| ③ | #74999 | **rustc 临时目录创建失败**（TMPDIR 指向共享 `$HOME/.cache/tmp`，被并发任务清理） | `Sources correctly downloaded …`（下载成功）、`Finished \`release\` profile … 21m 31s`（release 已编译完）、`elapsedTime=2827.8s` 远未触及 10800s；错误为 `couldn't create a temp dir: No such file or directory (os error 2)` at `.../target/release/deps/rustc2wTSif` → `could not compile \`kingfisher\` (test "int_jwt_provider")` |

**修复（③）**：按 **R49 精神**（依赖/临时资源只用 build_folder 私有路径，不注入共享路径），
`build()` 中把 `TMPDIR` 从共享 `$HOME/.cache/tmp` 切换为 **`build_folder/tmp` 私有路径**，
并防御性预建 `CARGO_TARGET_DIR/release/deps`；`cargo build` 与 `cargo test` 两条命令共用同一
`env_prefix`，确保两轮编译都使用私有 tmp：

```python
private_tmp = os.path.join(self.build_folder, "tmp")
os.makedirs(private_tmp, exist_ok=True)
os.makedirs(os.path.join(target_dir, "release", "deps"), exist_ok=True)
env_prefix = (f'CARGO_TARGET_DIR="{target_dir}" '
              f'CARGO_NET_GIT_FETCH_WITH_CLI=true '
              f'TMPDIR="{private_tmp}" ')
```

**另注**：`conandata.yml` 里的 `gh-proxy.com` 前缀**不需要修**——那是 CI 的 mirror fallback
自动注入的（日志 `[step] Mirror fallback: rewriting source URLs`），构建结束由
`[step] Pre-download: conandata.yml 已还原为官方 URL` 自动还原；仓库内的 `conandata.yml`
始终保持官方单源即可。

### 第 ④ 次失败（#81716）：TMPDIR 修复已生效，但 worker 在编译测试二进制时整体死亡

`#81716`（CI-007）验证了第 ③ 次修复**确实生效**：

| 检查项 | 结果 |
|---|---|
| cargo 命令中的 TMPDIR | `TMPDIR="/…/p/b/kingf…/b/build-release/tmp"` —— 已是 **build_folder 私有路径** |
| 旧共享路径 `.cache/tmp` | 命中 **0** |
| `couldn't create a temp dir` 错误 | **0**（第 ③ 次的报错已消失） |

但构建仍在 **2838s** 被终止，形态与以往不同：

```
o   Compiling kingfisher v1.109.0 (/…/b)
hprogram finished with exit code -1     ← conan-build-test，无任何 error 输出
helapsedTime=2838.479300
--- cleanup ---
eSSH bridge exec failed: connection lost before ready: Connection refused (111)
hprogram finished with exit code -1     ← cleanup 仅 0.012s 就失败
```

判读：`exit -1` 且**编译期零 error**、紧接着 `cleanup` 也连不上 worker（0.012s），
说明**整个 worker 在构建中途消失**（最可能是并发编译 44 个测试二进制时峰值内存
把容器 OOM 掉，容器一死，SSH bridge 与 cleanup 同时失联）。

**对策（本版）**：仅对**测试阶段**限制并行度，压住峰值内存；release 构建阶段
（已稳定成功）保持默认并行以不牺牲速度：

```python
test_env = env_prefix + "CARGO_BUILD_JOBS=2 "
self.run(f"{test_env}{cargo} test --release --no-fail-fast -- …")
```

（若属 worker 侧基础设施问题，此改动无害；若确为峰值内存所致，则直接消除该失败。）

### 第 ⑤ 次失败（#82118）：修复全部生效，仅剩 1 个联网用例未豁免

`#82118`（CI-015）是**首次真正跑完测试**的一轮，可视为前面全部修复的验收证据：

| 指标 | 值 | 判读 |
|---|---|---|
| `elapsedTime` | **8514s** | 未被超时杀 → **10800s 预算生效**（旧 3600s 下早就 SIGKILL） |
| 测试是否执行 | **19 条 `test result` 行、49 passed / 0 failed / 2 ignored** | 测试套件**真正运行**（此前几轮连测试都没跑到） |
| TMPDIR | 私有 `build_folder/tmp` | 第 ③ 次修复生效，`couldn't create a temp dir` 不再出现 |
| 并发编译被杀 | 未再现 | 第 ④ 次 `CARGO_BUILD_JOBS=2` 生效（本轮跑满 8514s 未被杀） |
| 失败点 | 仅 `` `--test int_s3` `` → `error: 1 target failed` | 唯一残留问题 |

**唯一残留**：`int_s3::test_visit_public_bucket` 调用
`visit_bucket_objects("awsglue-datasets", …)`，**联网访问公有 AWS S3 端点**并断言对象内容，
需出网到 AWS —— 与此前已豁免的 3 个外部网络用例同类。测试源码未删改，
仅按 TEST_QUALITY_SPEC §3.3 追加 `--skip test_visit_public_bucket` 并在
`test_package/MANIFEST.yml` 声明豁免。

> 注：CI 机器人提示的「源码服务器返回 429 / 源码下载失败」仍是**关键词误报**——本轮
> 实际失败在测试执行阶段（`test result` 都已产出），与源码下载无关。

---

**编译结束**: 2026-10-01 21:58
**最终状态**: built
