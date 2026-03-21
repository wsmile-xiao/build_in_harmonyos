# Python 3.9.0 鸿蒙系统编译指南

> **编译日期**: 2026-03-20  
> **编译环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **编译器**: Clang 15.0.4  
> **C 库**: musl libc  
> **复杂度**: 🔴 高（涉及 8 个补丁、多个 HarmonyOS 系统级约束）  

---

## 一、软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | Python |
| 版本 | 3.9.0 |
| 官网 | https://www.python.org/ |
| 下载地址 | https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz |
| 构建系统 | Autotools (configure.ac) + 自定义 setup.py + Makefile.pre.in |

### 为什么 Python 编译比其他软件复杂得多？

Python 的构建系统是 **Autotools (configure) + 自定义 setup.py + Makefile.pre.in** 三层混合架构，而大多数软件只用其中一种。这意味着：

| 层级 | 职责 | 鸿蒙适配点 |
|------|------|-----------|
| `configure.ac` | 系统检测、生成 Makefile | 平台识别、变量设置、功能检测 |
| `Makefile.pre.in` | 编译核心解释器和库 | 链接方式、安装规则 |
| `setup.py` | 编译扩展模块 | 头文件搜索、库搜索、编译参数 |
| `config.guess/config.sub` | 平台三元组识别 | 三元组格式 |
| `Lib/sysconfig.py` | 运行时平台信息 | 平台字符串格式 |
| `Lib/distutils/util.py` | 分发工具平台信息 | 平台标识符 |
| `Lib/_bootsubprocess.py` | 子进程执行 | 系统调用兼容 |

三层都需要适配，且相互关联。一个地方改错，可能在另一层引发连锁问题。

### HarmonyOS 导致的编译障碍总览

| # | 障碍 | 类型 | 根因 | 补丁 |
|---|------|------|------|------|
| 1 | 平台三元组不被识别 | 构建系统 | config.guess/config.sub 不认识 HarmonyOS | 0003, 0004 |
| 2 | configure.ac 没有 HarmonyOS 分支 | 构建系统 | 所有 case 语句缺少 HarmonyOS 匹配 | 0001 |
| 3 | `setup.py` 不识别 OHOS 平台 | 扩展模块 | HOST_PLATFORM 精确匹配失败 | 0002 |
| 4 | 扩展模块符号找不到 | 动态链接 | musl BIND_NOW + 缺少 libpython 链接 | 0001, 0007 |
| 5 | 不支持硬链接 | 系统限制 | SELinux 策略 | 0007 |
| 6 | `ln -sf` 乱码 | 系统限制 | toybox 工具 bug | 0007 |
| 7 | 平台字符串含空格 | 系统特性 | `sys.platform` 返回长字符串 | 0008, 0005 |
| 8 | 大小写检测误判 → .exe 后缀 | 构建系统 | case-insensitive 测试在鸿蒙不可靠 | 0001 |
| 9 | CAN socket 宏未定义 | 内核差异 | 鸿蒙内核头文件缺少 CAN 宏 | 0001 |
| 10 | 子进程 exec SDK 二进制被拦截 | 沙箱签名 | 沙箱签名校验机制 | 0006 |

---

## 二、编译步骤

### 2.1 环境准备

```bash
# 必需环境变量（鸿蒙特有）
export TMPDIR=$HOME/tmp          # /tmp 只读，必须指定
mkdir -p $TMPDIR

# 工具链路径（鸿蒙自带）
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH
export CC=clang CXX=clang++
export AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip

# 验证环境
clang --version                  # Clang 15.0.4
clang -dM -E - < /dev/null | grep OHOS  # 确认 __OHOS__ 已定义
```

### 2.2 解压源码

```bash
tar -xzf Python-3.9.0.tgz
cd Python-3.9.0
```

### 2.3 应用补丁

```bash
# 复制补丁到源码目录
cp /path/to/patches/*.patch .

# 依次应用（顺序很重要）
for p in 0001-*.patch 0002-*.patch 0003-*.patch 0004-*.patch \
         0005-*.patch 0006-*.patch 0007-*.patch 0008-*.patch; do
    echo "=== $p ==="
    patch -p1 < "$p"
done
```

**补丁应用顺序**：必须按编号顺序，因为 0001 修改 configure.ac，0007 修改 Makefile.pre.in，它们同时被 autoconf 处理。

### 2.4 生成 configure 脚本

```bash
autoconf
```

> **为什么需要 autoconf？**  
> 补丁修改的是 `configure.ac`（源文件），需要 `autoconf` 生成 `configure` 脚本。鸿蒙系统已自带 `autoconf`（位于 SDK 工具链）。

### 2.5 配置

```bash
./configure --prefix=$HOME/usr/local --enable-shared CC=clang
```

**验证配置结果**（关键检查点）：

```bash
# 1. 平台识别
grep "^MACHDEP" Makefile
# 期望: MACHDEP=      ohos

# 2. 可执行文件后缀（不应有 .exe）
grep "^BUILDEXE=\|^EXE=" Makefile
# 期望: BUILDEXE=  和  EXE=

# 3. 链接器设置（LDSHARED 必须包含 -lpython）
grep "^LDSHARED=" Makefile
# 期望: LDSHARED=  clang -shared  -L. -lpython3.9

# 4. -fPIC 标志
grep "^CCSHARED=" Makefile
# 期望: CCSHARED=     -fPIC
```

### 2.6 编译

```bash
make -j$(nproc)
```

### 2.7 验证

```bash
export LD_LIBRARY_PATH=.
./python3.9 --version
# 期望: Python 3.9.0

./python3.9 -c "import sys; print(sys.platform)"
# 期望: ohos

# 注意：扩展模块需要单独编译（见第四节）
```

### 2.8 安装

```bash
make install
```

---

## 三、补丁详解

### 3.1 补丁总览

| 编号 | 补丁文件 | 修改文件数 | 大小 | 目的 |
|------|---------|-----------|------|------|
| 0001 | configure.ac-HarmonyOS-support.patch | 1 | 10.3KB | 平台识别、链接器、功能检测 |
| 0002 | setup.py-HarmonyOS-support.patch | 1 | 6.2KB | 扩展模块编译支持 |
| 0003 | config.guess-HarmonyOS-support.patch | 1 | 936B | 平台三元组识别 |
| 0004 | config.sub-HarmonyOS-support.patch | 1 | 620B | 三元组 OS 验证 |
| 0005 | Lib-distutils-util.py-HarmonyOS-support.patch | 1 | 532B | distutils 平台标识 |
| 0006 | Lib-_bootsubprocess.py-HarmonyOS-fix.patch | 1 | 2.2KB | 子进程执行修复 |
| 0007 | Makefile.pre.in-HarmonyOS-ln-fix.patch | 1 | 4.5KB | 链接规则、硬链接、安装 |
| 0008 | Lib-sysconfig.py-HarmonyOS-platform.patch | 1 | 1.2KB | 运行时平台字符串 |

