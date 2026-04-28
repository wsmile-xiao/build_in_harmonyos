> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# AI 编译执行指南（Step 2 完整内容）

来源: SKILL.md §2 Step 2, §2.1, §2.2, §2.2.1, §2.3, §2.5, §2.6, §2.7

## 概述

> **这是整个流程中唯一需要 AI 判断的环节。** 其余全部自动化。
>
> **⚠️ 核心原则：`--prefix` 指向运行时路径（$DEFAULT_PREFIX），用 DESTDIR 做隔离安装。**
>
> **完整执行顺序**：
> ```
> configure(--prefix=$DEFAULT_PREFIX) → make → make install DESTDIR=$TEST_PREFIX
>   → 安全弹窗(R7) → make check
>   → Staging 验证 → ohc-run.py package
>   → ⭐ make install（不带 DESTDIR，安装到 $DEFAULT_PREFIX）
>   → 用户验证（模拟普通用户部署）
>   → ohc-run.py finish
> ```

---

## 2.1 开始编译前的准备

```bash
# ① 加载上下文
source .build-context-<name>-<ver>

# ② 进入源码目录
cd $BUILD_SRC_DIR

# ③ 如有历史补丁，应用它们
if [ "$BUILD_HISTORY_FOUND" = "true" ]; then
    for p in $BUILD_ARCHIVE_DIR/patches/*.patch; do
        patch -p1 < "$p"
    done
fi

# ④ 识别构建系统（如需要）
${SKILL_ROOT}/scripts/ohc-run.py detect-build-system (已废弃，请使用 ohc-run.py engine) .  # 可选，context 已含 BUILD_SYSTEM
```

### 2.1.1 预编译风险扫描（build Step 2.5，自动执行）

> `ohc-run.py build` 在 Step 2（apply-patches）之后、Step 3（configure）之前自动执行 pre-scan。

**不需要手动运行。** 但如果使用模式 B（AI 手动编译），建议先运行：

```bash
python3 $SKILL_ROOT/scripts/ohc/pre_scan.py $BUILD_SRC_DIR \
    --rules $SKILL_ROOT/knowledge/graph/pre-scan-rules.yaml \
    --output $BUILD_SRC_DIR/.pre-scan-report.yaml
```

**扫描内容**：
1. **规则集扫描**：从 `pre-scan-rules.yaml` 读取已知风险 pattern，grep 源码
2. **Musl 函数检测**：自动扫描 pthread_cancel、mremap、ppoll、secure_getenv 等高频缺失函数
3. **构建系统检测**：config.guess 存在性、CMake find_library(LIBM m) 等
4. **文件系统风险**：/tmp 硬编码、/etc 路径硬编码

**输出报告**：`$BUILD_SRC_DIR/.pre-scan-report.yaml`

```yaml
findings:
  - rule_id: PSCAN-MUSL-001
    severity: critical
    description: "pthread_cancel 在 musl/OHOS 上不可用"
    hits: ["src/worker.c:42: pthread_cancel(t);"]
    solution_hint: "#ifdef __OHOS__ 跳过 cancel，改用标志位+pthread_join"
```

**AI 如何使用**：阅读 `.pre-scan-report.yaml`，对 critical/high 级别发现提前准备补丁，避免编译失败。

**闭环机制**：编译中新发现的问题在 `graph add` 时可填写 `pre_scan_*` 字段，下次 pre-scan 自动识别同类问题。

---

## 2.2 执行编译（DESTDIR 路径隔离模式）

> **⚠️ 每次操作前必须 source 上下文文件（R11）**：
> ```bash
> # 新会话 / 重新操作前必须执行：
> source .build-context-<name>-<ver>
> echo "TEST_PREFIX=$TEST_PREFIX"   # 确认不为空
> echo "DEFAULT_PREFIX=$DEFAULT_PREFIX"
> ```
> 否则变量为空 → configure 报错 → 浪费 10+ 分钟重跑。

### DESTDIR 路径隔离模式（⭐ 统一标准）

| 变量 | 值 | 说明 |
|------|------|------|
| `$DEFAULT_PREFIX` | `/storage/Users/currentUser/usr/local` | **运行时安装路径**（configure --prefix 使用） |
| `$TEST_PREFIX` | `$TMPDIR/test-install-{name}-{ver}` | **临时安装隔离根**（DESTDIR 使用） |
| `$STAGING_PREFIX` | `$TEST_PREFIX/$DEFAULT_PREFIX`（去掉开头 `/`） | **实际产物位置**（验证/打包时使用） |

