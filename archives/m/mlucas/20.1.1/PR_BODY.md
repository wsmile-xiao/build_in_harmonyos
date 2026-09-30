## PR 信息

- 三方库名称：mlucas
- 上游版本：20.1.1（上游仓库 v20.1.1 对应提交 `039e912fa7a246788c7a2c6b1a1f4c13485bbf23`，2022-07-12）
- 上游仓库地址：https://github.com/primesearch/Mlucas
- 适配路径：路径 A（基础适配） + 知识库扩展（draft 知识解决一类问题）
- 使用知识库：openharmony-compile-agent（SKILL v12.22）；参考既有条目/草稿 `E086`、`DRAFT-chipmunk2d-7.0.3-sysctl-apple-guard`、`DRAFT-msquic-2.6.1-pthread-setaffinity-np-android-guard`；本 PR 新增草稿 1 条（`knowledge/drafts/DRAFT-mlucas-20.1.1-glibc-feature-test-undefined-macro-trap.{kv,md}`）
- 适配路径（配方）：`archives/m/mlucas/20.1.1/`

## 测试用例对比

> 计数口径在三处文档中统一（`reports/test-report.md`、`notes.md`、`test_package/MANIFEST.yml` 的
> `case_counts` 块），避免出现"同一个数、两种粒度"的歧义。

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 GitHub 源码树无 `tests/` 目录，亦无 ctest/pytest/meson 注册 |
| 集成测试 | 3 | 来源：官方发布 tarball 的 autotools 包装 `Makefile.am:22` `TESTS = tests/spot-check tests/fermat-test tests/self-test`（即 3 个 check-target） |
| 其他测试 | 0 | 程序内置自检（`-s` 各档）属运行时功能，不单独计为用例 |
| **合计** | **3** | 上游 check-target 总数（展开为 4 条 mlucas 命令行） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试入口 |
| 集成测试 | 3（展开 4 条命令，全部执行） | **不变，0 修改** | `spot-check`、`fermat-test`（2 条命令）、`self-test` 全部实际执行，exit 0 |
| 其他测试（补充档） | 1 | 新增 | `mlucas -s t` 内置自检 tiny 档（上游自带能力，不在 `TESTS` 清单） |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/conanfile.py`：断言安装后 `bin/mlucas` 为 64-bit LE AArch64 ELF（`e_machine=183`）且 ELF 解释器为 OHOS musl 加载器 `/lib/ld-musl-aarch64.so.1`（5 条断言） |
| **合计** | **上游命令 5 + 鸿蒙 1** | **+1（鸿蒙）** | 上游 check-target 覆盖率 **3/3（100%）**，漏测 0 |

**上游命令逐条结果（全部 exit 0）**

| # | 命令 | 结果 |
|---|---|---|
| 1 | `mlucas -fftlen 192 -iters 100 -radset 0` | `Res64: 71E61322CCFB396C`，`Done ...` |
| 2 | `mlucas -fftlen 1024 -f 24 -iters 100` | `INFO: 12 of 12 radix-sets at FFT length 1024 K passed` |
| 3 | `mlucas -fftlen 1024 -radset 4 -f 24 -iters 1000` | 通过 |
| 4 | `mlucas -s m -cpu 0:3` | 16/16 FFT 长度（2M–7.5M）全部写入 cfg 条目，无 `Halting` |
| 5 | `mlucas -s t` | 32 个 FFT 长度中 15 个写入 cfg，17 个按上游规则跳过 |

> 未执行且**不在** `TESTS` 清单内的档位：`-s l` / `-s all` / `-s xl` / `-s xxl`（各需 10 小时~数天），
> 因此不构成漏测。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 本 PR 仅对上游**源码**打 2 个平台可移植性补丁，未触碰任何测试文件；
> 上游 check-target 以原样命令执行。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游 check-target 已覆盖核心功能，本 PR 未补全"上游缺失的测试"。
> `test_package/` 内的测试属**消费者侧冒烟 + 鸿蒙产物校验**，按 R51 规则**不替代**上游测试统计，
> 仅额外新增 1 个鸿蒙特有用例（见上表）。

## 验证结果

- 编译状态：**通过**（`conan create` exit 0；`conan-verify` G0–G4 + L2/L4/L5 全 PASS；W3 本地 CI 模拟 `JC/KC/L0/L1/L2/L4/L5` 全 pass，Pass rate 100% (1/1)）
- 上游测试用例通过率：**5/5（100%）**，退出码全部为 0，漏测 0
- 新增测试用例通过率：**1/1（100%）**（鸿蒙产物断言 5 条 + 上游 spot-check 复现 3 条断言，`conan create` 内执行）

**关键门禁证据**

| 项 | 结果 |
|---|---|
| 源码 | `https://github.com/primesearch/Mlucas/archive/039e912…tar.gz`，sha256 `fd15734f…6580`（多次独立下载一致，第 4 次实测 MATCH） |
| 依赖 | `gmp/6.3.0`（唯一强制第三方库，静态链接；产物 `readelf -d` 仅 `NEEDED libc.so`） |
| 补丁 | 2 个，均 `patch_type: portability`，对全新官方 tarball `patch -p1 --dry-run` exit 0，新增行**无** `__OHOS__` 等平台宏 |
| W2 原子性 | `JC6 涉及软件数: 1（合规）`；`junk_check` PR-diff 模式 `Junk Files: 0` |
| 产物 | `bin/mlucas`（aarch64 / OHOS musl ELF，解释器 `/lib/ld-musl-aarch64.so.1`）+ 软件级 `commands.json`（R38） |

