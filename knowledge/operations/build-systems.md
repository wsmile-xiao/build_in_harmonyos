# 构建系统识别与适配策略

## 1. 构建系统类型

| 构建系统 | 识别特征 | 配置文件 | 适配方式 | 示例软件 |
|---------|---------|---------|---------|---------|
| **Autotools** | 存在 `configure` 脚本 | `configure.ac`, `Makefile.am` | 修改 `config.guess`, `config.sub` | libffi, bash, coreutils |
| **CMake** | 存在 `CMakeLists.txt` | `CMakeLists.txt`, `*.cmake` | 添加平台检测 | zlib |
| **自定义 Perl** | 存在 `Configure` (大写) | `Configurations/*.conf` | 添加配置文件 | OpenSSL |
| **Meson** | 存在 `meson.build` | `meson.build` | 添加平台检测 | systemd |
| **Makefile** | 存在 `Makefile` | `Makefile`, `*.mk` | 直接修改 | bzip2 |
| **QMake** | 存在 `.pro` 文件 | `*.pro` | 修改 .pro 文件 | Qt 项目 |
| **无构建/打包族** | 无 configure/CMakeLists/meson.build/Makefile 编译目标（header-only 库/数据资源/脚本工具） | 源码树无构建文件 | 纯 copy 打包 + `self.info.clear()` | doctest, datafile（见 §12，v12.21） |
| **Python C 扩展** | 存在 `setup.py` 且含 `build_ext`/`ext_modules`/Cython 源 | `setup.py`, `*.pyx`, `*.c` | setuptools 交叉编译覆盖 CC/CFLAGS/LDSHARED | lxml, pycairo（见 §14） |

## 2. 构建系统识别命令

```bash
# 检测脚本
check_build_system() {
    if [ -f "configure" ] && [ -x "configure" ]; then
        echo "Autotools"
    elif [ -f "CMakeLists.txt" ]; then
        echo "CMake"
    elif [ -f "Configure" ] && [ -x "Configure" ]; then
        echo "Custom-Perl"
    elif [ -f "meson.build" ]; then
        echo "Meson"
    elif [ -f "Makefile" ] || ls *.mk 1>/dev/null 2>&1; then
        echo "Makefile"
    else
        echo "Unknown"
    fi
}
```

## 3. Autotools 适配

### 3.0 核心原则：不欺骗构建系统

> **重要原则**：永远不要通过伪造三元组（如 `--build=aarch64-unknown-linux-gnu`）来欺骗 configure。
> 
> 这种做法虽然可能暂时解决问题，但会导致：
> 1. 构建系统对平台特性的错误判断
> 2. 缺失正确的平台特定代码路径
> 3. 编译产物可能与预期不符
> 4. 无法复用补丁和经验

**正确做法**：为 HarmonyOS 添加正式的三元组支持：
1. 修改 `config.guess` 添加 HarmonyOS 识别
2. 修改 `config.sub` 添加 `linux-ohos` 支持
3. 如有必要，修改 `configure.ac` 添加平台分支

**三元组格式**：`{架构}-{厂商}-{操作系统}`
- 标准格式：`aarch64-unknown-linux-ohos`
- 表示：ARM64 架构，未知厂商，基于 Linux 的 HarmonyOS

<!-- ~~### 3.1 修改 config.guess~~ → 已迁移至 graph/E007.kv + doc/E007.md -->

<!-- ~~### 3.2 修改 config.sub~~ → 已迁移至 graph/E007.kv + doc/E007.md (config.guess/sub 配套修改), graph/E072.kv + doc/E072.md (config.sub 三元组验证失败) -->

### 3.3 编译命令

```bash
# 本地构建（最简配置）
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make install
```

<!-- ~~### 3.4 交叉编译必须设置 --host/--build/--target~~ → 已迁移至 graph/E007.kv + doc/E007.md (config.guess 失败时的 fallback 方案) -->

<!-- ~~### 3.5 交叉编译工具链的 include 路径需要显式指定~~ → 已迁移至 graph/E015.kv + doc/E015.md -->

### 3.6 Autotools 源码修改层级决策树

> **核心原则**：修改越靠近源头越好。生成文件（configure/Makefile）的修改是最后手段。