> `$STAGING_PREFIX` 示例：`/home/currentUser/tmp/test-install-xxx/storage/Users/currentUser/usr/local`

**原理**：
```bash
# configure 使用运行时路径（会被 bake 进二进制）
./configure --prefix=$DEFAULT_PREFIX

# install 时通过 DESTDIR 隔离到临时目录（不影响系统）
make install DESTDIR=$TEST_PREFIX

# 产物实际位置
ls $STAGING_PREFIX/bin/    # 验证二进制
ls $STAGING_PREFIX/lib/    # 验证库文件
```

**为什么用 DESTDIR**：
1. 二进制硬编码路径天然正确（$DEFAULT_PREFIX 而非临时路径）
2. GNU 标准做法，autotools/cmake/meson 原生支持
3. 打包时直接从 staging 收集，路径结构匹配
4. 无需额外的路径修复步骤

### 各构建系统的 DESTDIR 命令

```bash
# Autotools 项目（标准做法）
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX

# CMake 项目
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX .. && make && make install DESTDIR=$TEST_PREFIX

# Meson 项目
meson setup builddir --prefix=$DEFAULT_PREFIX && ninja -C builddir && ninja -C builddir install

# Makefile 项目（无 configure，使用 PREFIX/DESTDIR）
make PREFIX=$DEFAULT_PREFIX && make PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install
```

**⚠️ P0 参数最少化**：理想状态只需 `--prefix=$DEFAULT_PREFIX` + `DESTDIR=$TEST_PREFIX`。如果必须加额外参数（`--build/--host`/`--without-shared`/CFLAGS hack），记录到 notes.md 并在 manifest.yaml `build_cleanliness` 字段标注为技术债务。

### 变量命名规范（⭐ C01 统一）

> **消除歧义：整个管线中，安装前缀只用 `$DEFAULT_PREFIX` 一个变量名。**

| 变量名 | 含义 | 谁设置 | 谁使用 | 作用域 |
|--------|------|--------|--------|--------|
| **`DEFAULT_PREFIX`** | **唯一权威**的安装前缀路径 | `ohc-run.py init-build` export + 写入 .build-context | **所有脚本**（ohc-run.py verify-build, ohc-run.py package, AI Phase 3） | 全局 |
| `PKGDIR` | 打包工作目录（ohc-run.py package 内部临时目录） | `ohc-run.py package` 设置 | 仅 `ohc-run.py package` 内部 | 局部 |

**历史遗留**：旧文档/代码中可能出现 `$PREFIX`，等同于 `$DEFAULT_PREFIX`（兼容别名），新代码统一使用 `$DEFAULT_PREFIX`。

---

## 2.2.1 make check / make test（⭐ 标准步骤）

> **make install 之后、finish-build 之前，必须执行软件自带的测试套件。**
>
> **⚠️ 遇到问题时的处理顺序（禁止直接跳过）：**
> 1. **先诊断**：是超时？哪个测试卡住？还是编译错误？
> 2. **再尝试**：用 `RUN_TEST_FAILURES=yes` 跳过卡住的测试重跑
> 3. **分析失败原因**：平台限制(E051/E046/E002) vs 真正 bug
> 4. **最后才标记 partial**：确认无法解决后记录原因，继续后续步骤
>
> ohc-run.py build 的 Step 7 已内置此诊断+恢复逻辑（后台监控→卡住检测→SIGUSR1→选择性跳过→重试）

```bash
# Autotools 项目（首选 make check，fallback 到 make test）
make -j1 check 2>&1 | tail -20    # 记录结果到 reports/test-report.md
# 或: make -j1 test 2>&1 | tail -20

# CMake 项目
ctest --output-on-failure 2>&1 | tail -20

# Meson 项目
meson test -C builddir 2>&1 | tail -20
```

### 测试结果处理

| 结果 | 处理方式 |
|------|---------|
| **全通过 (PASS)** | 记录到 `reports/test-report.md`，继续下一步 |
| **部分失败但核心功能 OK** | 分析失败原因 → 平台限制(E051/E046等)则记录并继续；真正的 bug 则修复后重测 |
| **全部失败或 core dump** | 检查是否漏触发安全弹窗(R7) → 重新触发后再跑 |