## 补充说明

### 1. 适配内容（2 个平台可移植性补丁，均不含平台宏）

| 补丁 | 文件 | 根因 → 修复 |
|---|---|---|
| `0001-src-platform.h.patch` | `src/platform.h` | 上游 `#if … ((__GLIBC__ < 2) \|\| (__GLIBC_MINOR__ < 30))` 在 musl 上因 `__GLIBC__` 未定义而按 **0** 参与运算 → 条件恒真 → 引入 glibc/BSD 专有的 `<sys/sysctl.h>`（OHOS sysroot 无此头，20 个 TU 编译失败）→ 改为 `#if __has_include(<sys/sysctl.h>)` 能力探测 |
| `0002-src-threadpool.c.patch` | `src/threadpool.c` | 线程亲和性分支 `#elif defined(OS_TYPE_LINUX)` 使用 glibc 扩展 `cpu_set_t`/`CPU_ZERO`/`CPU_SET`/`sched_setaffinity`（musl 不提供）→ 收紧为 `OS_TYPE_LINUX && defined(__GLIBC__)`，并新增非 glibc 分支（沿用上游对 OpenBSD 的既有写法：亲和性交给 OS） |

两处修改对 glibc / BSD / macOS 行为**完全不变**，且**不使用任何平台宏**（`__OHOS__` 守卫是 PF5 会
拦截的写法；能力探测跨平台正确）。

构型：显式 `nosimd`（scalar double）。上游 `makemake.sh` 无参时按 `/proc/cpuinfo` 自动选 SIMD 并附
`-march=native`，在 CI/异构环境不可复现；该选择与 Debian 在 arm64 上的 `generic-c` 一致。

### 2. 框架门禁偏差说明（PF9 —— 必须登记，建 PR 时使用 `--no-preflight`）

本 PR 触发 `scripts/ohc/preflight.py` 的 **PF9 分支/路径闸**：

```
PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
  —— archives/m/mlucas/README.md, archives/m/mlucas/commands.json, archives/m/mlucas/manifest.yaml
```

判定为 **误拦**，依据：

1. 这 3 个文件是 `knowledge/ARCHIVE-SPEC.md` §2.1 **必需**的软件级元数据（`manifest.yaml`、`README.md`）；
   `commands.json` 另由 **R38** 强制（产物含 `bin/` 的可执行包必须有）。
2. `preflight.py` 内部自相矛盾：同一模块 **PF8** 正是从该软件级路径读取它
   （`cj = pkg_dir / "commands.json"`，`pkg_dir = repo_root/archives/m/mlucas`）——PF8 要求存在、PF9 禁止出现。
3. 仓库 `HEAD` 已有 **3309** 个软件级 `commands.json`、**5443** 个软件级 `README.md`、**13269** 个软件级 `manifest.yaml`。
4. CI 侧 `build_and_test.sh` 的 L0 路径检查对**同一文件集**判定 `L0_RESULT=pass`。

其余硬闸（PF1/PF2/PF3/PF3b/PF4/PF5/PF6/PF7/PF8 及 R52）**全部 PASS**，无其他豁免。
建 PR 命令：`python3 scripts/ohc-run.py submit mlucas 20.1.1 --no-preflight`。

### 3. 已知限制

- **scalar 构型的圆整误差裕度**：自检在接近各 FFT 长度推荐上限（`p/pmax_rec ≈ 0.995`）的指数上会因
  MaxErr 触顶而跳过部分 radix-set；小 FFT 长度另有上游设计限制
  （`CY routines with radix < 16 do not support shifted residues`）。均为上游对 scalar/非 SIMD 构型的
  固有行为（上游自身提示 "PLEASE CHECK YOUR BUILD OPTIONS"），非本次适配缺陷；`-s m` 仍为 16/16 长度通过。
- **`primenet.py` 未打包**：上游 GIMPS 结果提交助手需 Python3 运行时，为保持包自包含（`bin/` 仅 `mlucas`）未纳入。

### 4. 过程中发现的框架问题（供维护者参考，不在本 PR 内修复）

1. PF9 与 ARCHIVE-SPEC/PF8 的冲突（见上）。
2. `conan-verify` 的 E017 镜像注入未完整还原：G2 会改写 `conandata.yml` 注入 `gh-proxy.com`，
   并残留 `conandata.yml.orig` / `conandata.yml.ghfast-bak` / `patches/.patch-backup-*`；
   本 PR 提交前已手工恢复为官方单条 URL 并清理备份。
3. `finish` step8 `gen_summary` 崩溃（`'str' object has no attribute 'append'`）；
   step10 仍校验 ARCHIVE-SPEC §2.3 已废弃的 `packaging/` 与 `.staging-verified`。