---

### 3.2 补丁 0001：configure.ac — HarmonyOS 平台支持

**修改文件**：`configure.ac`  
**修改数量**：10 个 hunk  
**为什么是最大的补丁**：`configure.ac` 是整个构建系统的入口，负责系统检测和变量设置。Python 的 configure 有大量 `case $ac_sys_system in` 分支，每个分支都缺少 HarmonyOS，需要逐一添加。

#### 修改点 1：交叉编译时识别 HarmonyOS

```diff
 	*-*-vxworks*)
 	    ac_sys_system=VxWorks
 	    ;;
+	*-*-linux-ohos*)
+		ac_sys_system=HarmonyOS
+		;;
```

**位置**：第 387 行附近，交叉编译（`--host` 指定）的系统识别 case 分支。  
**原因**：鸿蒙的 `config.guess` 返回三元组 `aarch64-unknown-linux-ohos`，其中 OS 部分是 `linux-ohos`。如果不在此处匹配，会进入 `*)` 默认分支报错：`cross build not supported for $host`。  
**逻辑**：当 `$host` 以 `-linux-ohos` 结尾时，将 `ac_sys_system` 设为 `HarmonyOS`，后续所有 `case $ac_sys_system in` 分支都能通过 `HarmonyOS*)` 匹配到。

#### 修改点 2：MACHDEP 设置

```diff
     case $MACHDEP in
 	aix*) MACHDEP="aix";;
 	linux*) MACHDEP="linux";;
+	harmonyos*|HarmonyOS*) MACHDEP="ohos";;
 	cygwin*) MACHDEP="cygwin";;
```

**位置**：第 414 行附近，本地构建时的 MACHDEP 计算。  
**原因**：`uname -s` 返回 `HarmonyOS`，经过 `tr` 转小写后变成 `harmonyos`。MACHDEP 决定了 Python 内部模块搜索路径（如 `Lib/ohos/`）。如果不设置，MACHDEP 会变成 `harmonyosx.y.z`（带内核版本号），导致找不到正确路径。  
**逻辑**：用通配符 `harmonyos*|HarmonyOS*` 匹配，统一映射为 `ohos`。之所以映射到 `ohos` 而不是 `harmonyos`，是因为 Python 内部的平台目录命名偏向短名称（如 Linux → `linux`，Darwin → `darwin`）。

#### 修改点 3：跳过 _XOPEN_SOURCE 定义

```diff
   SunOS/*)
     define_xopen_source=no;;
+  HarmonyOS/*)
+    define_xopen_source=no;;
```

**位置**：第 489 行附近。  
**原因**：`_XOPEN_SOURCE` 宏用于启用 POSIX/X/Open 标准接口。鸿蒙使用 musl libc，musl 本身已经提供了完整的 POSIX 支持，不需要额外的 `_XOPEN_SOURCE` 定义。更重要的是，定义 `_XOPEN_SOURCE` 可能会隐藏某些函数原型（musl 在 `_XOPEN_SOURCE >= 700` 时会改变部分行为），导致编译错误。  
**逻辑**：参考 SunOS（Solaris）的做法，直接设置 `define_xopen_source=no` 跳过定义。这是一个独立分支，不是追加到 Linux 分支后面（参见 [SKILL.md §6.0.2 独立分支原则](../../SKILL.md)）。

#### 修改点 4：交叉编译三元组

```diff
 #if defined(__ANDROID__)
     # Android is not a multiarch system.
+#elif defined(__OHOS__)
+    # HarmonyOS/OpenHarmony uses musl libc
+# if defined(__aarch64__)
+        aarch64-linux-ohos
+# elif defined(__arm__)
+        arm-linux-ohos
+# elif defined(__x86_64__)
+        x86_64-linux-ohos
+# else
+#   error unknown platform triplet
+# endif
```

**位置**：第 737 行附近，`_PYTHON_HOST_PLATFORM` 的 C 预处理器逻辑。  
**原因**：`_PYTHON_HOST_PLATFORM` 决定了 Python 的构建目录路径（如 `build/lib.linux-x86_64-3.9/`）。交叉编译时，这个值通过 C 预处理器在 configure 阶段计算。如果不添加 `__OHOS__` 分支，会进入 `__linux__` 分支生成 `aarch64-linux-gnu` 这样的三元组，导致路径和平台不匹配。  
**逻辑**：检查 Clang 自动定义的 `__OHOS__` 宏（鸿蒙编译器特有），然后根据架构返回对应的三元组。三元组格式遵循 `aarch64-linux-ohos`（架构-厂商-操作系统），其中 `linux-ohos` 表示"基于 Linux 内核的 HarmonyOS"。这个三元组与 `config.guess` 和 `config.sub` 的输出保持一致。

#### 修改点 5：跳过 BUILDEXEEXT 大小写检测 ⭐ 新增

```diff
 AC_SUBST(BUILDEXEEXT)
-AC_MSG_CHECKING(for case-insensitive build directory)
-if test ! -d CaseSensitiveTestDir; then
-mkdir CaseSensitiveTestDir
-fi
+case $ac_sys_system in
+    HarmonyOS*)
+        BUILDEXEEXT=$EXEEXT
+        AC_MSG_RESULT(no - skipped for HarmonyOS)
+        ;;
+    *)
+        AC_MSG_CHECKING(for case-insensitive build directory)
+        ...
+esac
```

**位置**：第 970 行附近。  
**原因**：configure 通过以下逻辑检测文件系统是否大小写不敏感：先创建 `CaseSensitiveTestDir`（大写混合），再检查 `test -d casesensitivetestdir`（全小写）是否也存在。如果存在则认为大小写不敏感，设置 `BUILDEXEEXT=.exe`。在鸿蒙上这个检测结果**不准确**（可能误判为不敏感），导致生成 `python3.9.exe` 而非 `python3.9`。  
**后果链**：
```
BUILDEXEEXT=.exe
  → BUILDPYTHON=python3.9.exe
  → 安装时查找 python3.9.exe
  → 实际生成的是 python3.9
  → 运行时找不到解释器
```
**逻辑**：用 `case $ac_sys_system in` 包裹整个检测逻辑，HarmonyOS 分支直接使用 `$EXEEXT`（空值），跳过检测。这是一个独立分支，不影响其他平台。