#### 层级优先级（从高到低）

```
优先级 ①（最佳）：configure.ac / CMakeLists.txt / 源码 .c/.h 文件
    ↓  autoconf/automake/cmake 重新生成
优先级 ②（可接受）：configure / Makefile.in（autoconf 生成的中间文件）
    ↓  config.status / make 重新生成
优先级 ③（ workaround）：Makefile（make 过程生成的文件）
    ↓ 直接生效，但 make clean 后丢失
优先级 ④（禁止）：sed 操作二进制/运行时修改已编译产物
```

#### 决策流程图

```
需要修改编译行为？
    │
    ├─ 软件有 configure.ac？
    │   └─ ✅ → ① 修改 configure.ac + re-autoconf
    │            例：添加 case "*ohos*)" 分支禁用某功能
    │
    ├─ 只有 configure（无 configure.ac）？
    │   └─ ✅ → ② 修改 configure 本身
    │            例：在平台检测 case 中添加 *ohos* 匹配
    │            ⚠️ 记录：此修改在 autoreconf 后会丢失
    │
    ├─ 需要改变编译标志/链接库？
    │   └─ 检查 Makefile.am 是否存在
    │       ├─ 有 → ① 修改 Makefile.am + re-automake
    │       └─ 无 → ② 修改 Makefile.in 或 ③ Makefile
    │
    └─ 需要修复源码 bug？
        └─ ✅ → ① 直接修改 .c/.h 文件（永远是最高优先级）
           必须带 #ifdef __OHOS__ 守卫
```

#### 各层级的典型场景和示例

| 层级 | 典型场景 | 示例 |
|------|---------|------|
| **①** 源码/配置源码 | 平台特定代码路径、功能开关 | `#ifdef __OHOS__` 守卫的替代实现 |
| **①** configure.ac | 新增平台检测、条件编译选项 | `case "*ohos*)" ohos=yes ;;` |
| **②** configure | 平台检测 case 分支、库搜索路径 | config.guess 已识别但 configure 未处理 |
| **②** Makefile.in | 链接标志、安装路径模板 | `LDFLAGS += -lxxx` for ohos |
| **③** Makefile | 临时调试、快速验证 | `CC = clang` 替换 |
| **④** ❌ 禁止 | sed 操作 configure/Makefile | 绝对不允许 |

#### 特殊情况：内嵌依赖的 config.guess

当软件内嵌了其他项目的旧版 config.guess（如 pkg-config 内嵌 glib 2.38.2 的 config.guess），**无法通过修改主包的 config.guess 解决**。

**策略选择**：

| 方案 | 可行性 | 推荐度 |
|------|--------|--------|
| A. 为内嵌依赖单独打补丁 | ✅ 最佳但工作量大 | ⭐⭐⭐ 长期目标 |
| B. 强制指定 --build/--host 覆盖 | ✅ 立即可行 | ⭐⭐ 短期 workaround |
| C. --with-internal-glib 禁用内嵌依赖 | 视软件而定 | ⭐ 如可用则最干净 |

**方案 B 的正确使用方式**：
```bash
# 使用 --build/--host 作为兜底，不是首选方案
# 必须在 manifest.yaml build_cleanliness 中记录为技术债务
./configure --prefix=$PREFIX \
    --build=aarch64-unknown-linux-ohos \
    --host=aarch64-unknown-linux-ohos
# 原因：glib 内嵌 config.guess(2014) 无 HarmonyOS 检测
# 改进计划：为 glib 的 config.guess 打补丁后去掉此参数
```

### 3.7 OHOS 平台隔离标准写法

> **原则**：所有平台特定的代码修改必须使用标准化的隔离写法，
> 确保 OHOS 相关代码易于识别、不影响其他平台、便于上游接受。

#### 三种标准模板

**模板 A：C/C++ 源码中的预编译守卫**

```c
/* HarmonyOS: <具体原因，如 "fstat() 对非文件 fd 返回 EACCES"> */
#ifdef __OHOS__
/* 替代实现或安全回退 */
static inline int ohos_fstat_compat(int fd, struct stat *st) {
    if (fstat(fd, st) == 0) return 0;
    if (errno == EACCES || errno == EPERM) {
        memset(st, 0, sizeof(*st));
        st->st_blksize = 4096;
        return 0;
    }
    return -1;
}
#define compat_fstat(fd, st) ohos_fstat_compat((fd), (st))
#else
#define compat_fstat(fd, st) fstat((fd), (st))
#endif
```

