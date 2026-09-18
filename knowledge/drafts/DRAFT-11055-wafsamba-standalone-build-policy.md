# DRAFT-11055：Samba wafsamba 系独立库在 OHOS 的构建范式——waf 调用链、强制运行探针的处置与 python 绑定决策

- **触发实例**：tdb 1.4.15 适配（2026-09-16，任务 11055，分支 feat/tdb-1.4.15，wafsamba + 内置 waf 2.1.6 + python 3.14.7）
- **错误签名**：`The configuration failed` / `Could not build a python embedded interpreter` / `ld.lld: error: unable to find library -lintl` / `mandatory failure for this one`
- **类别**：build-system（Samba waf 生态）
- **严重度**：3（configure 确定性中断，且探针不可通过）

## 症状（可复现）

tdb 1.4.15 在 OHOS aarch64 上按常规姿势（python3 驱动 waf）配置时：

```text
Checking for HAVE_SECURE_MKSTEMP                       : not found
from .../lib/replace: The configuration failed False     # mandatory=True 直接中断
```

若不禁用 python 绑定，还会在更早处中断：

```text
Asking python-config for pyembed '--cflags --libs --ldflags --embed' flags : yes
Testing pyembed configuration : Could not build a python embedded interpreter
err: ld.lld: error: unable to find library -lintl
The configuration failed
```

另：直接执行 `buildtools/bin/waf` 会被拒绝（`PYTHONHASHSEED=1 missing! Don't use waf directly, use ./configure and make!`），必须走源码根目录的 `configure`/`make` 包装脚本。

## 根因

Samba 系独立库（tdb/talloc/ldb/tevent）用自带 waf（wafsamba）而非 autotools/cmake：

1. **调用链要求**：`configure` 包装脚本执行 `$PYTHON buildtools/bin/waf configure "$@"`（要求 `PYTHON` 环境变量指向可用 python3；脚本自行 `export PYTHONHASHSEED=1`、`unset LD_PRELOAD`）；`make` 包装脚本以 `WAF_MAKE=1` 调用 waf。必须在**源码根目录原地构建**——`wscript` 的 `conf.IN_LAUNCH_DIR()` 决定 `standalone_tdb`（否则会去找系统 tdb 包）。本包内置 waf 为 2.1.6，其 `waflib/Context.py` 已带 python≥3.12 兼容 shim（E339 所述旧版 `imp` 问题**未触发**）。
2. **mandatory 运行探针**：`lib/replace/wscript` 的 `HAVE_SECURE_MKSTEMP` 探针 `execute=True` 运行程序，硬编码写 `/tmp/test.XXXXXX` 并断言文件权限为 `0600`。OHOS `/tmp` 只读（E002），且 HMDFS 将新建文件权限归一化为 `0640`（chmod 不生效，E046）——探针**在任何可写目录都不可通过**；上游又标了 `mandatory=True`（源码注释 "lets see if we get a mandatory failure for this one"），configure 直接中止。
3. **python 绑定探针的链接缺陷**：`buildtools/wafsamba/samba_python.py` 的 `SAMBA_CHECK_PYTHON_HEADERS` 走 waf 的 `check_python_headers()`，其 `test_pyembed` 用 `python3-config --embed` 输出的链接参数；平台 python 的该输出带 `-lintl`，而 musl 无 libintl（`Checking for library intl : no`）→ `ld.lld: unable to find library -lintl` → fatal。

## 方案（可跨库复用）

**A. 调用链（conan 配方内）**：

```sh
cd <src>
PYTHON=python3 ./configure --prefix=<pkg> --disable-python && make -jN && make test
```

- `PYTHON` 由配方显式传入（R33：不依赖未定义 shell 环境变量）；
- 原地构建（不另设 build dir），`--prefix` 直接指向包目录，无需 DESTDIR；
- 测试用 `make test`（waf `testonly`），见 DRAFT-11055-WAF-TESTONLY-EXECUTION-ACCOUNTING。

**B. 强制运行探针的处置**：把沙箱内必失败的 `execute=True + mandatory=True` 探针改为非致命（`mandatory=True`→`False`），让检查**如实**报 `not found`，由 `lib/replace` 自动编译内置替代实现（`REPLACE_MKSTEMP` 等）：

- 不在补丁里硬编码 `/dev/shm` 等设备路径换"通过"；
- 不放宽 0600 断言语义；
- 不引入 `__OHOS__` 平台宏（R8/PF5）；
- 报告中如实记录探针结果为 not found（这一条恰好说明"使用的是内置实现"）。

**C. python 绑定决策树**：

1. 包定位为 C 库 → `--disable-python`（官方选项；同时避免包与构建机 python ABI 耦合）；
2. `--disable-python` 不会让 `SAMBA_CHECK_PYTHON` 停止记录 `python_interpreters`（仍会把 python3 记入），`testonly` 因而仍会跑 `python/tests/simple.py` → 需同步守卫（见第二篇草稿）；
3. 需要启用 pytdb 时，先修复平台 `python3-config --embed` 的 `-lintl` 依赖，或经 `PYTHON_PYEMBED_LDFLAGS` 类环境变量注入正确链接参数（waf 的 `python_cross_compile()` 旁路），并评估 python ABI 耦合。