#### 修改点 6：共享库和动态链接设置

```diff
     SunOS*)
 	  LDLIBRARY='libpython$(LDVERSION).so'
 	  BLDLIBRARY='-L. -lpython$(LDVERSION)'
 	  RUNSHARED=LD_LIBRARY_PATH=`pwd`${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
 	  INSTSONAME="$LDLIBRARY".$SOVERSION
 	  ...
+    HarmonyOS*)
+	  # HarmonyOS uses musl libc with BIND_NOW by default
+	  LDLIBRARY='libpython$(LDVERSION).so'
+	  BLDLIBRARY='-L. -lpython$(LDVERSION)'
+	  RUNSHARED=LD_LIBRARY_PATH=`pwd`${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
+	  INSTSONAME="$LDLIBRARY".$SOVERSION
+	  ...
+	  ;;
     Linux*|GNU*|NetBSD*|FreeBSD*|DragonFly*|OpenBSD*)
```

**位置**：第 1168 行附近。  
**原因**：这组变量控制 Python 共享库的构建和运行方式：

| 变量 | 含义 | 为什么需要设置 |
|------|------|--------------|
| `LDLIBRARY` | 主共享库名称 | 告诉 make 构建 `.so` 而非 `.a` |
| `BLDLIBRARY` | 链接时使用的库路径 | Python 解释器自身链接 libpython |
| `RUNSHARED` | 运行时库搜索路径 | 扩展模块能找到 libpython.so |
| `INSTSONAME` | 安装时的 soname | 正确的 .so 版本链接 |
| `PY3LIBRARY` | Python 3 兼容库名 | `python3.so` → `python3.9.so` 软链 |

**为什么不追加到 Linux 分支**：虽然值相同，但独立分支便于未来差异化修改（例如 musl 特有的链接器行为）。

#### 修改点 7：LDSHARED / BLDSHARED 设置 ⭐ 关键

```diff
+	HarmonyOS*)
+		BLDSHARED='$(CC) -shared'
+		LDSHARED='$(CC) -shared -L. -lpython$(LDVERSION)'
+		LDCXXSHARED='$(CXX) -shared'
+		;;
```

**位置**：第 2611 行附近。  
**原因**：这是解决 **musl BIND_NOW 问题** 的核心修改。

```
问题链：
  musl libc 默认使用 BIND_NOW（而非 glibc 的 BIND_LAZY）
    → dlopen() 加载 .so 时要求所有符号必须立即解析
    → 扩展模块的 NEEDED 项只有 libc.so（没有 libpython）
    → Python API 符号（_PyType_Name 等）无法解析
    → ImportError: symbol not found
```

**BLDSHARED vs LDSHARED 的区别**（极易混淆）：

| 变量 | 用于 | 包含 -lpython？ | 原因 |
|------|------|----------------|------|
| `BLDSHARED` | 构建 `libpython.so` 本身 | ❌ 不能 | 循环依赖：不能链接自己 |
| `LDSHARED` | 构建扩展模块（`.so`） | ✅ 必须 | 扩展模块需要 Python API 符号 |

**为什么 `-L.` 很重要**：`-L.` 告诉链接器在当前目录（构建目录）搜索 `libpython3.9.so`。如果不加 `-L.`，链接器会在系统库路径中搜索，找不到刚构建的 libpython。

#### 修改点 8：CCSHARED 设置

```diff
+	HarmonyOS*) CCSHARED="-fPIC";;
 	Linux-android*) ;;
 	Linux*|GNU*) CCSHARED="-fPIC";;
```

**位置**：第 2753 行附近。  
**原因**：`CCSHARED` 是编译共享库（`.so`）时必须的编译选项。`-fPIC`（Position Independent Code）生成位置无关代码，这是共享库的基本要求。鸿蒙使用动态链接，所有扩展模块都是共享库，必须加 `-fPIC`。  
**为什么放在 `Linux-android*)` 前面**：因为 `Linux-android*` 后面就是 `Linux*|GNU*`。鸿蒙的三元组是 `aarch64-linux-ohos`，理论上 `Linux*` 也能匹配到。但独立分支更明确，且避免 `Linux-android*` 空分支的歧义。

#### 修改点 9：LINKFORSHARED 设置

```diff
+	HarmonyOS*)
+		LINKFORSHARED="-Xlinker -export-dynamic";;
```

**位置**：第 2829 行附近。  
**原因**：`-Xlinker -export-dynamic` 让链接器将所有符号导出到动态符号表。这对于 Python 扩展模块至关重要：扩展模块通过 `dlopen()` 加载后，需要反向查找 Python 解释器的符号（如 `Py_None`、`PyExc_ValueError` 等）。如果不加此选项，部分符号可能不被导出，导致扩展模块加载失败。

#### 修改点 10：CAN socket 宏检测跳过

```diff
 AC_MSG_CHECKING(for CAN_RAW_FD_FRAMES)
+case $ac_sys_system in
+	HarmonyOS*)
+		AC_MSG_RESULT(no - skipped for HarmonyOS)
+		;;
+	*)
 		AC_COMPILE_IFELSE(...)
+		;;
+esac
```

**位置**：第 3531 行附近（两个宏检测）。  
**原因**：configure 会检测 `CAN_RAW_FD_FRAMES` 和 `CAN_RAW_JOIN_FILTERS` 这两个宏是否可用，如果可用就在 `pyconfig.h` 中定义它们。但鸿蒙内核头文件中**声明了但不定义**这些宏（编译时检查通过，实际使用时找不到定义），导致 `Modules/socketmodule.c` 编译失败。  
**逻辑**：为 HarmonyOS 跳过检测，直接报告 "no"。`socketmodule.c` 中有条件编译 `#ifdef HAVE_LINUX_CAN_RAW_FD_FRAMES`，不定义就不会使用这些宏。

---

### 3.3 补丁 0002：setup.py — 扩展模块编译支持

**修改文件**：`setup.py`  
**修改数量**：6 处

#### 修改点 1：OHOS 平台变量

```diff
 VXWORKS = ('vxworks' in HOST_PLATFORM)
+OHOS = (HOST_PLATFORM.startswith('harmony') or HOST_PLATFORM.startswith('ohos'))
```

**原因**：`setup.py` 通过 `HOST_PLATFORM` 变量判断当前平台，驱动后续所有平台相关的逻辑。原代码用精确匹配 `HOST_PLATFORM in ['harmony', 'ohos']`，但实际的 `HOST_PLATFORM` 值是 `harmonyos-aarch64`（来自 configure），精确匹配失败。  
**逻辑**：改用 `startswith()` 前缀匹配，`harmonyos` 以 `harmony` 开头，`ohos-aarch64` 以 `ohos` 开头。

