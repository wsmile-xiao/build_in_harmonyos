# Python 3.9.0 鸿蒙系统适配指南

> **版本**: 3.1 | **更新日期**: 2026-03-25 | **状态**: ✅ 已验证

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | Python 3.9.0 |
| 目标平台 | HarmonyOS aarch64 (musl libc) |
| 编译器 | Clang 15.0.4 |
| 适配复杂度 | 🔴 高（11 个补丁，涉及构建系统三层） |
| 核心功能可用性 | 74.9% 测试通过 |

### 快速开始

```bash
# 1. 环境准备
export TMPDIR=$HOME/tmp && mkdir -p $TMPDIR
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib

# 2. 下载源码
curl -L -o Python-3.9.0.tgz https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz
tar -xzf Python-3.9.0.tgz && cd Python-3.9.0

# 3. 应用补丁
PATCHDIR=/storage/Users/currentUser/tmp/opendesk/build_in_harmonyos/p/python/3.9.0/patches
for p in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011; do
    patch -p1 < $PATCHDIR/${p}*.patch
done
autoconf && ./configure --prefix=$HOME/usr/local --enable-shared && make -j$(nproc)

# 5. 验证
export LD_LIBRARY_PATH=.
./python3.9 -c "import sys; print(sys.platform)"  # 输出: ohos
```

---

## 一、适配要点

### 1.1 HarmonyOS 特有问题

| # | 问题 | 根因 | 解决补丁 |
|---|------|------|---------|
| 1 | 平台不被识别 | config.guess/config.sub 缺少 HarmonyOS | 0003, 0004 |
| 2 | configure 变量未设置 | configure.ac 缺少 HarmonyOS 分支 | 0001 |
| 3 | setup.py 不识别平台 | HOST_PLATFORM 匹配失败 | 0002 |
| 4 | 扩展模块符号找不到 | musl BIND_NOW + 缺少 libpython 链接 | 0001, 0007 |
| 5 | 硬链接不支持 | SELinux 策略 | 0007 |
| 6 | ln -sf 乱码 | toybox bug | 0007 |
| 7 | 构建路径含空格 | sys.platform 返回长字符串 | 0008 |
| 8 | 可执行文件带 .exe | 大小写检测误判 | 0001 |
| 9 | CAN socket 编译失败 | 内核头文件差异 | 0001 |
| 10 | **子进程执行 SDK 失败** | **SELinux 域转换限制** | **0006, 0009, 0010** |

---

## 二、完整构建流程

### 2.1 环境要求

```bash
export TMPDIR=$HOME/tmp          # /tmp 只读
export CC=clang CXX=clang++
export AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip
```

### 2.2 获取源码

```bash
cd ~/python
curl -L -o Python-3.9.0.tgz https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz
tar -xzf Python-3.9.0.tgz && cd Python-3.9.0
```

### 2.3 应用补丁

```bash
PATCHDIR=/storage/Users/currentUser/tmp/opendesk/build_in_harmonyos/p/python/3.9.0/patches
for p in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010; do
    patch -p1 < $PATCHDIR/${p}*.patch
done
```

### 2.4 配置与编译

```bash
autoconf
./configure --prefix=$HOME/usr/local --enable-shared
make -j$(nproc)
```

### 2.5 验证

```bash
export LD_LIBRARY_PATH=.
./python3.9 --version
./python3.9 -c "import sys; print(sys.platform)"  # ohos
```

### 2.6 安装

```bash
make install
echo 'export PATH=$HOME/usr/local/bin:$PATH' >> ~/.zshrc
echo 'export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.zshrc
```

---

## 三、补丁详解

### 3.1 补丁清单

| 编号 | 文件 | 修改内容 |
|------|------|---------|
| 0001 | configure.ac | 平台识别、链接器、功能检测 |
| 0002 | setup.py | 扩展模块编译、SDK 路径 |
| 0003 | config.guess | 三元组识别 |
| 0004 | config.sub | 三元组验证 |
| 0005 | Lib/distutils/util.py | distutils 平台标识 |
| 0006 | Lib/_bootsubprocess.py | setup.py 子进程修复 |
| 0007 | Makefile.pre.in | 链接规则、安装修复 |
| 0008 | Lib/sysconfig.py | 运行时平台字符串 |
| 0009 | Lib/_harmonyos_compat.py | 子进程兼容层模块 |
| 0010 | Lib/site.py | 自动加载兼容层 |