**模板 B：configure / configure.ac 中的平台分支**

```bash
# 在 configure.ac 中（优先级 ①）
case "$host_os" in
    *ohos*)
        # HarmonyOS 特定配置
        ac_cv_func_fstatat0=no      # 禁用不可靠的检测
        ;;
esac

# 在 configure 中（优先级 ②，如果无法修改 configure.ac）
# 找到对应的 case "$host_os" in 分支，添加 *ohos*) 模式
```

**模板 C：Makefile / Makefile.am 中的条件编译**

```makefile
# 在 Makefile.am 中（优先级 ①）
if OHOS
    CFLAGS += -D__OHOS__ -Wno-error=deprecated-declarations
endif

# 或在 configure.ac 中定义 AM_CONDITIONAL:
AM_CONDITIONAL([OHOS], [echo "$host_os" | grep -q "ohos"])
```

#### 命名规范

| 元素 | 规范 | 示例 |
|------|------|------|
| 宏/函数名前缀 | `ohos_` 或 `_ohos` | `ohos_fstat_compat()` |
| 变量名 | `_ohos` 后缀 | `ac_cv_func_xxx_ohos` |
| 补丁文件描述 | 以 `ohos-` 开头 | `0001-ohos-fix-fstat-for-non-file-fd.patch` |
| 条件编译注释 | 以 `HarmonyOS:` 开头 | `/* HarmonyOS: musl 不支持 */` |

<!-- ~~§3.8 补丁文件元数据规范~~ → 已迁移至 graph/principles.kv (P-PATCH-004) -->
<!-- 核心要求: 补丁 header 必须含 Source-Commit / Modification-Layer / Knowledge-Ref -->

### 3.9 Makefile sed 自动化机制

> 当必须在优先级③（Makefile）做修改时（如 glib 太老无法 re-autoconf），需要确保修改在 `make clean` 后不会丢失。

#### 问题场景

```
./configure → 生成 Makefile
sed -i 's/-Werror//' Makefile    # 临时修改
make && make install               # ✅ 成功
make clean                         # 清理
# 此时 Makefile 可能被重新生成或保留，取决于项目
./configure                        # 再次 configure
# sed 修改丢失！❌ 需要重新执行 sed
```

#### 推荐方案：post-configure hook 脚本

```bash
# 创建 scripts/post-configure-hook.sh（放在软件档案目录下）
#!/bin/sh
# post-configure-hook.sh — 在每次 ./configure 之后执行
# 用于处理无法通过补丁解决的优先级③修改

set -e

BUILD_DIR="${1:-.}"

# Example: glib Werror fix for pkg-config's embedded glib 2.38.2
if [ -f "$BUILD_DIR/glib/Makefile" ]; then
    sed -i 's/CFLAGS = /CFLAGS = -Wno-error=deprecated-declarations /' \
        "$BUILD_DIR/glib/Makefile"
    echo "  [hook] Applied glib CFLAGS workaround"
fi

echo "  [hook] post-configure complete"
```

**使用方式**：

```bash
# 在 Phase 3 编译执行中：
./configure --prefix=$PREFIX ...
bash scripts/post-configure-hook.sh "$(pwd)"   # ← 每次 configure 后执行
make -j1
```

**manifest.yaml 中记录**：

```yaml
build_config:
  post_configure_hook: scripts/post-configure-hook.sh
  hook_reason: "glib 2.38.2 Makefile uses -Werror, cannot patch at layer ①/②"
```

#### 方案对比

| 方案 | 可靠性 | 复杂度 | 推荐度 |
|------|--------|--------|--------|
| post-configure hook 脚本 | ✅ 高（显式、可审计） | 低 | ⭐⭐⭐ **首选** |
| notes.md 手动记录步骤 | ⚠️ 中（依赖人记忆） | 最低 | ⚠️ 仅用于极简情况 |
| 写入 Makefile 的 EXTRA_CFLAGS 覆盖 | ✅ 高（如果支持） | 中 | ⭐⭐ （需 configure 支持） |