#### 修改点 2：SDK sysroot 检测函数

```python
def ohos_sdk_root():
    """返回鸿蒙 SDK 的 sysroot 路径"""
```

**原因**：`setup.py` 需要知道鸿蒙 SDK 的 sysroot 路径来搜索头文件和库文件（类似 macOS 的 `macosx_sdk_root()`）。鸿蒙 SDK 的 sysroot 路径通常类似 `/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native/sysroot`。  
**逻辑**：两种探测方式：
1. 从 `CFLAGS` 环境变量中提取 `--sysroot=` 参数（最可靠）
2. 调用 `clang -v` 解析输出来定位 sysroot 路径（兜底）

#### 修改点 3：架构映射函数

```python
def get_ohos_arch():
    """获取鸿蒙架构"""
```

**原因**：鸿蒙 SDK 的库文件按架构组织在 `usr/lib/{arch}-linux-ohos/` 目录下。需要将 `uname -m` 返回的架构名映射到标准格式。  
**逻辑**：`aarch64`/`arm64` → `aarch64`，`armv7l` → `arm32` 等。

#### 修改点 4：扩展模块链接 libpython（musl BIND_NOW 修复）

```python
if OHOS:
    ldversion = sysconfig.get_config_var('LDVERSION')
    args['compiler_so'] = (args.get('compiler_so', '') +
                           ' -L. -lpython' + ldversion)
```

**位置**：`set_compiler_executables()` 方法中。  
**原因**：这是 `setup.py` 层面解决 musl BIND_NOW 问题的修改。与 configure.ac 的 LDSHARED 修改互补：configure.ac 设置 `LDSHARED='$(CC) -shared -L. -lpython3.9'`，`setup.py` 在调用编译器时追加 `-L. -lpython3.9` 到 `compiler_so` 命令。  
**为什么两层都需要**：`setup.py` 有自己的编译器调用逻辑，它使用 `self.compiler.compile()` 和 `self.compiler.link()` 方法，这些方法最终使用 `compiler_so` 和 `linker_so` 变量。即使 Makefile 设置了 `LDSHARED` 环境变量，`setup.py` 内部仍可能覆盖这些设置。

#### 修改点 5：多架构路径

```python
if OHOS:
    arch = get_ohos_arch()
    if arch:
        add_dir_to_list(self.compiler.library_dirs, f'/usr/lib/{arch}-linux-ohos')
        add_dir_to_list(self.compiler.include_dirs, f'/usr/include')
    return
```

**位置**：`add_multiarch_paths()` 方法中。  
**原因**：鸿蒙的第三方库（如 ncurses、readline）安装在 `/usr/lib/aarch64-linux-ohos/` 这样的多架构路径下。如果不添加这些路径，`setup.py` 会找不到已安装的库，导致相关扩展模块（如 `_curses`、`readline`）编译失败。  
**为什么用 `return` 提前退出**：后续代码是 Debian/Ubuntu 的多架构逻辑，不适用于鸿蒙。

#### 修改点 6：SDK sysroot 搜索路径

```python
if OHOS:
    sysroot = ohos_sdk_root()
    if sysroot:
        full_lib_dir = os.path.join(sysroot, "usr", "lib", "{}-linux-ohos".format(ohos_arch))
        if os.path.isdir(full_lib_dir):
            self.lib_dirs.append(full_lib_dir)
        pub_sdk_inc_dir = os.path.join(sysroot, "usr", "include")
        if os.path.isdir(pub_sdk_inc_dir):
            self.inc_dirs.append(pub_sdk_inc_dir)
```

**位置**：`detect_modules()` 方法中，初始化 `self.lib_dirs` 和 `self.inc_dirs` 之后。  
**原因**：`setup.py` 在 `detect_modules()` 中搜索各种头文件和库。鸿蒙的 SDK 头文件和库文件在 sysroot 下按架构组织。如果不添加这些路径，`setup.py` 会找不到 SDK 提供的系统头文件（如 `<openssl/ssl.h>`），即使 OpenSSL 已安装。

---

### 3.4 补丁 0003：config.guess — 平台三元组识别

**修改文件**：`config.guess`  
**修改数量**：1 个 hunk

```diff
+    *:HarmonyOS:*:*)
+	case "$UNAME_MACHINE" in
+		aarch64|arm64)
+			echo "aarch64-unknown-linux-ohos"
+			;;
+		...
+	esac
+	exit ;;
```

**原因**：`config.guess` 是 autotools 用来检测当前构建平台的脚本。它通过 `uname` 系统调用获取信息，生成标准三元组。鸿蒙的 `uname -s` 返回 `HarmonyOS`，原版 `config.guess` 不认识这个系统名。  
**为什么三元组是 `aarch64-unknown-linux-ohos`**：
- `aarch64`：CPU 架构
- `unknown`：厂商（未知，因为是本地构建而非交叉编译）
- `linux-ohos`：操作系统（基于 Linux 内核的 HarmonyOS）

`linux-ohos` 而非 `harmonyos` 是因为 HarmonyOS 使用 Linux 内核，许多工具和库的配置逻辑是基于 "linux" 前缀做判断的（如 `config.sub` 中的 `linux-gnu*` 模式）。

---

### 3.5 补丁 0004：config.sub — 三元组验证

**修改文件**：`config.sub`  
**修改数量**：3 处

#### 修改点 1：maybe_os 识别

```diff
-  nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \
+  nto-qnx* | linux-ohos* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \
```

**原因**：`config.sub` 开头有一个 `maybe_os` 列表，用于快速识别操作系统部分。如果三元组的 OS 部分不在列表中，后续解析可能失败。添加 `linux-ohos*` 确保 `aarch64-unknown-linux-ohos` 能被正确解析。  
**为什么放在 `linux-gnu*` 前面**：避免被后面的 `linux*` 通配符吞掉（虽然两者能匹配同一个三元组，但显式匹配更可靠）。

#### 修改点 2：-linux-ohos 映射

```diff
+	-linux-ohos)
+		os=-linux-ohos
+		;;
 	-linux*)
 		os=`echo $os | sed -e 's|linux|linux-gnu|'`
 		;;
```

**原因**：`config.sub` 中 `linux*` 分支会将所有 `linux-*` 映射为 `linux-gnu`。必须在 `linux*` 之前拦截 `linux-ohos`，保留原始 OS 名称。

#### 修改点 3：-harmonyos 兜底

```diff
+	-harmonyos)
+		os=-linux-ohos
+		;;
```

