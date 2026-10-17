# DRAFT-ohos-configure-sanity-check-mtime：
# 预生成 autotools 产物的 mtime 策略——未来时间戳触发 configure sanity check

> Contributor: siril-1.2.3 适配 | Status: Draft | Updated: 2026-09-06
> Source: archives/s/siril/1.2.3（PR #8366，构建 #40743 / #41049 实测）

## 现象

siril/1.2.3 配方携带预生成 autotools 产物（`autotools/` 下 configure、
aclocal.m4、config.h.in、全部 Makefile.in、aux 脚本），因为 CI 沙箱
**不能 EXECUTE host automake/aclocal**（"Can't exec aclocal: No such
file or directory"），autoreconf 不可行。patch 修改了 configure.ac /
Makefile.am 后，出现两轮完全不同的 CI 失败：

1. **#40743 — automake 重生成触发**：

```text
.../b/missing automake-1.17 --foreign
.../b/missing: line 85: automake-1.17: command not found
make: *** [Makefile:449: .../b/Makefile.in] Error 1
```

   `os.utime(dst_file)`（当前时间）在 CI worker **0.01s 时间戳精度**下与
   patch 应用落在同一 tick，无法保证 Makefile.in 严格新于 patch 后的
   configure.ac → `Makefile.in: Makefile.am $(am__configure_deps)` 维护
   规则触发 → 调用缺失的 automake-1.17。

2. **#41049 — configure sanity check 硬报错**（改用未来时间戳 `now+3600` 后）：

```text
checking filesystem timestamp resolution... 0.01
checking whether build environment is sane... no
configure: error: newly created file is older than distributed files!
Check your system clock
```

   未来时间戳压制了 automake 规则，却触发了 configure 的 AM_SANITY_CHECK。

关键对比：本地（高精度 FS）两种时间戳策略都能过，只有 CI 0.01s 精度
暴露差异——**mtime 策略必须与 FS 时间戳精度解耦**。

## 根因分析

- **automake 维护规则**：`$(srcdir)/Makefile.in: $(srcdir)/Makefile.am
  $(am__configure_deps)`，其中 `am__configure_deps = $(am__aclocal_m4_deps)
  $(CONFIGURE_DEPENDENCIES) $(ACLOCAL_M4)`。规则**一触发即无条件执行
  `$(AUTOMAKE) --foreign`**（本地生成规则 + 最小实验验证：Makefile.am
  旧 + Makefile.in touch 最新 → 不执行 automake）。
- **当前时间 touch 的缺陷**：CI FS 时间戳精度 0.01s，`os.utime(当前时间)`
  与 patch 应用可能在**同一 tick** → 生成文件不严格新于源文件 → 规则
  触发。E248 的"对齐 mtime"方案（`os.utime(makefile_in,
  ns=(os.stat(makefile_am).st_mtime_ns,)*2)`）在 0.01s 精度下同样可能
  同 tick 失效。
- **未来时间戳的缺陷**：`now + 3600` 让所有生成文件严格新于源文件
  （automake/autoconf 规则不触发），但 configure 的 AM_SANITY_CHECK
  会运行 `ls -Lt "$srcdir/configure" conftest.file`（`conftest.file`
  是 configure 运行期间新建的）：**configure 一旦在未来，永远比新建
  文件新** → `test "$2" = conftest.file` 两次重试均失败 → 硬报错
  "newly created file is older than distributed files!"。
- 结论：单边策略（当前时间 / 未来时间戳）都有无法绕过的失败面，必须
  **双向拉开**。

## 解决方案

**双向 mtime 策略**（与 FS 时间戳精度彻底无关）：

1. **生成文件**（configure、aclocal.m4、config.h.in、全部 Makefile.in、
   aux 脚本）→ `os.utime(dst_file, (now, now))`，`now = time.time()`
   **只算一次、所有文件同一个值** → 相互严格相等，make 的 `>` 严格比较
   永不触发维护规则；
2. **patch 影响的源文件**（configure.ac、被 patch 的 Makefile.am、
   source() 生成的 po/Makefile.am）→ `os.utime(src_file, (past, past))`，
   `past = now - 86400`（一天前）→ 绝对旧于生成文件；
3. **任何文件都不在未来** → configure 的 AM_SANITY_CHECK 通过。