---

### 3.2 补丁 0001：configure.ac（核心补丁）

**修改文件**：`configure.ac`（Autotools 入口，生成 configure 脚本）

**修改点数量**：10 处

#### 修改点 1：交叉编译平台识别

```diff
 *-*-vxworks*)
     ac_sys_system=VxWorks
     ;;
+*-*-linux-ohos*)
+    ac_sys_system=HarmonyOS
+    ;;
```

**问题背景**：当使用 `--host=aarch64-linux-ohos` 进行交叉编译时，configure 需要识别目标系统。

**技术原理**：
- `--host` 参数值（如 `aarch64-linux-ohos`）会被解析
- 原代码只识别 `*-*-vxworks*` 等已知模式，遇到 `linux-ohos` 会进入默认分支报错
- 添加匹配规则后，`ac_sys_system` 被设为 `HarmonyOS`

**举一反三**：任何 Autotools 项目在 HarmonyOS 上交叉编译都需要类似的平台识别规则。

---

#### 修改点 2：MACHDEP 设置

```diff
 case $MACHDEP in
     linux*) MACHDEP="linux";;
+    harmonyos*|HarmonyOS*) MACHDEP="ohos";;
```

**问题背景**：MACHDEP 决定 Python 内部模块搜索路径（如 `Lib/ohos/`）。

**技术原理**：
- `uname -s` 返回 `HarmonyOS`，转小写后为 `harmonyos`
- 原代码不匹配，MACHDEP 会变成 `harmonyos1.11.0`（含内核版本），导致路径错误
- 映射为 `ohos` 保持简洁，与 `linux` 命名风格一致

**举一反三**：涉及平台相关路径的软件都需要处理 MACHDEP 类似变量。

---

#### 修改点 3：跳过 _XOPEN_SOURCE 定义

```diff
 SunOS/*)
   define_xopen_source=no;;
+HarmonyOS/*)
+  define_xopen_source=no;;
```

**问题背景**：`_XOPEN_SOURCE` 宏用于启用 POSIX/X/Open 标准接口。

**技术原理**：
- glibc 需要此宏来暴露某些函数原型
- musl libc（HarmonyOS 使用）已默认提供完整 POSIX 支持
- 定义 `_XOPEN_SOURCE` 可能导致 musl 隐藏某些函数，引发编译错误

**举一反三**：所有使用 musl 的系统（Alpine、OpenWrt）都应跳过此定义。

---

#### 修改点 4：交叉编译三元组生成

```diff
 #if defined(__ANDROID__)
     # Android is not a multiarch system.
+#elif defined(__OHOS__)
+    # HarmonyOS/OpenHarmony uses musl libc
+# if defined(__aarch64__)
+        aarch64-linux-ohos
+# elif defined(__arm__)
+        arm-linux-ohos
 ...
```

**问题背景**：`_PYTHON_HOST_PLATFORM` 决定构建目录路径（如 `build/lib.linux-x86_64-3.9/`）。

**技术原理**：
- 此值通过 C 预处理器在 configure 阶段计算
- 需要检测 `__OHOS__` 宏（Clang 自动定义）
- 生成正确的三元组 `aarch64-linux-ohos`

**举一反三**：任何软件如果使用类似的三元组来命名构建目录，都需要添加 `__OHOS__` 分支。

---

#### 修改点 5：跳过 BUILDEXEEXT 大小写检测

```diff
 AC_SUBST(BUILDEXEEXT)
-case $ac_sys_system in
+AC_MSG_CHECKING(for case-insensitive build directory)
+if mkdir conftestdir 2>/dev/null; then
 ...
+case $ac_sys_system in
+    HarmonyOS*)
+        BUILDEXEEXT=$EXEEXT
+        AC_MSG_RESULT(no - skipped for HarmonyOS)
+        ;;
+    *)
+        # 原有检测逻辑
 ...
```

**问题背景**：configure 通过创建 `CaseSensitiveTestDir` 然后检查 `casesensitivetestdir` 是否存在来判断文件系统是否大小写不敏感。

**技术原理**：
- 此检测在 HarmonyOS 上结果不可靠（可能误判为不敏感）
- 误判导致 `BUILDEXEEXT=.exe`，生成 `python3.9.exe` 而非 `python3.9`
- 解决：HarmonyOS 分支直接使用 `$EXEEXT`（空值），跳过检测