**⚠️ 鸿蒙特有限制**（导致部分测试预期失败，不阻塞发布）：
- E046: chmod() 不生效 → 权限相关测试失败
- E051: 未实现 syscall → setreuid/chroot 等测试 crash
- `/tmp` 只读（E002）→ 依赖 /tmp 的测试失败
- SELinux 域转换 → 子进程执行 SDK 工具失败

**关键原则**：测试套件的目的是**发现真正的功能回归**，不是追求 100% 通过率。平台限制导致的预期失败应记录原因但不阻塞流程。

---

## 2.2.2 部署到本地 + 用户验证（⭐ package 完成后必须执行）

> **时机**：`ohc-run.py package` 完成后、`ohc-run.py finish` 之前。
> **目的**：将软件安装到 `$DEFAULT_PREFIX`（~/usr/local），模拟普通用户下载预编译包、通过 cmd-pkgs 公共安装脚本部署后的真实状态。
>
> **注意**：driver.py Step 10 已自动执行 deploy（从 staging 复制到 $DEFAULT_PREFIX）。此处为手动验证步骤。

```bash
# driver.py 已自动部署，此处验证安装结果
# 如需手动部署（模拟），可用 make install 不带 DESTDIR：
make install    # 直接安装到 $DEFAULT_PREFIX（configure 已设置 --prefix=$DEFAULT_PREFIX）

# 验证本地安装可用
$DEFAULT_PREFIX/bin/<软件> --version   # 确认可用
pkg-config --modversion <软件>          # 确认 pkg-config 可找到（如适用）
```

> **这一步能发现的问题**：
> - 打包遗漏（缺库、路径错误、配置文件缺失）
> - 二进制硬编码路径与实际安装路径不匹配
> - pkg-config 文件中路径错误
> - 运行时找不到数据文件/配置文件
>
> 这是整个流程的最终闭环验证：DESTDIR 模式下 --prefix=$DEFAULT_PREFIX 被硬编码进二进制，天然正确。但公共安装脚本部署后仍需验证实际运行效果。

---

## 2.3 错误处理与恢复

### 错误分类与标准对策

| 阶段 | 常见错误 | 标准对策 |
|------|---------|---------|
| **configure** | `command not found: xxx` | 缺工具 → 安装或设 ACLOCAL=/bin=true 绕过 |
| **configure** | `cannot run test program` | conftest pipe 问题 → `\| cat` 修复 |
| **configure** | `invalid host: aarch64-unknown-linux-ohos` | config.guess/sub 未识别 → 打补丁 |
| **compile** | `error: xxx.h: No such file` | 缺头文件 → 查依赖链/CFLAGS 加 -I |
| **compile** | `warning: -Werror` | 警告变错误 → CFLAGS 加 -Wno-error 或改 configure.ac |
| **link** | `undefined reference to xxx` | 缺库 → LDFLAGS 加 -lxxx 或查 NEEDED |
| **install** | `symlink: File exists` | HMDFS 限制 → 用 wrapper 脚本或 cp 替代 |
| **install** | `Permission denied` (help2man/sed/install) | 鸿蒙 sandbox 兼容性问题 → 见下方标准参数 |

### make install 标准参数（鸿蒙 sandbox 兼容）

> ⚠️ 以下参数在鸿蒙环境下几乎总是需要，**应作为 configure/make 的默认参数**：
>
> ```bash
> # configure 阶段（从源头避免）
> ./configure --prefix=$DEFAULT_PREFIX \
>     SED=$(find_tool sed) \          # 动态检测：优先 GNU sed，fallback toybox
>     HELP2MAN=/bin/true          # help2man 权限不足（跳过 man page）
>     MAKEINFO=/bin/true           # texinfo 工具缺失
>
> # 或在 make install 阶段覆盖（如 configure 已完成）
> make install DESTDIR=$TEST_PREFIX \
>     SED=$(find_tool sed) \
>     INSTALL=$(find_tool install) \  # 动态检测：优先 GNU install
>     HELP2MAN=/bin/true \
>     MAKEINFO=/bin/true
> ```
>
> **动态检测逻辑**（ohc-run.py build 内置 `find_tool()` 函数）：
> 1. 先找 `$DEFAULT_PREFIX/bin/sed` → `$STAGING_PREFIX/bin/sed` → PATH 中的版本
> 2. 检查 `--version` 输出是否含 "GNU" → 是则使用（功能更强）
> 3. 否则 fallback 到 `/bin/sed`（系统原生 toybox）
>
> 如果仍失败，可跳过非关键子目录：
> ```bash
> make install-binPROGRAMS install-binSCRIPTS SED=... INSTALL=...   # 只装 bin/
> ```

