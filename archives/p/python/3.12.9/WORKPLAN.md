# Python 3.12.9 鸿蒙适配 — 工作计划与进展

> **创建日期**: 2026-03-27 | **状态**: 🔄 Phase 2 完成
> **基于**: Python 3.9.0 适配经验（24 补丁，83.7% 测试通过率）

---

## 一、任务目标

将 CPython 3.12.9 移植到 HarmonyOS PC 平台（aarch64, musl libc, Clang 15），复用 3.9.0 的适配经验，采用"先分析预判，后编译验证"的工作流。

## 二、编译策略

| 项目 | 值 |
|------|-----|
| Python 版本 | 3.12.9（3.12 系列最终版本） |
| 源码路径 | `/storage/Users/currentUser/python/Python-3.12.9/` |
| 前缀 | `--prefix=$HOME/usr/local` |
| 配置 | `--enable-shared --disable-ipv6` |
| 编译器 | Clang 15.0.4 (LLVM) |
| C 库 | musl libc |
| 不裁剪功能 | 尽可能编译所有模块 |

## 三、依赖库状态

| 依赖 | 版本 | 状态 | 备注 |
|------|------|------|------|
| OpenSSL | 1.1.1w | ✅ 就绪 | HMDFS symlink 问题需注意（E050） |
| libffi | 3.5.2 | ✅ 就绪 | 同上 |
| zlib | 1.3.1 | ✅ 就绪 | |
| ncurses | 6.4 | ✅ 就绪 | 静态库（--without-shared） |
| readline | 8.2 | ✅ 就绪 | |
| gdbm | 1.23 | ✅ 就绪 | 含 libgdbm_compat |
| bzip2 | 1.0.8 | ✅ 就绪 | |
| lzma/xz | 5.6.2 | ✅ 就绪 | |

## 四、工作阶段

### Phase 1: 代码预分析（已完成 ✅）

| # | 任务 | 状态 | 产出 |
|---|------|------|------|
| 1.1 | 拉取源码 + 解压 | ✅ 完成 | Python-3.12.9 目录 |
| 1.2 | 检查依赖库 | ✅ 完成 | 全部就绪（8个库+头文件） |
| 1.3 | 建立归档目录 | ✅ 完成 | archives/p/python/3.12.9/ |
| 1.4 | 全量代码结构分析 | ✅ 完成 | `reports/BUILD_SYSTEM_ANALYSIS.md` |
| 1.5 | 3.9 vs 3.12 规格差异对比 | ✅ 完成 | `reports/BUILD_SYSTEM_ANALYSIS.md` + `reports/LIB_ANALYSIS.md` + `reports/MODULES_ANALYSIS.md` |
| 1.6 | 24 补丁可复用性评估 | ✅ 完成 | `reports/PATCH_REUSABILITY.md`（5直接复用/7需修改/6不需要/6需重写/4新增） |
| 1.7 | 编译风险预判 | ✅ 完成 | `reports/RISK_ASSESSMENT.md`（6高/7中/7低，共20个风险点） |

**Phase 1 关键结论**：
- 整个 3.12.9 源码树中 `__OHOS__` 出现次数为 **0**，需从零开始适配
- setup.py 已移除，构建系统架构发生根本性变化（→ PY_STDLIB_MOD 机制）
- `_posixsubprocess.c` 仍然作为 C 扩展存在（1251行），未内联
- 24 个 3.9 补丁中仅 5 个可直接复用，约 22 个新补丁需要开发

### Phase 2: 补丁开发（已完成 ✅）

| # | 任务 | 状态 | 产出 |
|---|------|------|------|
| 2.1 | Phase 2A: 平台检测层补丁 | ✅ 完成 | 0001-0003 (config.guess/config.sub/configure.ac) |
| 2.2 | Phase 2B: 构建系统补丁 | ✅ 完成 | 0004-0005 (Makefile.pre.in/Setup.stdlib.in) |
| 2.3 | Phase 2C: C 扩展模块补丁 | ✅ 完成 | 0006-0010 (pythread/thread/posixsubprocess/time/posixmodule) |
| 2.4 | Phase 2D: 标准库补丁 | ✅ 完成 | 0011-0018 (sysconfig/posixpath/subprocess/compat/site/multiproc/venv) |
| 2.5 | Phase 2F: 补充遗漏修复 | ✅ 完成 | 0019-0021 (fallocate/missing-fixups/hmdfs-symlink) |
| 2.6 | 补丁完整性校验 | ✅ 完成 | 21 个补丁全部 patch --dry-run 通过 |