**举一反三**：任何 Autotools 项目如果遇到可执行文件莫名加 `.exe` 后缀，检查此检测逻辑。

---

#### 修改点 6：共享库设置

```diff
+HarmonyOS*)
+    LDLIBRARY='libpython$(LDVERSION).so'
+    BLDLIBRARY='-L. -lpython$(LDVERSION)'
+    RUNSHARED=LD_LIBRARY_PATH=`pwd`${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
+    INSTSONAME="$LDLIBRARY".$SOVERSION
+    ;;
 Linux*|GNU*|NetBSD*|FreeBSD*)
```

**问题背景**：这组变量控制 Python 共享库的构建和运行方式。

**技术原理**：

| 变量 | 作用 |
|------|------|
| `LDLIBRARY` | 主共享库名称（`libpython3.9.so.1.0`） |
| `BLDLIBRARY` | 构建时链接的库路径（`-L. -lpython3.9`） |
| `RUNSHARED` | 运行时库搜索路径（设置 `LD_LIBRARY_PATH`） |
| `INSTSONAME` | 安装时的 soname |

**举一反三**：任何需要构建共享库的项目都需要正确设置这些变量。

---

#### 修改点 7：LDSHARED / BLDSHARED 设置（⭐ 最关键）

```diff
+HarmonyOS*)
+    BLDSHARED='$(CC) -shared'
+    LDSHARED='$(CC) -shared -L. -lpython$(LDVERSION)'
+    LDCXXSHARED='$(CXX) -shared'
+    ;;
 Linux*)
```

**问题背景**：这是解决 **musl BIND_NOW 问题** 的核心修改。

**技术原理**：

```
musl libc 默认启用 BIND_NOW
    ↓
动态链接器加载 .so 时要求所有符号必须立即解析
    ↓
Python 扩展模块的 NEEDED 只有 libc.so（无 libpython）
    ↓
Python API 符号（_PyType_Name 等）无法解析
    ↓
ImportError: symbol not found
```

**关键区别**：

| 变量 | 用途 | 含 -lpython？ | 原因 |
|------|------|--------------|------|
| `BLDSHARED` | 构建 `libpython.so` 本身 | ❌ 不能 | 循环依赖：不能链接自己 |
| `LDSHARED` | 构建扩展模块 `.so` | ✅ 必须 | 扩展模块需要 Python API |

**举一反三**：
- 所有插件系统（Python、Perl、Ruby 扩展）在 musl 环境都需要处理此问题
- 检查扩展模块的 NEEDED：`llvm-readelf -d module.so | grep NEEDED`
- 应该看到 `libpython` 在 NEEDED 列表中

---

#### 修改点 8：CCSHARED 设置

```diff
+HarmonyOS*) CCSHARED="-fPIC";;
 Linux-android*) ;;
```

**问题背景**：`-fPIC`（Position Independent Code）是共享库的必需编译选项。

**技术原理**：
- 共享库在运行时可以被加载到任意内存地址
- `-fPIC` 生成使用相对地址的代码，支持动态加载
- 不加此选项会导致链接错误：`relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used`

**举一反三**：任何编译共享库的项目都必须使用 `-fPIC`。

---

#### 修改点 9：LINKFORSHARED 设置

```diff
+HarmonyOS*)
+    LINKFORSHARED="-Xlinker -export-dynamic";;
```

**问题背景**：Python 解释器需要导出符号供扩展模块使用。

**技术原理**：
- `-export-dynamic` 让链接器将所有符号导出到动态符号表
- 扩展模块通过 `dlopen()` 加载后，需要反向查找解释器的符号
- 如 `Py_None`、`PyExc_ValueError` 等

**举一反三**：任何支持插件系统的主程序都需要此选项。

---

#### 修改点 10：CAN socket 宏检测跳过

```diff
 AC_MSG_CHECKING(for CAN_RAW_FD_FRAMES)
+case $ac_sys_system in
+    HarmonyOS*)
+        AC_MSG_RESULT(no - skipped for HarmonyOS)
+        ;;
+    *)
         AC_COMPILE_IFELSE([AC_LANG_PROGRAM([[
```

**问题背景**：HarmonyOS 内核头文件声明了 `CAN_RAW_FD_FRAMES` 但未定义其值。

**技术原理**：
- configure 检测通过（头文件存在声明）
- 实际编译时宏值为空，导致错误
- 解决：跳过检测，不定义 `HAVE_LINUX_CAN_RAW_FD_FRAMES`