### 失败恢复操作序列

```
configure 失败:
  1. make distclean          # 清理旧配置
  2. 查 error-patterns.md    # 按错误信息匹配已知方案
  3. 修改源码/补丁/configure
  4. 重新 ./configure ...

编译失败 (make):
  1. 读最后 20 行错误         # 定位具体文件和行号
  2. 修复该文件              # 最小改动原则
  3. make -j1                 # 单线程重新编译（避免并行干扰）
  4. 如果还不行 → make clean && make -j1

安装失败 (make install):
  1. 检查是否是软链接问题      # ls -la 验证
  2. 是 → wrapper 脚本替代
  3. 不是 → 检查权限/磁盘空间
```

---

## 2.4 Phase 3 补丁管线规则（⚠️ 强制）

**Phase 3 绝对禁止生成 .patch 文件。**

Phase 3 的职责只有两件事：
1. **修改源码**解决编译问题
2. **在 notes.md 记录**每个修改的意图

原因：Phase 3 源码处于频繁试错状态，此时生成的补丁是中间态。
补丁生成**唯一入口**是 Phase 4 的 `ohc-run.py refresh-patch --auto`。

**允许的操作**：
- ✅ `sed` / 直接编辑源码（解决编译问题）
- ✅ 创建 post-configure hook 脚本（§3.9）
- ✅ 在 notes.md「源码修改清单」中记录

**禁止的操作**：
- ❌ 生成任何 `.patch` 文件
- ❌ 手动写 diff 内容到文件
- ❌ AI 生成补丁文本写入文件
- ❌ copy 之前的 `.patch` 文件

---

## 2.4.1 Phase 3 自包含性检查清单（⭐ R21 强制）

> **时机**：AI 认为编译完成、准备调用 `ohc-run.py finish` 之前。
> **目的**：确保所有手动操作已固化为补丁/规则，构建过程零人工介入。

AI 必须逐项自检：

### 自检清单

- **config.sh 未手动修改**：所有配置差异都通过 `Configure -D` 参数或 `hints/{osname}.sh` 实现？
  - ❌ 反面：`sed -i 's|lddlflags=.*|...|' config.sh`
  - ✅ 正确：`hints/harmonyos.sh` 中设置 `lddlflags='-shared'`

- **无手动编译命令**：所有编译都通过 `make` 规则自动完成？
  - ❌ 反面：`clang -c -o DynaLoader.o DynaLoader.c` 手动执行
  - ✅ 正确：修复 Makefile.PL 依赖后由 `make` 自动编译

- **无手动文件操作**：没有在构建过程中手动 cp/mv/touch 文件？
  - ❌ 反面：`cp libperl.a /some/path/` 手动复制
  - ✅ 正确：Makefile install 规则自动处理

- **补丁覆盖所有修改**：`track-edit` 记录的每个修改都有对应补丁？
  - 用 `ohc-run.py track-edit --status` 检查
  - 未覆盖的修改需要说明原因

- **平台代码有守卫**：所有 `#ifdef`/条件分支使用 `__OHOS__` 或 `$^O eq 'harmonyos'`？
  - 非鸿蒙平台编译不受影响

- **可以一条龙**：确认 `tar xf → patch → Configure → make → make install` 能无人工介入完成？

### 不通过的处理

任何一项不通过 → 不要调用 `ohc-run.py finish`，继续修复：
1. 将手动操作固化为补丁/Makefile 规则/hints 配置
2. 重新运行 `make clean && make` 验证
3. 全部通过后再调用 finish

---

## 2.5 平台检测机制优先（⭐ R23）

> **核心原则**：在修改生成文件（config.h/config.sh/Makefile）之前，先检查软件是否有平台检测钩子。
> 优先使用软件自身机制，不手动修改生成文件（R6 的扩展）。

### 常见软件的平台检测机制

| 构建系统 | 机制 | 示例 |
|----------|------|------|
| autotools | config.guess/config.sub 补丁 | `aarch64-unknown-linux-ohos`（E007） |
| perl | `hints/{osname}.sh` | `hints/harmonyos.sh` |
| cmake | `CMAKE_SYSTEM_NAME` 检查 | `if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")` |
| python | `configure.ac` 平台分支 | `AC_DEFINE(__OHOS__, 1, ...)` |
| makefile | `uname` 条件判断 | `ifeq ($(shell uname -s),HarmonyOS)` |
| node.js | `process.platform` 检查 | `platform === 'ohos'` |