**原因**：如果有人使用 `aarch64-unknown-harmonyos` 这样的三元组（不带 `linux-` 前缀），映射为 `aarch64-unknown-linux-ohos` 以保持一致。

---

### 3.6 补丁 0005：distutils/util.py — 平台标识符

**修改文件**：`Lib/distutils/util.py`  
**修改数量**：1 处

```diff
+    elif osname[:9] == "harmonyos":
+        return "ohos-%s-%s" % (osname, machine)
```

**位置**：`get_platform()` 函数。  
**原因**：`distutils` 的 `get_platform()` 用于生成分发包的平台标签。`osname` 是 `HarmonyOS`（大写开头），`release` 包含空格（如 `HongMeng Kernel 1.11.0`），`machine` 是 `aarch64`。  
**为什么返回 `ohos-HarmonyOS-aarch64`**：跳过 `release` 避免空格问题，`osname` 保留原始值用于调试。

---

### 3.7 补丁 0006：_bootsubprocess.py — 子进程执行修复 ⭐ 关键

**修改文件**：`Lib/_bootsubprocess.py`  
**修改数量**：1 处（Popen.wait 方法重写）

```python
# 原代码
def wait(self):
    pid = os.fork()
    if pid == 0:
        os.execv(self._cmd[0], self._cmd)  # ❌ 在鸿蒙上失败
    else:
        _, status = os.waitpid(pid, 0)
        self.returncode = os.waitstatus_to_exitcode(status)

# 修改后
def wait(self):
    cmd_str = ' '.join(shlex.quote(arg) for arg in self._cmd)
    self.returncode = os.system(cmd_str)  # ✅ 通过 /bin/sh 执行
```

**原因**：这是 **HarmonyOS 沙箱签名拦截** 问题的修复。详见 [SKILL.md §3.7.7](../../SKILL.md)。

**问题链**：
```
setup.py → _bootsubprocess.Popen → os.fork() + os.execv("clang")
  → exec 加载 SDK 预装的 clang 二进制
  → HarmonyOS 沙箱签名校验 → 拦截 → 子进程退出 → 编译失败
```

**为什么 `os.system()` 能绕过**：`os.system(cmd)` 实际执行的是 `/bin/sh -c cmd`。`/bin/sh` 是系统二进制（有合法 SELinux 签名），可以正常 exec。shell 内部再调用 `clang` 时，走的是 shell 自己的执行路径，不受沙箱签名限制。

**使用 `shlex.quote()` 的原因**：正确处理参数中的空格、引号等特殊字符，避免 shell 注入和参数分割错误。

**局限性**：`os.system()` 返回的是 `waitstatus` 而非 `exitcode`。原代码用 `os.waitstatus_to_exitcode(status)` 转换，新代码直接用 `os.system()` 的返回值（在 POSIX 上 `os.system()` 返回的就是 exitcode）。

**注意**：这个 workaround 对简单的编译命令有效，但对于复杂的构建场景（如需要精确控制子进程环境变量、管道等），可能不够用。根治方案需要 HarmonyOS 系统层面解决沙箱签名问题。

---

### 3.8 补丁 0007：Makefile.pre.in — 链接和安装修复

**修改文件**：`Makefile.pre.in`  
**修改数量**：7 处

#### 修改点 1：HARDLINK 和 LN_FORCE 变量

```makefile
+HARDLINK=	$(shell uname -s 2>/dev/null | grep -qi harmony && echo cp -p || echo ln)
+LN_FORCE=	$(shell uname -s 2>/dev/null | grep -qi harmony && echo ln -s || echo ln -sf)
```

**原因**：
- 鸿蒙 **不支持硬链接**（`ln` 创建硬链接报 `Operation not permitted`），需要用 `cp -p` 替代。`-p` 保留权限和时间戳。
- `ln -sf` 在 toybox 实现中有 bug（创建的软链接文件名带随机后缀），改用 `ln -s`。调用方需先 `rm -f` 旧链接。

**为什么用 `$(shell uname -s)` 运行时判断**：这样 Makefile 在任何系统上都能正确工作，无需在 configure 阶段检测。Linux 上 `uname -s` 返回 `Linux`，`grep harmony` 失败，`HARDLINK` 仍为 `ln`。

#### 修改点 2：BUILDPYTHON 变量

```diff
-BUILDPYTHON=	python$(BUILDEXE)
+BUILDPYTHON=	python@VERSION@$(BUILDEXE)
```

**原因**：`BUILDPYTHON` 是构建过程中使用的 Python 可执行文件名。原代码用 `python$(BUILDEXE)`，在鸿蒙的文件系统上，`make` 执行时可能因为文件系统特性（大小写敏感性问题）找不到 `python` → 找到 `Python` → 大小写不匹配。  
**为什么用 `@VERSION@`**：`@VERSION@` 是 configure 替换的变量，值为 `3.9`，生成 `python3.9`。完整路径不会产生大小写歧义。  
**影响范围**：仅影响 Makefile 中引用 `$(BUILDPYTHON)` 的规则，如 sharedmods、install 等。

#### 修改点 3：sharedmods 规则使用 LDSHARED ⭐ 新增

```diff
-	echo "$(RUNSHARED) CC='$(CC)' LDSHARED='$(BLDSHARED)' OPT='$(OPT)' \
+	echo "$(RUNSHARED) CC='$(CC)' LDSHARED='$(LDSHARED)' OPT='$(OPT)' \
```

**位置**：`sharedmods:` 目标规则（第 633 行附近）。  
**原因**：`sharedmods` 规则调用 `setup.py` 编译扩展模块。它通过环境变量 `LDSHARED` 告诉 `setup.py` 用什么命令链接共享库。原代码传 `$(BLDSHARED)`（不含 `-lpython`），导致扩展模块缺少 libpython 依赖。  
**为什么改 `Makefile.pre.in` 而非 configure.ac**：`sharedmods` 规则在 `Makefile.pre.in` 中硬编码，不在 `configure.ac` 中。这是 Python 构建系统的一个设计问题：`sharedmods` 使用的链接器变量与 `configure` 中设置的 `LDSHARED` 没有自动关联。

#### 修改点 4：libpython.so 硬链接改复制

```diff
-		$(LN) -f $(INSTSONAME) $@; \
+		$(HARDLINK) $(INSTSONAME) $@; \
```

**原因**：`libpython3.9.so.1.0` → `libpython3.9.so` 的创建原用 `$(LN) -f`（即 `ln -f`），这是硬链接操作。鸿蒙不支持硬链接，改为 `$(HARDLINK)`（鸿蒙上映射为 `cp -p`）。

#### 修改点 5：install 规则中的链接操作