**举一反三**：遇到"头文件声明但未定义"的情况，跳过检测是最安全的方案。

---

### 3.3 补丁 0002：setup.py

**修改文件**：`setup.py`（Python 扩展模块编译脚本）

#### 修改点 1：平台识别

```diff
 VXWORKS = ('vxworks' in HOST_PLATFORM)
+OHOS = (HOST_PLATFORM.startswith('harmony') or HOST_PLATFORM.startswith('ohos'))
```

**问题背景**：`HOST_PLATFORM` 来自 configure，值为 `harmonyos-aarch64`。

**技术原理**：
- 原代码用精确匹配 `HOST_PLATFORM in ['harmony', 'ohos']`
- 实际值带架构后缀，精确匹配失败
- 改用 `startswith()` 前缀匹配

**举一反三**：任何基于平台字符串判断的逻辑都要考虑字符串格式的变化。

---

#### 修改点 2：SDK 路径搜索

```python
if OHOS:
    sysroot = ohos_sdk_root()
    if sysroot:
        full_lib_dir = os.path.join(sysroot, "usr", "lib", f"{arch}-linux-ohos")
        self.lib_dirs.append(full_lib_dir)
```

**问题背景**：setup.py 需要搜索 SDK 提供的头文件和库。

**技术原理**：
- HarmonyOS SDK 的库文件在 `usr/lib/aarch64-linux-ohos/` 这样的多架构目录
- 需要添加到 `lib_dirs` 和 `include_dirs` 搜索路径

**举一反三**：任何需要搜索 SDK/系统库的构建脚本都需要处理类似的多架构路径。

---

### 3.4 补丁 0003/0004：config.guess 和 config.sub

**修改文件**：`config.guess`（平台检测）、`config.sub`（三元组验证）

#### config.guess 修改

```diff
+*:HarmonyOS:*:*)
+    case "$UNAME_MACHINE" in
+        aarch64|arm64)
+            echo "aarch64-unknown-linux-ohos"
+            ;;
```

**问题背景**：`config.guess` 通过 `uname` 系统调用检测当前平台。

**技术原理**：
- `uname -s` 返回 `HarmonyOS`
- 原代码不认识此系统名
- 添加匹配规则，生成三元组 `aarch64-unknown-linux-ohos`

**三元组格式**：`{架构}-{厂商}-{操作系统}`
- `aarch64`：CPU 架构
- `unknown`：厂商（本地构建未知）
- `linux-ohos`：基于 Linux 内核的 HarmonyOS

**举一反三**：任何 Autotools 项目都需要这两个文件的 HarmonyOS 支持。

---

#### config.sub 修改

```diff
 nto-qnx* | linux-gnu* | linux-android* | linux-ohos* | ...
```

**问题背景**：`config.sub` 验证三元组的 OS 部分是否合法。

**技术原理**：
- 添加 `linux-ohos*` 到已知 OS 列表
- 防止被 `linux*` 通配符错误地映射为 `linux-gnu`

**举一反三**：与 config.guess 配套，所有 Autotools 项目都需要。

---

### 3.5 补丁 0005：distutils/util.py

**修改文件**：`Lib/distutils/util.py`

```diff
+elif osname[:9] == "harmonyos":
+    return "ohos-%s-%s" % (osname, machine)
```

**问题背景**：`distutils.get_platform()` 生成分发包的平台标签。

**技术原理**：
- `osname` 是 `HarmonyOS`
- `release` 是 `HongMeng Kernel 1.11.0`（含空格）
- 原逻辑：`HarmonyOS HongMeng Kernel 1.11.0-aarch64`（非法路径）
- 修改后：`ohos-HarmonyOS-aarch64`（跳过 release）

**举一反三**：任何涉及平台字符串拼接的代码都要注意空格问题。

---

### 3.6 补丁 0006：_bootsubprocess.py

**修改文件**：`Lib/_bootsubprocess.py`（setup.py 编译扩展模块时使用）

```python
# 原代码（失败）
def wait(self):
    pid = os.fork()
    if pid == 0:
        os.execv(self._cmd[0], self._cmd)  # SELinux 拦截

# 修改后（成功）
def wait(self):
    cmd_str = ' '.join(shlex.quote(arg) for arg in self._cmd)
    cmd_str = f"set -o pipefail; {cmd_str} 2>&1 | cat"
    return os.system(cmd_str)
```