**Phase 2 关键结论**：
- 共生成 **21 个补丁**（总计 ~40KB），覆盖 25 个源文件
- 基于 3.9 的 24 补丁经验：5 直接复用 / 7 需修改 / 6 不再需要 / 6 需重写 / 4 新增 → 最终 21 个 3.12 补丁
- 3 个高风险项有对应补丁覆盖：R1(configure 平台检测→0001-0003)、R3(musl BIND_NOW→0003+0004)、R6(HMDFS symlink→0021)
- subprocess 适配（0013-0015）完全重写，利用 3.12 的 `_use_posix_spawn()` 新架构
- 新增 `_harmonyos_compat.py` 兼容层，替换 `os.system()`/`os.popen()` 为 subprocess 实现

### Phase 3: 编译验证

| # | 任务 | 状态 | 产出 |
|---|------|------|------|
| 3.1 | configure 阶段 | ⏳ | logs/configure.log |
| 3.2 | make 编译阶段 | ⏳ | logs/build.log |
| 3.3 | make install | ⏳ | logs/install.log |
| 3.4 | 扩展模块导入验证 | ⏳ | reports/EXTENSION_VERIFICATION.md |
| 3.5 | 官方测试套件 | ⏳ | reports/TEST_REPORT.md |

### Phase 4: 归档与知识沉淀

| # | 任务 | 状态 | 产出 |
|---|------|------|------|
| 4.1 | manifest.yaml | ⏳ | 归档元数据 |
| 4.2 | README.md | ⏳ | 编译指南 |
| 4.3 | 知识库更新 | ⏳ | error-patterns.md 等 |
| 4.4 | 分析预测准确性复盘 | ⏳ | reports/PREDICTION_REVIEW.md |

---

## 五、预判关键差异（3.9 → 3.12）

| 维度 | 3.9 | 3.12 | 风险等级 |
|------|-----|------|---------|
| 构建入口 | setup.py | `PY_STDLIB_MOD` 宏 + Modules/Setup 机制 | 🔴 高（R2） |
| distutils | 存在 | 完全移除 | 🟢 低（补丁 0005/0024 不再需要） |
| _posixsubprocess | C 扩展模块 | **仍为 C 扩展**（1251行，未内联） | 🟡 中 |
| subprocess.py | 需大幅改造 | 新增 `_use_posix_spawn()` 路径 | 🔴 高（R4） |
| multiprocessing | 默认 fork | macOS 改 spawn，Linux 仍 fork | 🟡 中（R13） |
| venv | symlink 回退 | `symlink_or_copy` 已有回退 | 🟢 低（lib64 处仍需小改） |
| _bootsubprocess | 存在 | **已移除** | 🟢 低（补丁 0006 不再需要） |
| cpu_count /proc | 未使用 | 新增 Linux /proc 路径 | 🟡 中（R9，新增问题） |
| _hacl/ 哈希库 | 不存在 | 新增内置 HACL* 哈希实现 | 🟡 中（新增需验证） |
| threading.get_native_id | 补丁 0012+0021 | 仍需适配 | 🟢 低（代码结构相同） |
| ctypes.util find_library | 补丁 0022 | 不再崩溃（自然返回空） | 🟢 低 |

## 六、3.12 新增/变更特性清单

### 6.1 新增模块/文件
- `_zoneinfo.c` — IANA 时区数据库（PEP 615）
- `_hacl/` — HACL* 内置哈希库（SHA2/3/BLAKE2/MD5/SHA1）
- `_uuidmodule.c` — 内置 UUID
- `_typingmodule.c` — C 加速 typing
- `_xxinterpchannelsmodule.c` — 子解释器通道
- `Modules/Setup.bootstrap.in` — 引导静态模块配置模板
- `Modules/Setup.stdlib.in` — 标准库扩展模块配置模板
- `Programs/_freeze_module.py` — Python 冻结工具

### 6.2 移除模块/文件
- `setup.py` — 完全移除
- `Lib/distutils/` — 完全移除
- `Lib/_bootsubprocess.py` — 已移除

### 6.3 构建系统变更
- `PY_STDLIB_MOD` / `PY_STDLIB_MOD_SET_NA` 宏系统（105处使用）
- `Modules/makesetup` 成为核心构建引擎
- `PY3LIBRARY` 变量（libpython3.so）
- Emscripten/WASI 完整支持

---

## 七、记录索引

| 文档 | 位置 | 状态 |
|------|------|------|
| 工作计划（本文档） | `WORKPLAN.md` | ✅ 已创建 |
| 源码结构分析 | `reports/SOURCE_STRUCTURE_ANALYSIS.md` | ⏳ |
| 规格差异对比 | `reports/SPEC_DIFF_ANALYSIS.md` | ⏳ |
| 补丁可复用性 | `reports/PATCH_REUSABILITY.md` | ⏳ |
| 风险评估 | `reports/RISK_ASSESSMENT.md` | ⏳ |
| 编译日志 | `logs/` | ⏳ |
| 测试报告 | `reports/TEST_REPORT.md` | ⏳ |
| manifest.yaml | `manifest.yaml` | ⏳ |
| README.md | `README.md` | ⏳ |

---

*创建者: OpenDesk | 基于 Python 3.9.0 适配经验*