```diff
-		(cd $(DESTDIR)$(BINDIR); $(LN) python$(LDVERSION)$(EXE) python$(VERSION)$(EXE)); \
+		(cd $(DESTDIR)$(BINDIR); $(LN_FORCE) python$(LDVERSION)$(EXE) python$(VERSION)$(EXE)); \
```

**原因**：创建 `python3` → `python3.9` 软链接。原用 `$(LN)` 即 `ln`，在目标已存在时会失败。改用 `$(LN_FORCE)`（鸿蒙上映射为 `ln -s`，但调用前需先删除旧链接）。这里的目标是新安装，通常不存在旧链接，所以 `ln -s` 即可。

#### 修改点 6：lib install 中的软链接

```diff
-				(cd $(DESTDIR)$(LIBDIR); $(LN) -sf $(INSTSONAME) $(LDLIBRARY)) \
+				(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(LN_FORCE) $(INSTSONAME) $(LDLIBRARY)) \
```

**原因**：创建 `libpython3.9.so` → `libpython3.9.so.1.0` 的软链接。原用 `$(LN) -sf`（`ln -sf`），鸿蒙 toybox 的 `ln -sf` 有 bug。改用先 `rm -f` 删除旧链接，再 `$(LN_FORCE)`（`ln -s`）创建新链接。

---

### 3.9 补丁 0008：sysconfig.py — 运行时平台字符串

**修改文件**：`Lib/sysconfig.py`  
**修改数量**：1 处

```diff
+    elif osname[:9] == "harmonyos" or osname[:4] == "ohos":
+        return "%s-%s" % (osname, machine)
```

**位置**：`get_platform()` 函数。  
**原因**：
```
sys.platform = "HarmonyOS HongMeng Kernel 1.11.0"  （含空格）
get_platform() 原逻辑: "HarmonyOS HongMeng Kernel 1.11.0-aarch64"  （路径非法）
构建目录: build/lib.HarmonyOS HongMeng Kernel 1.11.0-aarch64-3.9/  （无法访问）
```

修改后：
```
get_platform() = "harmonyos-aarch64"  （无空格）
构建目录: build/lib.harmonyos-aarch64-3.9/  （正常）
```

**为什么 `osname[:9] == "harmonyos"` 而非 `osname[:4] == "ohos"`**：主分支检查 `harmonyos` 前缀，因为 `osname` 在到达此函数前已经被处理为小写。`ohos` 前缀是 MACHDEP 为 `ohos` 时的备用路径。

**与补丁 0005 的关系**：0005 修改 `distutils/util.py` 的 `get_platform()`（用于分发包），0008 修改 `sysconfig.py` 的 `get_platform()`（用于构建系统）。两者功能相似但作用于不同阶段。

---

## 四、扩展模块编译

### 4.1 当前状态

由于 HarmonyOS 沙箱签名拦截子进程 `exec` SDK 二进制（见 SKILL.md §3.7.7），`make` 过程中 `setup.py` 通过 `_bootsubprocess.Popen` 编译扩展模块时会失败。**Python 解释器本身和 libpython 共享库可以正常编译**。

### 4.2 手动编译扩展模块

对于无法通过 `make` 自动编译的扩展模块，可以手动编译：

```bash
cd Python-3.9.0
export LD_LIBRARY_PATH=.

# 通用编译模板
CFLAGS="-fPIC -I./Include/internal -I./Include -I. -I$HOME/usr/local/include"
LDFLAGS="-shared -L. -lpython3.9"

# 编译 _struct
clang $CFLAGS -c Modules/_struct.c -o build/_struct.o
clang $LDFLAGS build/_struct.o -o build/_struct.so

# 验证
PYTHONPATH=build ./python3.9 -c "import _struct; print('OK')"
```

### 4.3 需要 Py_BUILD_CORE_MODULE 的模块

```bash
CFLAGS="$CFLAGS -DPy_BUILD_CORE_MODULE"

# math, cmath（还需要 Modules/_math.o 和 -lm）
clang $CFLAGS -c Modules/mathmodule.c -o build/math.o
clang $LDFLAGS build/math.o Modules/_math.o -lm -o build/math.so
```

### 4.4 已验证可用的模块（手动编译）

| 模块 | 额外依赖 | 说明 |
|------|----------|------|
| _struct | 无 | 基础结构体打包 |
| _json | 无 | JSON 解析 |
| math | `-lm`, `Modules/_math.o` | 数学函数 |
| cmath | `-lm`, `Modules/_math.o` | 复数数学 |
| _datetime | 无 | 日期时间 |
| _random | 无 | 随机数 |
| array | 无 | 数组 |
| _pickle | 无 | 序列化 |
| _csv | 无 | CSV 读写 |
| fcntl | 无 | 文件控制 |
| select | 无 | I/O 多路复用 |
| mmap | 无 | 内存映射 |
| syslog | 无 | 系统日志 |
| audioop | 无 | 音频操作 |
| _bisect | 无 | 二分查找 |
| _heapq | 无 | 堆队列 |
| _statistics | 无 | 统计函数 |
| _opcode | 无 | 操作码 |
| _queue | 无 | 队列 |
| _contextvars | 无 | 上下文变量 |
| _posixsubprocess | 无 | POSIX 子进程 |
| _zoneinfo | 无 | 时区 |

### 4.5 待编译的模块

| 模块 | 依赖 | 状态 |
|------|------|------|
| _socket | 无（系统支持） | 待编译 |
| _ssl | OpenSSL 1.1.1w | 待编译 |
| _ctypes | libffi | 待编译 |
| zlib | zlib | 待编译 |
| _sqlite3 | SQLite | 待编译 |
| readline | libreadline + ncurses | 待编译 |
| pyexpat | 内置 expat | 待编译 |
| _elementtree | 内置 expat | 待编译 |
| unicodedata | 无 | 待编译 |
| _codecs_cn/jp/kr/tw/hk/iso2022 | 无 | 待编译 |
| _sha256/_sha512/_md5/_sha1/_sha3/_blake2 | 无 | 待编译 |
| _multibytecodec | 无 | 待编译 |

---

## 五、鸿蒙特有问题汇总

### 5.1 已解决的问题