---

## 4. CMake 适配

### 4.1 平台检测

在 `CMakeLists.txt` 中添加：

```cmake
# 检测 HarmonyOS
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OpenHarmony")
    set(OHOS TRUE)
    add_definitions(-D__OHOS__)
endif()
```

### 4.2 编译命令

```bash
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      ..
make -j$(nproc)
make install
```

### 4.3 Header-only CMake 库

Header-only C++ 库（如 doctest、catch2、fmt header-only 模式）使用 CMake 在鸿蒙上编译无需任何源码修改。只需标准 cmake configure + make install DESTDIR 流程。

**特征识别**：
- `CMakeLists.txt` 中无 `add_library(... SHARED|STATIC)` 或只有 `INTERFACE` 库
- 产物仅为头文件（`.h`/`.hpp`），无二进制输出

**编译流程**：
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

**验证**：确认安装目录仅含 `include/`，无 `bin/`、`lib/`（或仅有 cmake 配置文件）。

**适用软件**：doctest 2.5.2 及类似 header-only 库。

## 5. 自定义 Perl Configure（OpenSSL 风格）

### 5.1 添加配置文件

创建 `Configurations/15-openharmony.conf`：

```perl
my %targets = (
    "openharmony" => {
        inherit_from     => [ "linux-generic32.0" ],
        template         => 1,
        cflags           => add("-D__OHOS__"),
        cppflags         => add("-D__OHOS__"),
        cxxflags         => add("-D__OHOS__"),
        thread_scheme    => "pthreads",
        dso_scheme       => "dlfcn",
        shared_target    => "linux-shared",
        shared_cflag     => "-fPIC",
    },
    "openharmony-aarch64" => {
        inherit_from     => [ "openharmony", "linux-aarch64" ],
    },
);
```

### 5.2 修改 Configure 脚本

添加自动检测逻辑：

```perl
# 检测 HarmonyOS
if ($target eq "" && -x "/system/bin/getprop") {
    my $sysname = `uname -s 2>/dev/null`;
    if ($sysname =~ m/harmonyos|openharmony/i) {
        $target = "openharmony-" . `uname -m`;
    }
}
```

### 5.3 编译命令

```bash
# OpenSSL 编译
./Configure --prefix=$HOME/usr/local \
            --openssldir=$HOME/usr/local/ssl \
            no-asm \
            openharmony-aarch64

make -j$(nproc)
make install
```

## 6. Makefile 直接修改

对于简单的 Makefile 项目，直接修改：

```makefile
# 添加编译器设置
CC = clang
AR = llvm-ar
RANLIB = llvm-ranlib

# 添加编译标志
CFLAGS += -fPIC -D__OHOS__

# 添加安装前缀
PREFIX ?= $(HOME)/usr/local
```

## 7. 构建系统对比

| 方面 | Autotools | CMake | Custom-Perl |
|------|-----------|-------|-------------|
| 学习曲线 | 中等 | 较高 | 低（OpenSSL 特有） |
| 平台检测 | config.guess | CMAKE_SYSTEM_NAME | Configure 脚本 |
| 三元组支持 | ✅ 原生 | ❌ 需手动 | ❌ 使用目标名 |
| 交叉编译 | ✅ 优秀 | ✅ 优秀 | ⚠️ 需配置 |
| 鸿蒙适配难度 | 中等 | 简单 | 中等 |

<!-- ~~## 8. 常见问题~~ → Q1→E007, Q2→E001, Q3→E016 -->

## 9. 测试原则

### 9.1 必须执行官方测试套件

> **核心原则**：编译完成后，必须执行官方测试套件，不能跳过。

**原因**：
1. 验证编译产物的正确性
2. 发现潜在的兼容性问题
3. 为后续用户提供可靠的参考

**测试命令**：

| 构建系统 | 测试命令 |
|----------|----------|
| Autotools | `make check` |
| CMake | `ctest` 或 `make test` |
| Makefile | `make test`（如有） |
| 自定义 | 查看项目文档 |

### 9.2 测试结果分类

测试失败时，需要区分两类问题：