```python
# conanfile.py build() 中 apply_conandata_patches(self) 之后：
now = time.time()
past = now - 86400
# ...复制 autotools/ 生成文件后统一设置：
os.utime(dst_file, (now, now))          # 每个生成文件
os.utime(src_file, (past, past))        # 每个 patch 影响的源文件
```

合规与维护边界：patch 改 `Makefile.am`/`configure.ac` 时必须同步手改
对应 `autotools/*/Makefile.in` 与 `configure`（内容漂移不会因 mtime
抑制被掩盖，如漏 `-lintl` 会静默缺库）。

## 验证证据

- 本地完整 `conan create`（`-pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64`）：
  - `checking whether build environment is sane... yes` ✅
  - make 阶段**零** automake/autoconv 调用，直接进入编译 ✅
  - test_package 通过：`siril-cli --version` → `siril 1.2.3` ✅
- 本地最小实验（make 4.4）：Makefile.am 旧 + Makefile.in touch 最新 →
  不执行 automake，证实规则触发条件是"依赖严格新于目标"。
- CI 复验：PR #8366 重新触发后应在 configure 阶段直接通过（待用户
  `/rebuild` 触发确认）。

## 查重（B1 去重证据摘要）

- 检索词（`knowledge/` 全目录 grep：index.tsv + graph/*.kv +
  drafts/*.kv，1341 文件）：`newly created file is older` /
  `build environment is sane` / `AM_SANITY_CHECK` /
  `am_cv_filesystem_timestamp` / `sanity_check` → **0 命中**；
  `am__configure_deps` / `Makefile.in: Makefile.am` / `maintainer` /
  `regenerate` → 命中 E248 / E069 / E175 / E178（见差异化定位表）。
- 结论：**同族可申报**——"configure AM_SANITY_CHECK 与生成文件 mtime
  策略的冲突（未来时间戳必炸）+ 0.01s 精度 FS 下不依赖精度的双向
  mtime 策略"为新增问题层，需下表定位差异。

## 相关既有条目差异化定位表

| 条目 | 问题层（根因/机制） | 与本草稿差异 |
|---|---|---|
| E248 | patch 应用后 Makefile.in mtime 早于 Makefile.am → `Makefile.in: Makefile.am $(am__configure_deps)` 触发 automake 重生成（设备无 automake → Error 127）；修复 = 对齐两者 mtime（`os.utime(ns=...)`） | 只覆盖"**生成文件旧于源文件**"单边；其对齐方案在 **0.01s 精度 FS 上同 tick 失效**（#40743 实证）；不含"未来时间戳 → sanity check"另一面 |
| E069 | automake 自身编译的循环依赖 / `@am_AUTOM4TE@` 未解析（gen-all.pl timestamp 检查） | 面向 automake 源码构建，非"预生成产物 + 缺 automake 设备"的维护规则 mtime 策略 |
| E175 | HMDFS `config.status` confXXXXXX mktemp 段 Permission denied | 不涉及 AM_SANITY_CHECK 的 `ls -Lt` mtime 比较；无未来时间戳/sanity check 维度 |
| E178 | autoreconf 在缺工具链（automake/coreutils）的 worker 上失败 | 面向 autoreconf 路径；本条是"跳过 autoreconf、用预生成产物"路径的 mtime 治理 |

- 新增价值：确立"**预生成 autotools 产物 + 无 automake 设备 + 0.01s
  精度 FS**"场景下 mtime 治理的完整两难（当前时间 → 触发 automake；
  未来时间戳 → 触发 configure sanity check）与唯一鲁棒解法（生成文件
  统一同一 now + 源文件 pin 到过去），补齐 E248 的低精度 FS 盲区，
  构成 autotools mtime 故障图谱的独立节点。

## 禁止做法

- **不要用未来时间戳**（`now + 3600`、`os.utime(f, (t, t))` 其中
  t 在未来）——configure 的 AM_SANITY_CHECK 必然失败（#41049 实证：
  "newly created file is older than distributed files!"）。
- 不要只对齐 Makefile.in/Makefile.am（E248 方案）就认为低精度 FS 可
  行——0.01s 精度下同 tick 失效（#40743 实证），须叠加"源文件 pin 过去"。
- 不要为单个库安装 automake 或跑 autoreconf（E248 forbid 1/2 同款：
  依赖面扩散 + 破坏预生成产物一致性）。