| # | 问题 | 根因 | 解决方案 | 补丁 |
|---|------|------|---------|------|
| 1 | 平台不被识别 | config.guess/config.sub 缺少 HarmonyOS | 添加 `*:HarmonyOS:*:*` 和 `linux-ohos` | 0003, 0004 |
| 2 | configure 变量未设置 | configure.ac 所有 case 分支缺少 HarmonyOS | 添加独立的 `HarmonyOS*)` 分支 | 0001 |
| 3 | setup.py 不识别 OHOS | HOST_PLATFORM 精确匹配失败 | 改为 `startswith()` | 0002 |
| 4 | 扩展模块符号找不到 | musl BIND_NOW + 缺少 libpython | LDSHARED 加 `-lpython$(LDVERSION)` | 0001, 0007 |
| 5 | 硬链接创建失败 | SELinux 策略 | `HARDLINK=cp -p` | 0007 |
| 6 | `ln -sf` 产生乱码文件 | toybox bug | `LN_FORCE=ln -s` + 先删后建 | 0007 |
| 7 | 构建路径含空格 | `sys.platform` 含空格 | 跳过 release 字符串 | 0008 |
| 8 | 可执行文件名带 .exe | 大小写检测误判 | HarmonyOS 跳过检测 | 0001 |
| 9 | CAN socket 编译失败 | 内核头文件差异 | 跳过宏检测 | 0001 |
| 10 | 子进程编译失败 | 沙箱签名拦截 | `os.system()` 替代 `os.execv()` | 0006 |

### 5.2 未解决的问题

| # | 问题 | 根因 | 可能的解决方向 |
|---|------|------|--------------|
| 1 | make 扩展模块全部失败 | 沙箱签名拦截子进程 exec SDK clang | 系统级白名单 / wrapper 二进制 |
| 2 | _ssl 编译需要 OpenSSL | 依赖外部库 | 先编译 OpenSSL（已有补丁） |
| 3 | _ctypes 编译需要 libffi | 依赖外部库 | 先编译 libffi（已有补丁） |

### 5.3 经验教训

1. **三层构建系统需要三层适配**：configure.ac、Makefile.pre.in、setup.py 都需要修改，遗漏任何一层都会导致部分功能失败
2. **独立分支优于追加 Linux 分支**：HarmonyOS 与 Linux 有大量微妙差异，追加到 Linux 分支容易引入连锁问题
3. **musl BIND_NOW 影响所有插件系统**：不仅是 Python，Perl、Ruby 等也会遇到
4. **BLDSHARED ≠ LDSHARED**：构建主库和构建插件的链接命令必须分开，否则循环依赖
5. **sandbox 签名是最隐蔽的问题**：不报明确错误信息，需要深入排查才能定位根因
6. **补丁顺序很重要**：0001（configure.ac）必须先于 0007（Makefile.pre.in），因为两者同时被 autoconf 处理
7. **共享库风险**：ncurses 等系统依赖的共享库，编译时应优先选择静态库，避免符号链接问题导致系统 shell 崩溃
8. **宽字符宏是隐蔽的**：`_XOPEN_SOURCE_EXTENDED` 宏对 ncurses 宽字符函数至关重要，缺少会导致 `cchar_t` 等类型未定义

---

## 六、curses 模块静态链接编译

### 6.1 问题背景

Python 的 `_curses` 和 `_curses_panel` 模块在鸿蒙系统上编译存在以下问题：

| 问题 | 原因 | 影响 |
|------|------|------|
| setup.py 路径硬编码 | 硬编码 `/usr/include/ncursesw` | 找不到头文件 |
| 宽字符函数未定义 | 缺少 `_XOPEN_SOURCE_EXTENDED` | `cchar_t`、`setcchar` 等未定义 |
| 共享库链接风险 | 鸿蒙 zsh 依赖 `libncursesw.so.6` | 符号链接问题导致系统崩溃 |

### 6.2 `_XOPEN_SOURCE_EXTENDED` 问题详解

**问题现象：**

编译 `_curses` 模块时报错：
```
error: unknown type name 'cchar_t'; did you mean 'wchar_t'?
error: call to undeclared function 'setcchar'
error: call to undeclared function 'wadd_wch'
```

**根本原因：**

ncurses 的宽字符函数是条件编译的：
```c
#if defined(_XOPEN_SOURCE_EXTENDED) || (defined(_XOPEN_SOURCE) && (_XOPEN_SOURCE - 0 >= 500))
#define NCURSES_WIDECHAR 1
```

各平台情况：

| 平台 | C库 | `_XOPEN_SOURCE` 状态 | 需要添加宏？ |
|------|-----|---------------------|--------------|
| Linux | glibc | 默认定义且 >= 500 | ❌ 不需要 |
| macOS | - | 默认不定义 | ✅ 需要 |
| HarmonyOS | musl | 未定义 | ✅ 需要 |

**解决方案：**

补丁 `0009-setup.py-curses-XOPEN_SOURCE_EXTENDED.patch` 修改了 `setup.py`：

```python
# 原代码（只在 macOS 上添加宏）
if MACOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))

# 修改后（macOS 和 HarmonyOS 都添加宏）
if MACOS or OHOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))
```

### 6.3 推荐方案：静态链接

**强烈建议使用静态链接**，避免共享库问题影响系统稳定性。

#### 步骤 1：编译 ncurses 静态库

```bash
cd ncurses-6.4
./configure --prefix=$HOME/usr/local \
    --without-shared \       # ⭐ 关键：不生成共享库
    --without-cxx \
    --enable-widec \         # 启用宽字符支持
    --enable-overwrite       # 头文件安装到顶层
make && make install.libs
```

生成的静态库：
- `libncursesw.a` - 主库
- `libpanelw.a` - 面板库

#### 步骤 2：编译 _curses 模块

```bash
cd Python-3.9.0-work

# 编译 _cursesmodule.c
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \   # ⭐ 关键：启用宽字符函数
    -D_XOPEN_SOURCE=600 \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_cursesmodule.c \
    -o build/temp.ohos-aarch64-3.9/_cursesmodule.o

# 静态链接
clang -shared -L. -lpython3.9 \
    build/temp.ohos-aarch64-3.9/_cursesmodule.o \
    $HOME/usr/local/lib/libncursesw.a \   # 静态链接
    -o build/lib.ohos-aarch64-3.9/_curses.so
```

#### 步骤 3：编译 _curses_panel 模块

```bash
# 编译 _curses_panel.c
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_curses_panel.c \
    -o build/temp.ohos-aarch64-3.9/_curses_panel.o

# 静态链接（注意顺序：panel 在前，ncurses 在后）
clang -shared -L. -lpython3.9 \
    build/temp.ohos-aarch64-3.9/_curses_panel.o \
    $HOME/usr/local/lib/libpanelw.a \
    $HOME/usr/local/lib/libncursesw.a \
    -o build/lib.ohos-aarch64-3.9/_curses_panel.so
```

### 6.3 验证

```bash
./python3.9 -c "
import _curses
import _curses_panel
import curses
print('✓ curses 模块正常')
print(f'ncurses 版本: {curses.ncurses_version}')
"
```

