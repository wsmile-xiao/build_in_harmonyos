# DRAFT-rust-preohos-musl-cfg-gate-ohos-misfire — Rust pre-ohos 依赖 cfg 门在 target_env="ohos" 上误启用 glibc-only 符号

> Contributor: Curator (zram-1.2.1 run) / Status: **DRAFT** / Updated: 2026-09-30 / Severity: 3 (blocking)
> Prospect ID: `DRAFT-rust-preohos-musl-cfg-gate-ohos-misfire`（正式编号由主编 `graph promote` 分配）
> 一句规则：**nix ≤0.26 一类 pre-ohos crate 的 `all(target_os = "linux", not(target_env = "musl"))` 门把 `target_env="ohos"` 误判为"非 musl"而启用 glibc-only 符号；当上游声明范围内无兼容版本时，唯一不污染上游判定的修法是按 `cfg(not(target_env = "ohos"))` 门控该依赖（dev-dependencies 同样必要——cargo 为 `--bins` 测试目标也构建 dev-deps 图）。**

## 查重证据（实际检查范围、检索词、命令、命中与逐项差异）

检查范围：设备 run worktree 内 `knowledge/graph/`（546 个 kv）、`knowledge/doc/`（542 个 md）、`knowledge/drafts/`、`knowledge/operations/`、`knowledge/principles.yaml`。实际执行的检索（2026-09-30，真机 grep）：

| 检索词 | 命中 | 差异结论 |
|---|---|---|
| `grep -rEiln 'O_FSYNC\|target_env\|CLONE_NEWUSER\|SIGSYS\|etxtbsy\|text file busy'` | graph E051/E220/E246（SIGSYS 族）、graph E358（target_env）、drafts 多个 sigsys 条目 | 无 O_FSYNC/ETXTBSY 命中；E358 是唯一 target_env 条目，见下逐项差异 |
| `grep -rElwn 'nix'`（词边界） | E358.kv、graph/index.tsv、doc/E358.md、drafts/zpaq-7.15（后经核查为"*nix 工具"无关词形） | 仅 E358 语义相关 |
| `grep -rli 'O_FSYNC'`（drafts/doc） | 0 | 本条符号特征无覆盖 |
| `grep -rln 'E0425'` | drafts/wagyu-0.6.1（kv+md） | wagyu 是 E358 同族锁文件问题，见下 |
| `grep -rln 'dev-dep\|dev-dependenc\|cfg(not'` | 0 | dev-deps 门控解法无覆盖 |

与最相近条目的逐项差异：

- **E358**《旧 Rust Unix 依赖锁图在 OHOS target_env 下的确定性迁移》：根因是**旧 Cargo.lock 固定**的 libc/nix/ctrlc 与现代 rustc 不兼容，解法是 semver 范围内**锁图迁移**（`cargo update -p ... --precise`），触发面前提是存在锁定图。本条：上游**根本没有 Cargo.lock**，失败发生在依赖 crate **自身源码的 cfg 门**（非 ABI/锁图组合），且在依赖**自身声明范围内无任何可用版本**（本 run 对 libc 0.2.139…0.2.189 逐版本核实 + nix <0.24 全 range 核实）——E358 的推荐方案在本问题上**不可执行**，两互为 `similar_to` 而非覆盖。
- **wagyu-0.6.1 草稿**（E358 同族）：2019 年锁文件的组合修复（libc/cc bump + registry 补丁 + 签名），同属"锁文件时代"问题类。
- **DRAFT-ohos-musl-glibc-specific-symbols**：musl 缺 glibc 符号的**统一处置**，但场景是**项目自己的源码**直用 glibc 符号（`program_invocation_short_name` 等），修法是源码处守卫。本条：项目源码**不引用**这些符号，是**依赖 crate 的平台 cfg 误判**把符号段带进来，修法在**依赖解析的 target 适用范围**，动不了（也不应动）项目源码。libc 符号缺失层相同，根因层与修复层不同。
- **E086/E102**（socket 结构/头文件层）、**E051**（运行期 SIGSYS 层）：层次不同，作 `similar_to` 家族参照。