**问题背景**：setup.py 通过 `_bootsubprocess.Popen` 调用 clang 编译扩展模块。

**技术原理**：

```
SELinux 域转换链：
  Shell (hishell_hap:s0) → exec Python → 域转换为 adhoc_bin:s0
                                                  ↓
                                      无法 exec SDK 工具 (hnp_file)

管道语法绕过：
  os.system("cmd | cat") → /bin/sh 创建子进程执行管道
                          → 子进程具有不同权限 → 可以执行 SDK 工具
```

**关键点**：
- `set -o pipefail`：确保退出码反映实际命令的状态
- `2>&1 | cat`：捕获 stderr，强制创建管道子进程

**举一反三**：任何通过子进程调用 SDK 工具的场景都需要此 workaround。

---

### 3.7 补丁 0007：Makefile.pre.in

**修改文件**：`Makefile.pre.in`（Makefile 模板）

#### 修改点 1：sharedmods 使用 LDSHARED

```diff
 sharedmods: $(BUILDPYTHON)
-    @$(RUNSHARED) CC='$(CC)' LDSHARED='$(BLDSHARED)' ...
+    @$(RUNSHARED) CC='$(CC)' LDSHARED='$(LDSHARED)' ...
```

**问题背景**：`sharedmods` 规则调用 setup.py 编译扩展模块。

**技术原理**：
- 原代码传 `$(BLDSHARED)`（不含 `-lpython`）
- 需要传 `$(LDSHARED)`（含 `-lpython`）
- 这是 musl BIND_NOW 问题在 Makefile 层面的修复

---

#### 修改点 2：硬链接处理

```diff
-HARDLINK= ln
+HARDLINK= $(shell uname -s 2>/dev/null | grep -qi harmony && echo cp -p || echo ln)
```

**问题背景**：HarmonyOS 不支持硬链接（SELinux 策略）。

**技术原理**：
- 运行时检测系统是否为 HarmonyOS
- 是则用 `cp -p` 替代 `ln`（复制文件）
- `-p` 保留权限和时间戳

**举一反三**：任何使用硬链接的安装脚本都需要类似处理。

---

#### 修改点 3：ln -sf 问题

```diff
-LN_FORCE= ln -sf
+LN_FORCE= $(shell uname -s 2>/dev/null | grep -qi harmony && echo "rm -f && ln -s" || echo "ln -sf")
```

**问题背景**：toybox 的 `ln -sf` 在 HarmonyOS 上有 bug，会创建带随机后缀的文件。

**技术原理**：
- 改用先 `rm -f` 删除，再 `ln -s` 创建
- 分步操作避免 toybox bug

**举一反三**：遇到 toybox 工具行为异常时，考虑用标准命令替代。

---

### 3.8 补丁 0008：sysconfig.py

**修改文件**：`Lib/sysconfig.py`

```diff
+elif osname[:9] == "harmonyos" or osname[:4] == "ohos":
+    return "%s-%s" % (osname, machine)
```

**问题背景**：`sysconfig.get_platform()` 用于构建目录路径。

**技术原理**：与补丁 0005 类似，跳过含空格的 release 字符串。

**与 0005 的区别**：
- 0005 修改 `distutils`（用于分发包）
- 0008 修改 `sysconfig`（用于构建系统）

---

### 3.9 补丁 0009/0010：子进程兼容层

**新增文件**：`Lib/_harmonyos_compat.py`
**修改文件**：`Lib/site.py`

#### 设计思路

**问题**：即使修复了 `_bootsubprocess.py`，用户代码中直接使用 `subprocess.run()` 仍会失败。

**方案对比**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| sitecustomize.py | 易禁用 | 需手动安装 |
| **源码集成** | 自动生效 | 需修改源码 |

#### 实现原理

```python
# _harmonyos_compat.py
def _wrap_with_pipe(cmd_str):
    return f"set -o pipefail; {cmd_str} 2>&1 | cat"

def _apply_compat_layer():
    # 包装 os.system
    os.system = _wrapped_os_system
    
    # 包装 subprocess.Popen
    subprocess.Popen.__init__ = _wrapped_popen_init
```

```python
# site.py
def main():
    try:
        import _harmonyos_compat
        _harmonyos_compat.init()
    except ImportError:
        pass
```