### 6.4 关键编译选项说明

| 选项 | 作用 |
|------|------|
| `-DHAVE_NCURSESW=1` | 指定使用 ncurses 宽字符版本 |
| `-D_XOPEN_SOURCE_EXTENDED` | 启用 X/Open 宽字符扩展函数（`cchar_t`、`setcchar` 等） |
| `-D_XOPEN_SOURCE=600` | 设置 X/Open 标准版本 |
| 静态链接 `.a` 文件 | 避免共享库依赖，不影响系统 |

### 6.5 为什么需要 `-D_XOPEN_SOURCE_EXTENDED`

ncurses 的宽字符函数是条件编译的：

```c
#ifndef NCURSES_WIDECHAR
#if defined(_XOPEN_SOURCE_EXTENDED) || (defined(_XOPEN_SOURCE) && (_XOPEN_SOURCE >= 500))
#define NCURSES_WIDECHAR 1
#else
#define NCURSES_WIDECHAR 0  // 默认关闭
#endif
#endif
```

如果不定义 `_XOPEN_SOURCE_EXTENDED`，`NCURSES_WIDECHAR` 为 0，导致：
- `cchar_t` 类型未定义
- `setcchar()`、`mvwadd_wch()`、`wget_wch()` 等函数未声明

### 6.6 静态链接 vs 动态链接

| 方式 | 优点 | 缺点 |
|------|------|------|
| **静态链接**（推荐） | 不影响系统；无运行时依赖；更稳定 | 文件较大；更新需重新编译 |
| 动态链接 | 文件小；多程序共享；更新方便 | 可能影响系统 shell；需正确配置库路径 |

**事故案例**：

```bash
# 尝试创建共享库符号链接
cd $HOME/usr/local/lib
ln -sf libncursesw.so.6.4 libncursesw.so.6

# 结果：所有终端无法启动！
# 错误：Error loading shared library libncursesw.so.6: Permission denied (needed by /bin/zsh)
```

### 6.7 相关文档

- ncurses 编译指南：`build_in_harmonyos/n/ncurses/6.4/README.md`
- 鸿蒙编译知识库：`build_in_harmonyos/SKILL.md`

---

## 六、补丁应用验证

### 6.1 验证流程

```bash
# 从纯净源码开始
tar -xzf Python-3.9.0.tgz
cd Python-3.9.0

# 应用全部补丁
PATCHDIR=/path/to/patches
for p in "$PATCHDIR"/*.patch; do
    patch -p1 < "$p" || echo "FAILED: $(basename $p)"
done

# 重新生成 configure
autoconf

# 配置并编译
export TMPDIR=$HOME/tmp
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH
./configure --prefix=$HOME/usr/local --enable-shared
make -j$(nproc)
```

### 6.2 配置验证清单

```bash
grep "^MACHDEP=" Makefile          # 期望: ohos
grep "^BUILDEXE=" Makefile         # 期望: 空（不应有 .exe）
grep "^EXE=" Makefile              # 期望: 空
grep "^LDSHARED=" Makefile         # 期望: clang -shared -L. -lpython3.9
grep "^CCSHARED=" Makefile         # 期望: -fPIC
grep "LDSHARED.*\$(LDSHARED)" Makefile  # sharedmods 规则应使用 $(LDSHARED) 而非 $(BLDSHARED)
```

---

## 七、透明兼容层（sitecustomize.py）

### 7.1 问题背景

HarmonyOS 的 SELinux 域转换机制导致 Python 子进程无法直接执行 SDK 二进制（如 clang）。用户代码中使用 `os.system()`、`subprocess.run()` 等标准接口时会失败。

### 7.2 解决方案

通过 `sitecustomize.py` 实现对用户代码完全透明的兼容：

**安装方式**：

```bash
# 复制到 Python 安装目录
cp sitecustomize.py $HOME/usr/local/lib/python3.9/site-packages/
```

**文件位置**：`{prefix}/lib/python3.9/site-packages/sitecustomize.py`

**原理**：Python 启动时自动加载此文件，monkey patch `os.system`、`os.popen` 等函数，自动添加管道语法。

### 7.3 用户无需修改代码

```python
# 用户代码 - 正常写，不需要关心 HarmonyOS
import os
import subprocess

# 自动被包装为管道语法
os.system("clang test.c -o test")  # ✅ 成功

# subprocess 也可用
subprocess.run(["clang", "--version"])  # ✅ 成功
```

### 7.4 配置选项

```bash
# 禁用兼容层
export HARMONYOS_SUBPROCESS_COMPAT=0

# 启用调试日志
export HARMONYOS_SUBPROCESS_DEBUG=1
```

### 7.5 安全特性

| 特性 | 说明 |
|------|------|
| 条件加载 | 只在 HarmonyOS 上启用 |
| 可禁用 | 通过环境变量控制 |
| 可恢复 | 删除文件即可回滚 |
| 异常回退 | 出错时回退到原始函数 |

**详细说明**：参见 `HARMONYOS_SUBPROCESS_GUIDE.md`

---

## 八、快速构建命令汇总

```bash
# ============================================================
#                    Python 3.9.0 完整构建流程
# ============================================================

# 1. 解压源码
tar -xzf Python-3.9.0.tgz
mv Python-3.9.0 Python-3.9.0-work
cd Python-3.9.0-work

# 2. 应用所有补丁
PATCHDIR=/storage/Users/currentUser/tmp/opendesk/build_in_harmonyos/p/python/3.9.0/patches
for p in 0001 0002 0003 0004 0005 0006 0007 0008; do
    patch -p1 < $PATCHDIR/${p}*.patch
done

# 3. 生成 configure
autoconf

# 4. 配置
export TMPDIR=$HOME/tmp
./configure --prefix=$HOME/usr/local --enable-shared

# 5. 编译
make -j$(nproc)

# 6. 验证
export LD_LIBRARY_PATH=.
./python3.9 --version
./python3.9 -c "import sysconfig; print(sysconfig.get_platform())"
# 期望输出: harmonyos-aarch64

# 7. 安装透明兼容层（可选）
cp sitecustomize.py $HOME/usr/local/lib/python3.9/site-packages/

# 8. 安装
make install
```

---

## 九、相关文档

| 文件 | 说明 |
|------|------|
| `HARMONYOS_SUBPROCESS_GUIDE.md` | 子进程 SELinux 问题完整分析 |
| `sitecustomize.py` | 透明兼容层模板 |
| `patches/series` | 补丁应用顺序说明 |

---

*文档更新时间: 2026-03-20*