| 类型 | 特征 | 示例 |
|------|------|------|
| **编译问题** | 功能本身不工作 | 链接错误、段错误、输出错误 |
| **环境兼容性问题** | 功能正常但测试框架不兼容 | BusyBox 缺少选项、PTY 不可用 |

**处理方式**：
- 编译问题：必须修复后重新编译
- 环境兼容性问题：在 manifest.yaml 和测试报告中记录，标记为"不影响核心功能"

### 9.3 测试报告模板

```markdown
# XXX 测试报告

## 测试结果汇总

| 测试项 | 结果 |
|--------|------|
| test1 | ✅ PASS |
| test2 | ❌ FAIL |

## 失败分析

### test2

**失败原因**: ...

**影响范围**: ...

## 结论

兼容性评级: 高/中/低
```

### 9.4 manifest.yaml 测试结果字段

```yaml
test_results:
  type: official  # official | manual | skipped
  total: 6
  passed: 5
  failed: 1
  note: |
    详细说明测试结果和失败原因
```

## 10. 特殊构建场景

<!-- ~~§10.1 automake 鸡生蛋问题~~ → 已迁移至 graph/E069.kv + doc/E069.md -->
<!-- 现象: @am_AUTOCONF@ 未替换变量 | 方案: gen-all.pl + sed 或 /bin/true 绕过 -->

### 10.2 无 32 位兼容层的软件

<!-- ~~§10.2 无 32 位兼容层~~ → 已迁移至 graph/E070.kv + doc/E070.md -->
<!-- 现象: m32 personality 不支持 | 方案: --disable-mpers -->

### 10.3 automake 版本不匹配

<!-- ~~§10.3 automake 版本不匹配~~ → 已迁移至 graph/E071.kv + doc/E071.md -->
<!-- 现象: requires automake >= X.Y but A.B installed | 方案: ACLOCAL=/bin/true 绕过 或 VPATH 构建 -->

### 10.4 VPATH 构建避免 autotools 重生成

**问题**：某些 autotools 项目在 make 过程中会检测源码时间戳，如果比生成的 Makefile.in 更新，会尝试调用 autotools 重新生成，导致失败或无限循环。

**解决方案**：使用 VPATH（out-of-tree）构建，将源码和构建产物分离：

```bash
# 源码目录（保持只读，不修改时间戳）
$HOME/man-db-src/

# 构建目录（所有编译产物在这里）
$HOME/build-man-db/

cd $HOME/build-man-db
ACLOCAL="/bin/true" AUTOHEADER="/bin/true" AUTOMAKE="/bin/true" \
  ../man-db-src/configure --prefix=$HOME/usr/local
make -j1
make install
```

**优势**：
1. 不触碰源码目录的时间戳，避免触发 autotools 重生成
2. 源码和构建产物分离，方便多配置构建
3. 清理构建产物只需删除构建目录

**注意**：部分 autotools 项目的 `make` target 名称在 VPATH 下可能不同（如 `make mandb` vs `make src/mandb`），需要检查实际 Makefile。

**适用软件**：man-db 2.13.1

<!-- ~~### 10.5 上游 config.guess 已含 HarmonyOS 但 config.sub 不完整~~ → 已迁移至 graph/E072.kv + doc/E072.md -->

## 11. Meson 适配详解（v12.21 补——166 配方 4.8%，此前仅一行表格）

### 11.1 识别与工具链

- 识别特征：`meson.build`；上游要求 python3 ≥ 3.7
- Conan 2 标准姿势：`from conan.tools.meson import Meson, MesonToolchain`（模板 `conanfile-meson.py.tmpl`）

### 11.2 交叉编译 ohos 三元组

Meson 的平台判定取自 cross/native file 的 `[host_machine]`。鸿蒙（musl）配置：

```ini
[binaries]
c = 'clang'
cpp = 'clang++'
ar = 'llvm-ar'
strip = 'llvm-strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'linux'          # musl 内核口径用 linux，勿写 ohos（meson 无此系统名）
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
```

> 注意：meson 无 `ohos` 系统名，写 `linux` + musl sysroot 即可；`b_ohos` 之类的伪属性不存在。

### 11.3 常见坑