### 决策优先级

```
需要改配置？
├─ 有平台检测机制？→ 用它！（hints/config.guess/cmake 检查）
├─ 没有 → 改 configure.ac/configure.in（源文件）
└─ 没有 .ac → 改 configure（生成文件，最后手段）
```

**铁律**：手动修改 config.sh/config.h 是 Phase 3 的调试手段，不是交付物。交付时必须通过 Configure 参数或平台检测机制替代。

---

## 2.6 实时知识提取决策树（⭐ R17 强制）

每解决一个问题后，立即判断：

```
Q1: 此问题只与本软件有关？
    → 是：只记录到 notes.md
    → 否（其他软件也可能遇到）：
        Q2: 与平台机制相关？（musl/SELinux/文件系统/内核）
            → 是：立即创建知识图谱草稿（L1 平台真理）
            → 否：是构建系统模式？（autotools/cmake 通用问题）
                → 是：创建知识图谱草稿（L2 模式经验）
                → 否：标记 "⏳ 待评估"（Phase 4 处理）
```

### 创建草稿的完整流程

```bash
# Step 1: 先用引擎检查是否已有匹配条目
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志关键行"
# → 如果输出匹配结果（如 "E007 (config.guess)"），直接复用方案
# → 如果没有匹配，继续 Step 2

# Step 2: 查找下一个可用 ID
python3 $SKILL_ROOT/scripts/ohc-run.py graph add
# → 输出 "下一个可用 ID: E096"

# Step 3: 创建草稿（写到 draft/ 目录，不影响正式图谱）
python3 $SKILL_ROOT/scripts/ohc-run.py graph add E096 --draft

# Step 4: 填写关键字段（编辑 .kv 文件）
# 必填：
#   error_signature: 典型错误日志正则（| 分隔，如 "undefined reference to.*getpass|implicit declaration.*getpass"）
#   root_cause: 根因分析（为什么会出现这个错误）
#   match_keywords: 检索关键词（逗号分隔）
#   category: 分类标签（如 libc-compat|musl, platform_detection|cmake）
#   severity: 3=阻塞 / 2=中等 / 1=轻微
#   title: 一句话描述（如 "musl 缺 getpass() GNU 扩展"）
# 推荐：
#   rec_description: 推荐解决方案描述
#   rec_command: 一行修复命令
#   affected_scope: 受影响的软件范围
#   similar_to: 类似的已有条目（如 [E081, E085]）

# Step 5: 补充 .md 文档（编辑 draft 中的 .md 文件）
# 写入：错误特征、根因分析、解决方案、禁止做法、验证命令

# Step 6: 在 notes.md 记录 "知识图谱草稿: E096"
```

### 常见分类标签

| category | 含义 | 示例条目 |
|----------|------|---------|
| `libc-compat\|musl` | musl libc 兼容性 | E081, E085, E093 |
| `platform_detection\|cmake` | CMake 平台检测 | E092 |
| `platform_detection\|autotools` | autotools 平台检测 | E007, E072 |
| `platform_detection\|meson` | Meson 平台检测 | E090 |
| `toolchain\|custom-configure` | 自定义构建系统 | E095 |
| `filesystem\|hmdfs` | HMDFS 文件系统限制 | E011, E018, E050 |
| `security\|selinux` | SELinux 安全策略 | E009, E045, E046 |
| `linkage\|rpath` | 动态链接/RPATH | E042, E073 |

### 草稿位置

```
knowledge/graph/draft/
├── E096-draft-A7F3.kv   # {E编号}-draft-{AgentID}.kv
└── E096-draft-A7F3.md   # {E编号}-draft-{AgentID}.md
```

主编审核后用 `graph add E096` 合并到正式图谱。

---

## 2.7 安全弹窗验证代码

鸿蒙系统首次执行非系统二进制会弹安全确认框，超时未点则进程被杀。

```bash
# make install 后立即触发（在 staging 目录中验证）
find $STAGING_PREFIX/bin -type f -exec {} --version \; 2>/dev/null || true

# make check 前确保已完成弹窗确认
```

---

## 2.8 更新 notes.md

每解决一个问题后**立即**更新 notes.md：
- 当前阶段和时间
- 错误信息 + 根因 + 解决方案
- 源码修改清单（表格：文件 | 原因 | 方式 | 补丁状态）
� | 方式 | 补丁状态）