**新增价值**：把"`not(target_env = "musl")` 布尔门在新 target_env 上的漏判"确立为一类可检索的编译错误模式，给出"范围无解 ⇒ cfg 门控依赖"的通用解法与 cargo dev-deps 图语义前置事实。

## 症状（真实日志，zram-1.2.1 run 真机预检）

```console
   Compiling nix v0.23.2
error[E0425]: cannot find value `O_FSYNC` in crate `libc`
   --> /storage/Users/currentUser/.cargo/registry/src/rsproxy.cn-e3de039b2554c837/nix-0.23.2/src/fcntl.rs:102:9
    |
102 |         O_FSYNC;
    |         ^^^^^^^
```

- 保留日志：`~/zram-work/logs/preflight2.log`（29 行 `error[E]`，E0425 为主）、`~/zram-work/logs/unittest.log`（同型 3 处）；Builder 计全量 51 个错误（含 E0004/E0308 等）。
- 触发特征三元组：`error[E0425]` + `aarch64-unknown-linux-ohos` + 报错位置在 `nix-*/src/`。

## 根因机理链（工具实现证据 → 触发命令 → 失败点 → 归类）

1. **工具实现证据**：nix 0.23.2 `src/fcntl.rs:88-93` 用 `all(target_os = "linux", not(target_env = "musl"))` 门控 O_FSYNC 等 glibc-only 常量；`src/lib.rs` 的 mqueue/aio 模块同型门控。该门写于 OHOS target 进入 Rust upstream 之前。
2. **触发命令**：`cargo test --release --lib --bins --target aarch64-unknown-linux-ohos`（上游 `make check` 的 OHOS 等价物；集成测试目标 `tests/test_cases.rs` 的 dev-dependency 即 nix）。
3. **失败点**：cfg 门在 `target_env="ohos"` 上求值为真 → nix 编译自身时引用 `libc::O_FSYNC`/`mq_*`/`aio_*`；libc 对该 target 路由 musl 模块 → `error[E0425]` 级联（51 个错误）。cargo 对 `--bins` 测试目标同样构建 dev-deps 图，故该失败先于任何用例执行。
4. **归类**：编译期平台探测语义错误（cfg 布尔门漏判新 target_env），阻塞面 = 构建失败（真机 51 错、CI 前预检拦截）。

版本面（本 run 实证）：`nix >=0.22,<0.24` 内无 ohos 感知版本；0.26.4 仍带同门；ohos 修复在 nix >=0.27，但 0.27 移除了上游集成测试辅助代码依赖的 mount API——升版本方案在上游声明范围内外**双重不可行**。

## 方案空间

**rec（主方案）：按 `cfg(not(target_env = "ohos"))` 门控该依赖**

```patch
--- a/Cargo.toml
+++ b/Cargo.toml
@@ -23,7 +23,6 @@
 [dev-dependencies]
 tempfile = "3"
 fs_extra = "1.3"
-nix = ">=0.22, <0.24"
 ctor = "0.2"
+
+[target.'cfg(not(target_env = "ohos"))'.dev-dependencies]
+nix = ">=0.22, <0.24"
```

（与 `archives/z/zram/1.2.1/patches/0001-gate-nix-devdep-for-ohos.patch` 同构；真机应用后 `cargo test --lib --bins` 41/41 通过、权威 CI run1 PASS。）主依赖形态用 `[target.'cfg(not(target_env = "ohos"))'.dependencies]`。适用前提：该依赖仅服务非 ohos 平台的测试/可选路径——**申报时须先核实这一点**，不得为绕编译盲目门控运行期必需依赖。

**fallback（退路，诚实权衡）**：依赖在 ohos 运行期确属必需时——(a) 试上游范围外 ohos 感知版本（nix >=0.27；其 mount API 已移除，与本问题之外的用例兼容性**未核实**，仅候选）；(b) 对依赖 crate 自身 cfg 门打补丁（`not(target_env = "musl")` → `not(any(target_env = "musl", target_env = "ohos"))`）。两者都越出"仅调整依赖解析范围"的边界、偏离上游语义，仅作退路并逐项留证。