**D. robust mutex（引用，不新增）**：musl 未实现 `pthread_mutexattr_setrobust`，`lib/replace` 自动探测为否，`USE_TDB_MUTEX_LOCKING` 自动关闭，**无需补丁**（E192 已覆盖该修法；本条只记录"wafsamba 自动探测"这一构建开关层事实，37 个含 mutex 的单测在无 robust mutex 模式下全过）。

## 真实验证

- tdb 1.4.15 设备实机：`PYTHON=python3 ./configure --prefix=... --disable-python` rc=0；`make -j2` rc=0（122 tasks）；`make test` rc=0（37 TAP 单测 + 2 shell 集成 + tdbtorture 全过，python 测试显式跳过）；
- `conan create`（test_package 消费者 9 断言 + 包内 tdbdump）通过（W3 证据见归档 `reports/`）；
- 内置 waf 版本核对：`third_party/waf/waflib/Context.py` 的 `if sys.hexversion > 0x3040000:` 兼容分支在 python 3.14.7 下工作正常。

## 禁忌

- ❌ 探针目录硬编码 `/dev/shm`、放宽 0600 断言、`chmod` 探针二进制等"制造通过"（欺骗性适配）；
- ❌ 在补丁/配方中注入 `-D__OHOS__`（R8/PF5）；
- ❌ 绕过 `configure`/`make` 包装脚本直调 `buildtools/bin/waf`（会被 `PYTHONHASHSEED`/`WAF_MAKE` 守卫拒绝，行为不可复现）；
- ❌ 把 E339（旧版 waf 的 `imp` 模块修复）当作本条的"触发问题"——tdb 1.4.15 实测未触发，仅作为版本核对项引用。

## 适用范围与边界

- **适用**：所有 Samba wafsamba 系独立包（tdb/talloc/ldb/tevent 及其同门）在 OHOS 的独立构建；`lib/replace` 探针族、waf 包装脚本、python 绑定决策三处可直接复用。
- **边界/反例**：
  - 内置 waf 版本 < 2.0.18 或 Context.py 无 `types.ModuleType` shim 时，会触发 E339 的 `imp` 问题（需按 E339 打补丁）——**本条与 E339 是正交的两个面**：E339 管"旧 waf 能否启动"，本条管"能启动后构建能否通过、测试怎么跑"；
  - 探针改为非致命依赖 `lib/replace` 自带替代实现可用（musl 下已实测）；若替代实现缺失或语义不符，应评估 waf `--cross-answers`（需逐项证明答案与真机语义一致），不得改断言语义；
  - pytdb 属可选特性：禁用不改变 C 库功能与上游 C 测试覆盖。
- **解除条件**：上游/平台修复 `/tmp` 可写与 HMDFS 权限语义后，非致命化补丁可回归为上游原状。

## 与现有知识库的关系（查重）

| 既有条目 | 内容 | 本条增量 |
|---|---|---|
| **E339**（waf/`imp` 模块级修复） | 旧版 bundled waf 在 python≥3.12 的 `imp.new_module` 崩溃及修法 | **不重复**。tdb 1.4.15 内置 waf 2.1.6 已带 shim，E339 未触发；本条覆盖"探针/调用链/绑定决策"的构建体系级范式（E339 正交所不覆盖的层） |
| **E192**（musl robust mutex 条件编译） | 用平台守卫排除 `pthread_mutexattr_setrobust` | **不重复**。本任务无需补丁：wafsamba 自动探测并关闭 `USE_TDB_MUTEX_LOCKING`；本条仅把它记为决策树的一支（构建开关层事实） |
| E002/E046/E047（/tmp 只读、chmod 不生效、HMDFS 权限归一化） | 平台文件语义的**现象与判定** | 本条新增"这些现象如何**必然击穿 wafsamba 的 mandatory 运行探针**，以及最小、诚实、可跨库复用的处置范式"（引用前三者作为根因证据，不重复其内容） |
| E528（OHOS autotools env closure） | autotools 在 shadow CI 的工具链/PATH 闭合 | 正交：本条针对 **waf** 调用链与探针体系，且明确禁止套用 autotools 的 `replace_in_file` 修法 |
| E490（autotools helper 脚本执行位） | 源包脚本执行位恢复 | 不适用：waf 构建不依赖 autotools helper；`configure` 包装脚本随 tar 保留了执行位 |

`draft-review` 预审（2026-09-16，knowledge/graph/index.tsv 766 条）：质量预检 signature/root_cause/rec 全 ✅；TOP5 相似度 E357=0.11、**E339=0.11**（sig=0.0、kw=0.04、cat=0.5——仅类别词重合，错误面与修法均不同）、E320=0.04、E375=0.03、E192=0.01 → **预审建议 create（疑似新知）**。