| 坑 | 症状 | 处置 |
|---|---|---|
| wrap 依赖拉网 | `Downloading ... wrap` 走不出去 | `--wrap-mode=nodownload`，依赖走 conan requires |
| python 纯脚本检测 | 检测脚本用 `os.uname()` 判平台 | 走 subprojects 补丁或 `meson setup -Dxxx` 显式覆盖检测结果 |
| `-Doptimization` 与 build_type | Debug/Release 不一致告警 | MesonToolchain 自动映射，勿手动重复传 |
| samu/ninja 缺失 | `ninja: command not found` | tool_requires("ninja/...")，勿用裸 self.run 绕过 |

## 12. 无构建/打包族（v12.21 新增——普查 26%，此前零模板）

### 12.1 识别

源码树**没有**可编译目标：无 configure/CMakeLists.txt/meson.build/Makefile 的编译规则。三个子类：

| 子类 | 特征 | 例 |
|---|---|---|
| A. Header-only 库 | 仅 .h/.hpp，cpp_info 为空库 | doctest, catch2 |
| B. 数据/资源包 | 字体/配置/表数据，装到 share/ | tzdata, datafile |
| C. 脚本工具 | perl/python/bash CLI，只装不编 | flawfinder, imgp |

### 12.2 模板与要点

- 模板：`templates/conanfile-headeronly.py.tmpl`（三变体注释块，conan-init 可选 `headeronly`）
- 关键点：`package_id()` 里 `self.info.clear()`（无编译 → 单一 package_id，不做平台矩阵）；`no_copy_source = True`
- **R34 同样适用**：test_package 必须写 test.c/test.cpp 真实 include 并调用接口（header-only 也要编一个用到它的翻译单元），不能只 print
- **R51 同样适用**：上游测试三步法照常（header-only 库的上游测试也要清点+运行+如实申报）
- recipe-search：此类配方在 catalog 中标记 `headeronly`/`copy`，相似度 0.30 构建系统权重恢复命中

## 13. QMake（Qt5 存量处理要点，v12.21）

存量 14 例（qt/qt5-*/qscintilla2/dxflib 等）全为 Qt5 系。**新任务不再产生 QMake**（Qt6 已全面 CMake 化），维护存量时注意：

1. PATH 需含宿主 qmake；qmake 生成 Makefile 后走标准 make 流程
2. 平台差异注入用 `.pro` 文件变量（`QMAKE_CXXFLAGS += -D__OHOS__` 须走 R8 例外流程——patches/ 禁令不豁免 .pro）或 `qmake CONFIG+=` 传参
3. mkspecs 无 ohos 规格：用 `linux-clang` mkspec + 手动覆盖 sysroot/编译器变量
4. 优先级判定：若上游同时提供 CMakeLists.txt，改走 CMake 模板（勿为旧 .pro 增加新适配面）

## 14. Python C 扩展构建（setup.py build_ext，v12.21）

存量 6 例（lxml/pycairo/python3-cairo/xapian-bindings 等），python-gssapi 系新任务仍会遇到（R47 判定 C/C++ 扩展属合法 cpp 任务，不挂起）：

1. **解释器**：目标机 python3（版本须与 sysconfig 平台标签匹配）；宿主跑 setup.py 用 `--no-user-cfg`
2. **交叉编译覆盖**：`CC/LDSHARED/AR/CFLAGS/LDFLAGS` 环境变量注入 clang 与 sysroot——setuptools 不理解三元组，只认环境变量
3. **平台标签**：musl 无 manylinux 标签，`bdist_wheel` 会尝试纯平台名——用 `--plat-name=linux_aarch64` 显式指定；扩展含 C 代码不可打成 py3-none-any（R34 同族问题：纯标记包装无编译产物）
4. **Cython 预生成物**：优先用上游发布包里的 .c（勿现场 cythonize，版本漂移会引入构建差异）
5. **conan 依赖注入**：C 扩展链接 conan 库（如 lxml→zlib/libxml2）时，把 `cpp_info` 的 include/lib 路径显式并入 `CFLAGS/LDFLAGS`——setuptools 不会读 conan 包
6. 参考配方：`archives/l/lxml/6.1.1/conanfile.py`、`archives/p/pycairo/1.29.0/conanfile.py`