**forbid（反模式）**：
1. **固定 libc 版本追符号**——任何 libc 固定都无法满足（musl 模块 0.2.139…0.2.189 均无目标符号，逐版本核实），无效调试 + 锁图漂移。
2. **直接改 `~/.cargo/registry/src` 里的依赖源码**——污染共享真机缓存，其他任务不可复现（同 E358 红线）。
3. **整体砍掉测试目标绕编译**——污染上游测试判定（态度审计第 2 条）；正确口径是门控依赖后按平台限制逐项披露 NOT_RUN。

## 验证（自包含探针，任何人开新 shell 可跑）

在 OHOS 设备（harmonybrew cargo 已装）上：

```sh
P=$HOME/nixgate-probe; rm -rf "$P"; mkdir -p "$P/src" "$P/.cargo"
printf '[package]\nname="nixgate-probe"\nversion="0.1.0"\nedition="2021"\n\n[dev-dependencies]\nnix = "=0.23.2"\n' > "$P/Cargo.toml"
printf '#[cfg(test)]\nmod t {\n    #[test]\n    fn uses_nix() { let _ = nix::unistd::getpid(); }\n}\n' > "$P/src/lib.rs"
printf '[target.aarch64-unknown-linux-ohos]\nlinker = "/data/service/hnp/bin/clang"\n\n[source.crates-io]\nreplace-with = "rsproxy-sparse"\n\n[source.rsproxy-sparse]\nregistry = "sparse+https://rsproxy.cn/index/"\n\n[net]\nretry = 10\n\n[http]\ntimeout = 600\nlow-speed-limit = 1\n' > "$P/.cargo/config.toml"
cd "$P" && RUSTFLAGS="-C linker=/data/service/hnp/bin/clang" ~/.harmonybrew/bin/cargo test --target aarch64-unknown-linux-ohos --lib 2>&1 | grep -m3 "E0425\|O_FSYNC"
# 期望：error[E0425]: cannot find value `O_FSYNC` in crate `libc`（指向 nix-0.23.2/src/fcntl.rs:102）
# 静态佐证（复现后）：
grep -n 'not(target_env = "musl")' /storage/Users/currentUser/.cargo/registry/src/*/nix-0.23.2/src/fcntl.rs
```

注意探针目录名不含 "tmp"（设备工作目录命名纪律）。补上门控后同探针应编译通过，即完成"复现 → 修复 → 消失"闭环。

## 证据路径（zram-1.2.1 run）

- 失败日志：设备 `~/zram-work/logs/preflight2.log`（29 行 error[E]、O_FSYNC 于 :220-224）、`~/zram-work/logs/unittest.log`
- 修复补丁：`archives/z/zram/1.2.1/patches/0001-gate-nix-devdep-for-ohos.patch`（候选 ab369ce080）
- 机理与版本面核实记录：`archives/z/zram/1.2.1/notes.md`、`archives/z/zram/1.2.1/test_package/MANIFEST.yml`
- 修复后门禁：`runs/zram-1.2.1/logs_ci_run1.log`（run1 PASS，41/41 单元测试）

## 原则挂钩与申报域

- principles：**P-PATCH-002**（平台隔离守卫是标准写法——`cfg(not(target_env = "ohos"))` 是该原则在 Rust/cargo 语境的对应物；`not(target_env = "musl")` 正是"用否定邻集排除新平台"的反模式形状）。
- 申报域（八分类）：**编译错误**（主）+ **平台探测**（辅）。形态选择：机理叙事 + 方案空间完整，走 kv 条目形态（非 pre-scan 规则形态）。
- 配额使用：本条为 zram-1.2.1 run **主条**；另一次条 `DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry`；共 2/2，其余观察（rsproxy 复用、unshare SIGSYS 佐证、tmp 目录清理）降级经验仓。