**关键特性**：
- 只在 HarmonyOS 上启用（检测 `sys.platform`）
- Python 启动时自动加载
- 对用户代码完全透明

**举一反三**：任何需要系统级 workaround 的场景都可以用类似的 monkey patch 方式。

---

### 3.10 补丁 0011：venv/__init__.py（symlink fallback）

**修改文件**：`Lib/venv/__init__.py`（Python 虚拟环境创建模块）

#### 问题背景

Python 3.9 的 `venv` 模块在 64 位 POSIX 系统上（非 macOS）会自动创建 `lib64 -> lib` 符号链接（[Issue #21197](https://bugs.python.org/issue21197)），以便某些通过 `lib64` 路径安装的第三方包能被正确找到。

然而 HarmonyOS 的用户主目录使用 HMDFS 文件系统，该文件系统**完全不支持 `os.symlink()`**——调用会 100% 抛出 `PermissionError`，原因是 SELinux Hmmac 策略禁止创建符号链接。

```python
# 直接复现
import os
os.symlink('lib', '/storage/Users/currentUser/tmp/test-link')
# OSError: [Errno 13] Permission denied
```

这导致 `python3 -m venv` 和 `venv.EnvBuilder()` 完全无法使用。

#### 修改内容

```diff
             link_path = os.path.join(env_dir, 'lib64')
             if not os.path.exists(link_path):   # Issue #21643
-                os.symlink('lib', link_path)
+                try:
+                    os.symlink('lib', link_path)
+                except OSError:
+                    # HarmonyOS: HMDFS does not support symlinks (SELinux + Hmmac).
+                    # Fall back to creating lib64 as a real directory.
+                    os.makedirs(link_path, exist_ok=True)
```

#### 为什么创建目录而不是 symlink 就够了？

关键在于 `sysconfig.get_path()` 的实现：

```python
# sysconfig.get_path('purelib') 的计算逻辑（简化）
# ❌ 不是基于 _sysconfigdata 中的 LIBDIR（静态值，编译时烘焙）
# ✅ 而是基于 sys.prefix（动态值，venv 启动时计算）
purelib = os.path.join(sys.prefix, 'lib', 'python3.9', 'site-packages')
```

| 接口 | 值来源 | 正确？ |
|------|--------|--------|
| `sys.prefix` | 动态（venv 目录） | ✅ |
| `sysconfig.get_path('purelib')` | 基于 sys.prefix | ✅ |
| `sysconfig.get_config_var('LIBDIR')` | 静态（编译时烘焙） | ❌ 不一致 |

`pip install`、`ensurepip`、`setuptools` 都使用 `sysconfig.get_path()`，所以 `lib64` 是 symlink 还是真实目录对它们没有影响。

#### 技术原理

```
问题链：
  venv 创建 → os.symlink('lib', 'lib64') → HMDFS 不支持 → OSError → 失败

修复逻辑：
  try: os.symlink('lib', 'lib64')       # 标准系统正常工作
  except OSError: os.makedirs('lib64')  # HarmonyOS fallback
```

**举一反三**：
- 所有调用 `os.symlink()` 的 Python 代码在 HarmonyOS 上都需要类似处理
- 在 HMDFS 以外的路径（如 `/data/`）symlink 可能可用，但用户目录下一定不行
- 也可以在运行时检测文件系统是否支持 symlink，而非捕获异常

---

## 四、测试验证

### 4.1 测试结果

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 通过 | 314 | 74.9% |
| ❌ 失败 | 80 | 19.1% |
| ⏭️ 跳过 | 25 | 6.0% |

### 4.2 核心功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 数据结构 | ✅ | dict, list, tuple, set |
| 字符串/编码 | ✅ | unicode, codecs |
| 数学运算 | ✅ | math, cmath, decimal |
| 文件 I/O | ✅ | fileio, memoryio |
| 序列化 | ✅ | pickle, json, csv |
| 数据库 | ✅ | sqlite, dbm |
| 加密/安全 | ✅ | ssl, hashlib |
| 网络 | ✅ | http, ftp, smtp |
| 多进程 | ⚠️ | 部分受限 |

---

## 五、依赖关系

### 5.1 上游依赖（编译 Python 需要的软件）

| 依赖 | 用途 | 必需？ | 鸿蒙状态 |
|------|------|--------|---------|
| **Clang** | C/C++ 编译器 | ✅ 必需 | SDK 自带 |
| **LLVM 工具链** | llvm-ar, llvm-ranlib 等 | ✅ 必需 | SDK 自带 |
| **OpenSSL** | _ssl 模块（HTTPS） | ⚠️ 推荐 | 需单独编译 |
| **libffi** | _ctypes 模块 | ⚠️ 推荐 | 需单独编译 |
| **zlib** | zlib 模块（压缩） | ⚠️ 推荐 | 需单独编译 |
| **ncurses** | curses 模块（终端） | ⚠️ 可选 | 需单独编译 |
| **readline** | 交互式输入 | ⚠️ 可选 | 需单独编译 |
| **SQLite** | sqlite3 模块 | ⚠️ 可选 | 需单独编译 |

### 5.2 编译依赖的推荐顺序

```
1. OpenSSL  → Python _ssl 模块（HTTPS 支持）
2. libffi   → Python _ctypes 模块（FFI 支持）
3. zlib     → Python zlib 模块（压缩支持）
4. ncurses  → Python curses 模块（终端 UI）
5. readline → Python 交互式输入增强
6. SQLite   → Python sqlite3 模块
7. Python   → 最终目标
```

### 5.3 下游被依赖（依赖 Python 的软件）

| 软件 | 用途 | 说明 |
|------|------|------|
| **pip** | Python 包管理器 | 需要 _ssl 模块 |
| **setuptools** | 构建系统 | 核心依赖 |
| **wheel** | 打包工具 | 打包依赖 |
| **NumPy** | 科学计算 | 需要 BLAS/LAPACK |
| **Requests** | HTTP 库 | 需要 _ssl 模块 |
| **Django/Flask** | Web 框架 | 需要 _ssl 模块 |
| **许多构建系统** | Meson, SCons 等 | 构建依赖 |

---

## 六、常见问题

### Q1: cross build not supported

**现象**：`configure: error: cross build not supported for aarch64-linux-ohos`

**原因**：补丁 0001、0003 未正确应用

**解决**：
```bash
patch -p1 < patches/0001-configure.ac-HarmonyOS-support.patch
patch -p1 < patches/0003-config.guess-HarmonyOS-support.patch
autoconf
```

---

### Q2: symbol not found（扩展模块加载失败）

**现象**：`ImportError: Error relocating _struct.so: _PyType_Name: symbol not found`

**原因**：musl BIND_NOW 问题，扩展模块未链接 libpython

**解决**：
1. 检查 LDSHARED 是否包含 `-lpython`：
   ```bash
   grep "^LDSHARED=" Makefile
   # 期望: LDSHARED= ... -lpython3.9
   ```
2. 重新应用补丁 0001 和 0007

---

### Q3: subprocess 执行 SDK 工具失败

**现象**：`subprocess.run(['clang', '--version'])` 返回 exit code 1，无输出

**原因**：SELinux 域转换限制，兼容层未生效

**解决**：
1. 确认补丁 0009、0010 已应用
2. 验证兼容层加载：
   ```python
   import _harmonyos_compat  # 应该成功
   ```

---

### Q4: python3.9.exe 而非 python3.9

**现象**：生成的可执行文件名带 `.exe` 后缀

**原因**：BUILDEXEEXT 大小写检测误判

**解决**：应用补丁 0001，确认 `grep "^BUILDEXE=" Makefile` 输出为空

---

### Q5: 硬链接创建失败

**现象**：`ln: cannot create hard link: Operation not permitted`

**原因**：HarmonyOS SELinux 策略禁止硬链接

**解决**：应用补丁 0007，Makefile 会自动使用 `cp -p` 替代

---

### Q6: 编译扩展模块时找不到头文件

**现象**：`fatal error: Python.h: No such file`

**原因**：未设置正确的包含路径

**解决**：
```bash
export CFLAGS="-I$HOME/usr/local/include/python3.9"
```

---

### Q7: 运行时找不到 libpython

**现象**：`error while loading shared libraries: libpython3.9.so.1.0`

**原因**：未设置 LD_LIBRARY_PATH

**解决**：
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
# 或添加到 ~/.zshrc
```

---

## 七、技术要点总结

### 7.1 构建系统三层适配模式

Python 的构建系统是三层架构，任何类似复杂度的软件都可能有类似结构：

```
┌─────────────────────────────────────────────────────────────┐
│                  构建系统三层模型                            │
├─────────────────────────────────────────────────────────────┤
│  第一层：平台检测层                                          │
│  - 文件：config.guess, config.sub                           │
│  - 作用：检测系统类型，生成三元组                            │
│  - HarmonyOS 适配：添加 HarmonyOS 识别规则                  │
├─────────────────────────────────────────────────────────────┤
│  第二层：配置生成层                                          │
│  - 文件：configure.ac, CMakeLists.txt                       │
│  - 作用：生成构建配置（Makefile 等）                         │
│  - HarmonyOS 适配：添加 HarmonyOS 分支设置变量              │
├─────────────────────────────────────────────────────────────┤
│  第三层：构建执行层                                          │
│  - 文件：Makefile, setup.py, *.cmake                        │
│  - 作用：实际编译、链接、安装                                │
│  - HarmonyOS 适配：修改编译选项、链接参数                   │
└─────────────────────────────────────────────────────────────┘
```

**举一反三**：遇到构建问题时，从下往上排查——先检查构建执行层，再检查配置生成层，最后检查平台检测层。

---

### 7.2 musl BIND_NOW 问题模式

**问题模式**：插件/扩展系统在 musl 环境下加载失败

**诊断步骤**：
1. 检查 `.so` 的 NEEDED 列表：`llvm-readelf -d module.so | grep NEEDED`
2. 确认是否缺少主程序库（如 libpython）
3. 修改链接命令添加主程序库

**通用解决方案**：

| 场景 | 解决方案 |
|------|---------|
| Python 扩展 | LDSHARED 添加 `-lpython` |
| Perl XS | LDDLFLAGS 添加 `-lperl` |
| Ruby 扩展 | DLDFLAGS 添加 `-lruby` |
| 通用插件 | 链接时添加 `-L. -l主程序库名` |

---

### 7.3 SELinux 域转换问题模式

**问题模式**：用户程序子进程无法执行系统工具

**诊断步骤**：
1. 检查进程 SELinux context：`cat /proc/self/attr/current`
2. 检查目标文件 context：`ls -Z /path/to/file`
3. 确认是否域转换导致权限丢失

**通用解决方案**：
- 管道语法：`os.system("cmd | cat")`
- 通过 shell 包装：`/bin/sh -c "cmd"`
- 使用具有正确 context 的 wrapper

---

### 7.4 平台字符串处理模式

**问题模式**：平台字符串包含特殊字符（空格、版本号）

**HarmonyOS 特点**：
- `uname -s` → `HarmonyOS`
- `uname -r` → `HongMeng Kernel 1.11.0`（含空格）

**处理原则**：
1. 使用 `startswith()` 而非精确匹配
2. 跳过 release 字符串避免空格问题
3. 标准化为简短名称（如 `ohos`）

---

### 7.5 条件编译模式

**问题模式**：某些功能在 HarmonyOS 上不可用或行为不同

**检测方法**：
```c
#ifdef __OHOS__
    // HarmonyOS 特定代码
#else
    // 标准 Linux 代码
#endif
```

**适用场景**：
- 系统调用行为差异（fstat、lseek）
- 功能缺失（硬链接、PTY）
- 头文件差异（CAN socket）

---

## 八、相关文件

| 文件 | 用途 |
|------|------|
| `patches/` | 补丁文件 |
| `tests/test_subprocess_compat.py` | 兼容层测试 |
| `package_python.sh` | 打包脚本 |
| `HARMONYOS_SUBPROCESS_GUIDE.md` | 子进程问题深入分析 |
| `TEST_REPORT.md` | 测试详情 |

---

## 九、版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-21 | 1.0 | 初始版本 |
| 2026-03-21 | 2.0 | 补丁详解完善，添加举一反三 |
| 2026-03-21 | 3.0 | 添加依赖关系、技术要点总结章节 |
| 2026-03-25 | 3.1 | 新增补丁 0011（venv symlink fallback）、统一测试数据（425/314/80/25/6） |

---

*维护者: OpenHarmony 社区*��容层测试 |
| `package_python.sh` | 打包脚本 |
| `HARMONYOS_SUBPROCESS_GUIDE.md` | 子进程问题深入分析 |
| `TEST_REPORT.md` | 测试详情 |

---

## 九、版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-21 | 1.0 | 初始版本 |
| 2026-03-21 | 2.0 | 补丁详解完善，添加举一反三 |
| 2026-03-21 | 3.0 | 添加依赖关系、技术要点总结章节 |

---

*维护者: OpenHarmony 社区*