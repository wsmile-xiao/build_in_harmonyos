# Python 3.9.0 鸿蒙系统适配指南

> **版本**: 4.2 | **更新日期**: 2026-03-26 | **状态**: ⚠️ 部分验证（详见 STATUS.md）

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | Python 3.9.0 |
| 目标平台 | HarmonyOS aarch64 (musl libc) |
| 编译器 | Clang 15.0.4 |
| 适配复杂度 | 🔴 高（20 个补丁，涉及构建系统三层） |
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
PATCHDIR=/storage/Users/currentUser/renshang/build_in_harmonyos/archives/p/python/3.9.0/patches
for p in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011 0012 0013 0014 0015 0016 0017 0018 0019 0020; do
    patch -p1 < $PATCHDIR/${p}*.patch
done
CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib" autoconf && ./configure --prefix=$HOME/usr/local --disable-ipv6 ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no --enable-shared && make -j$(nproc)

# 5. 验证
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
python3.9 -c "import sys; print(sys.platform)"  # 输出: ohos
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
PATCHDIR=/storage/Users/currentUser/renshang/build_in_harmonyos/archives/p/python/3.9.0/patches
for p in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011 0012 0013 0014 0015 0016 0017 0018 0019 0020; do
    patch -p1 < $PATCHDIR/${p}*.patch
done
```

### 2.4 配置与编译

```bash
autoconf
CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib" ./configure --prefix=$HOME/usr/local --disable-ipv6 ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no --enable-shared
make -j$(nproc)
```

### 2.5 验证

```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
python3.9 --version
python3.9 -c "import sys; print(sys.platform)"  # ohos
python3.9 -c "import ssl; print(ssl.OPENSSL_VERSION)"  # OpenSSL 1.1.1w
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
| 0011 | Lib/venv/__init__.py | venv symlink→makedirs 降级 |
| 0012 | Include/pythread.h | threading.get_native_id() 支持 |
| 0013 | Lib/multiprocessing/context.py | 默认 spawn 模式 |
| 0014 | Lib/multiprocessing/util.py | abstract sockets 支持 |
| 0015 | Lib/posixpath.py | PATH 添加 /system/bin |
| 0016 | Lib/subprocess.py | 子进程全面修复（541 行） |
| 0017 | Modules/_posixsubprocess.c | FD_DIR 改为 /dev/fd |
| 0018 | Modules/posixmodule.c | posix_fallocate 支持 |
| 0019 | Modules/timemodule.c | musl 时区处理 |
| 0020 | Lib/subprocess.py | 修复 0016 遗留（pipe/execve/posix_spawn） |

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

根本原因在于当前平台的 `platlibdir` 值：

```python
import sysconfig
sysconfig.get_config_var('platlibdir')
# 'lib'  ← 不是 'lib64'
```

`platlibdir` 在编译时由 `_sysconfigdata` 烘焙，值为 `lib`（不是 `lib64`），所以 Python 的所有路径都基于 `lib/` 而非 `lib64/`：

```python
# sysconfig.get_path('purelib') 的实际计算：
#   {venv_dir}/lib/python3.9/site-packages
# 而不是：
#   {venv_dir}/lib64/python3.9/site-packages

purelib = os.path.join(sys.prefix, 'lib', 'python3.9', 'site-packages')
```

| 接口 | 值 | 说明 |
|------|-----|------|
| `sysconfig.get_config_var('platlibdir')` | `'lib'` | 编译时确定，决定路径骨架 |
| `sysconfig.get_path('purelib')` | `.../lib/python3.9/site-packages` | 基于 `sys.prefix` + `platlibdir` |
| `sysconfig.get_config_var('LIBDIR')` | 编译时路径（不一致） | 静态值，不被 get_path() 使用 |

`pip install`、`ensurepip`、`setuptools` 全部使用 `sysconfig.get_path()`，该函数基于动态的 `sys.prefix` + `platlibdir`，**根本不读取 `LIBDIR`**。因此 `lib64` 是 symlink 还是真实目录对它们没有任何影响——只要它存在，venv 就不会报错。

> **补充**：在某些 Linux 发行版（RHEL/Fedora）上，`platlibdir` 是 `lib64`，`lib64 -> lib` symlink 才有意义——它让硬编码 `lib64` 路径的第三方工具也能找到包。HarmonyOS 上 `platlibdir` 是 `lib`，symlink 纯粹是防御性代码，创建空目录即可。

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

> ⚠️ **注意**：以下测试结果基于 11 补丁版本（v3.1），已过期。完整测试需使用 20 补丁版本（v4.1）重新验证。

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
| `patches/` | 补丁文件（0001~0020） |
| `HARMONYOS_SUBPROCESS_GUIDE.md` | 子进程执行完整指南 |

---

## 九、全量构建验证成果（2026-03-25 第二轮）

### 9.1 扩展模块编译

从源码 tar 包全量构建，**64 个扩展模块编译链接成功**（含 CJK 编解码模块，修复 libintl_gettext 问题后），其中 30 个核心模块验证导入成功。

| 类别 | 数量 | 说明 |
|------|------|------|
| ✅ 编译成功 | 64 | 包括 math, json, pickle, xml, unicodedata, CJK 编解码（_multibytecodec, _codecs_kr/jp/cn/tw/hk/iso2022）等 |
| ✅ 导入测试通过 | 30 | 核心模块验证（math, json, pickle, xml, unicodedata 等） |
| ⚠️ 编译成功但导入失败 | 2 | _gdbm, _lzma（运行时库路径问题） |
| ❌ 编译失败 | 1 | _ctypes（ffi 头文件/库找不到） |
| ⏭️ 依赖缺失未编译 | 10+ | _ssl, _hashlib, _sqlite3, _tkinter 等 |
| ✅ multiprocessing 模块 | 1 | spawn 方式可用，Pool 测试通过 |

### 9.2 关键新发现

> 完整分析见 [HARMONYOS_SUBPROCESS_GUIDE.md](../HARMONYOS_SUBPROCESS_GUIDE.md)

#### 发现 1：鸿蒙 Pipe 数据丢失

**症状**：`posix_spawnp()` + pipe 重定向 stderr 时，子进程输出完全丢失（0 bytes）。

**原因**：Python 进程的 fd 0/1/2 在鸿蒙上是 socket（非终端/文件），子进程继承后 pipe 重定向行为异常。

**~~方案~~**（已废弃）：用临时文件替代 pipe — ~~在 `Popen._get_handles()` 层面实现，调用方接口不变。~~ 补丁 0020 修复后 `os.pipe()` 在鸿蒙上可正常使用，无需临时文件替代方案。

#### 发现 2：fork_exec 纯 Python Fallback

Python 3.9 的 `subprocess.py` 对 `_posixsubprocess` C 扩展有硬依赖，缺失时整个模块不可用。

**方案**：参考 Python 3.12+ 做法，实现纯 Python 的 `_python_fork_exec()`，并在鸿蒙上启用 `_USE_POSIX_SPAWN = True`。

#### 发现 3：C 级系统调用测试结论

| 原语 | SDK 工具 | 系统命令 |
|------|:---:|:---:|
| `fork()` | ✅ 可用 | ✅ 正常 |
| `fork() + execve()` | ❌ SELinux 拦截 | ⚠️ 受权限影响 |
| `posix_spawnp()` | ⚠️ 0020 修复后可用 | ✅ 正常 |
| `system("cmd \| cat")` | ✅ **Pipe 绕过** | ✅ 正常 |

**结论**：
- **fork() 在鸿蒙上可用**，`posix_spawn` 是推荐的子进程创建方式（补丁 0020 已修复相关问题）。
- Pipe 绕过法（`cmd | cat`）仍然是 **SDK 工具执行场景** 下可靠的 workaround（因 SELinux 域转换限制）。

#### 发现 4：communicate() elif 链 Bug

`communicate()` 的简单路径用 `elif` 链只能处理一个 pipe，双 pipe 时只读一个。需检查 `pipe_count` 后决定走简单路径还是复杂路径。

#### 发现 5：libintl_gettext 修复

修复 libintl/gettext 相关问题后，CJK 编解码模块全部编译成功（_multibytecodec, _codecs_kr/jp/cn/tw/hk/iso2022）。

### 9.3 C 扩展包测试结果

> ⚠️ **注意**：以下为早期估算数据，未经完整验证。C 扩展包已从 site-packages 卸载，实际兼容性受 libpython3.9.so 符号导出问题影响（P0 待解决）。验证后的数据见 `STATUS.md`。

| 扩展包 | 早期评估 | 说明 |
|--------|------|------|
| numpy | ⚠️ 待验证 | 需要 --enable-shared 修复后重测 |
| Pillow | ⚠️ 待验证 | |
| requests | ✅ Compatible | 纯 Python，依赖 urllib3/chardet |
| cryptography | ⚠️ 待验证 | 依赖 OpenSSL |
| pandas | ⚠️ 待验证 | 依赖 numpy/LAPACK |
| lxml | ⚠️ 待验证 | libxml2/libxslt 链接问题 |
| pyyaml | ⚠️ 待验证 | libyaml 编译问题 |
| psycopg2 | ⚠️ 待验证 | libpq 未安装 |

> **pip 版本**：当前 pip 20.2.3，可升级到 26.0.1（尚未执行）。

### 9.4 已知问题

- 🔴 **P0: libpython3.9.so 符号导出缺失**：`nm -D libpython3.9.so` 返回 0 个 text 符号，导致 greenlet/ujson/numpy 等包 import 时找不到 PyType_IsSubtype 等 C API。修复方式：重新编译 Python（--enable-shared），补丁无需修改。

---

## 十、Python 3.12 适配路线图

### 10.1 有利因素

Python 3.12+ 已做了多项改进，有利于鸿蒙适配：

| 3.12+ 变化 | 对鸿蒙的影响 | 备注 |
|-----------|:---:|------|
| `_posixsubprocess.c` 内联到 subprocess.py | ✅ 大利好 | 不再需要编译 C 扩展 |
| 更完善的 `posix_spawn` 路径 | ✅ | 可直接启用 |
| 移除 `distutils` | ✅ | 减少维护负担 |
| `venv` symlink 处理改进 | ⚠️ | 需确认是否覆盖 HMDFS |
| `__OHOS__` 可能已在 configure.ac 中 | ⚠️ | 需检查上游 |

### 10.2 仍需处理的问题（3.12 适配时）

| 问题 | 3.9 现状 | 3.12 预期 | 处理建议 |
|------|:---:|:---:|------|
| SELinux 限制 SDK 工具 | ✅ pipe 绕过 | 仍需 | 根本性限制，需 SELinux 策略调整 |
| Pipe 数据丢失 | ✅ 补丁 0020 已修复 | 已解决 | — |
| fd 0/1/2 socket | ✅ 补丁 0016 已实现 | 已解决 | — |
| multiprocessing fork 默认 | ✅ 补丁 0013 已实现 | 可能上游已修复 | 检查 3.12 源码 |
| /proc/self/fd 依赖 | ✅ 补丁 0017 已实现 | 已解决 | — |
| threading.get_native_id | ✅ 补丁 0012 已实现 | 可能上游已修复 | 检查 3.12 源码 |

### 10.3 建议的适配步骤

```
Step 1: 检查 Python 3.12 上游 configure.ac 对 HarmonyOS 的支持情况
Step 2: 尝试原生编译 Python 3.12（不应用任何 patch）
Step 3: 复用 subprocess-tests/ 中的 C 级测试验证系统调用能力
Step 4: 重点测试 subprocess 和 multiprocessing 模块
Step 5: 对比 3.9 的 patch 列表，识别哪些在 3.12 中已不需要
Step 6: 仅应用必要的鸿蒙适配 patch
Step 7: 运行完整测试套件
```

### 10.4 可复用的测试资产

| 资产 | 位置 | 用途 |
|------|------|------|
| 系统调用测试 | `subprocess-tests/test_syscalls.c` | 验证鸿蒙内核能力 |
| fork 测试 | `subprocess-tests/test_fork_clang.c` | 用 clang 作为锚点 |
| posix_spawn 测试 | `subprocess-tests/test_spawn*.c` | 测试 spawn 路径 |
| pipe 测试 | `subprocess-tests/test_pipe_simple.c` | pipe 基本功能 |
| Python subprocess 测试 | `subprocess-tests/test_subprocess_demo.py` | Python 层全面测试 |
| multiprocessing 测试 | `subprocess-tests/test_multiprocessing.py` | multiprocessing 验证 |

> **注意**：测试代码位于 `/storage/Users/currentUser/python/subprocess-tests/`，可直接复用于 Python 3.12。

---

## 十一、关键踩坑总结

### 11.1 构建阶段踩坑

| # | 踩坑 | 症状 | 解决 |
|---|------|------|------|
| 1 | echo 不能作为 subprocess 测试锚点 | echo 通过但 clang 失败 | **用 SDK 工具测试** |
| 2 | /tmp 只读 | configure 失败 | `export TMPDIR=$HOME/tmp` |
| 3 | libintl_gettext 缺失 | CJK 模块编译失败 | 安装 gettext 或修复 configure |
| 4 | ncurses 共享库冲突 | zsh 崩溃 | 用 `--without-shared` 编译静态库 |
| 5 | OpenSSL ARM64 asm bug | BAD_SIGNATURE | `no-asm` 编译 OpenSSL |

### 11.2 运行阶段踩坑

| # | 踩坑 | 症状 | 解决 |
|---|------|------|------|
| 6 | pipe 数据丢失 | 子进程输出 0 bytes | ✅ 补丁 0020 已修复（os.pipe + posix_spawn），无需临时文件 |
| 7 | fd 0/1/2 是 socket | 子进程 I/O 混乱 | dup2 到 /dev/null |
| 8 | communicate() elif 链 | 双 pipe 只读一个 | 检查 pipe_count |
| 9 | cleanup 关 read_fd | close 时报错 | cleanup 只删文件 |
| 10 | _posixsubprocess 硬依赖 | 缺失时模块不可用 | 纯 Python fallback |
| 11 | HMDFS 不支持 symlink | venv 创建失败 | try/except + makedirs 回退 |

### 11.3 通用复用经验

以下经验**不限于 Python**，适用于任何在鸿蒙上需要子进程交互的软件：

1. **Pipe 绕过 SELinux**：`system("cmd | cat")` 是 **SDK 工具执行场景** 下可靠的 workaround（因 SELinux 域转换限制）
2. **os.pipe() + posix_spawn**：补丁 0020 修复后 `os.pipe()` 在鸿蒙上可正常使用，无需临时文件替代方案
3. **fd 0/1/2 保护**：fork 后立即 dup2 到 /dev/null
4. **硬链接不支持**：用 `cp -p` 替代 `ln`
5. **symlink 可能不支持**：try/except OSError + makedirs 回退
6. **/tmp 只读**：用 `$HOME/tmp` 或 `$TMPDIR`
7. **musl BIND_NOW**：扩展模块/插件必须链接主程序库
8. **平台字符串含空格**：`uname -r` 返回 "HongMeng Kernel 1.11.0"

---

## 十二、相关文件索引

| 文件 | 用途 | 新增 |
|------|------|:---:|
| `README.md` | 本文件 — 主文档 | - |
| `patches/series` | 补丁序列 | - |
| `patches/0001~0020` | 20 个鸿蒙适配补丁 | - |
| `HARMONYOS_SUBPROCESS_GUIDE.md` | **子进程执行完整指南**（含 T0-T6 测试矩阵、C 扩展测试、POSIX spawn 分析） | ✅ v3.0 |
| `reports/UPSTREAM_ADAPTATION_ANALYSIS.md` | 上游合入方案 + 遗漏扫描 | - |
| `reports/MISSING_ADAPTATION_SCAN.md` | 全量遗漏扫描（P0~P2） | - |
| `tests/test_subprocess_compat.py` | 兼容层测试 | - |
| `scripts/package_python.sh` | 打包脚本 | - |

---

## 十三、版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-21 | 1.0 | 初始版本 |
| 2026-03-21 | 2.0 | 补丁详解完善，添加举一反三 |
| 2026-03-21 | 3.0 | 添加依赖关系、技术要点总结章节 |
| 2026-03-25 | 3.1 | 新增补丁 0011（venv symlink fallback）、统一测试数据 |
| 2026-03-25 | 3.2 | 全量适配分析：上游合入方案、遗漏扫描、pip 阻塞根因 |
| 2026-03-25 | 4.0 | **全量构建验证**：64 扩展模块编译、C 级 subprocess 调试、Pipe 数据丢失发现、fork_exec fallback、Python 3.12 路线图、踩坑总结 |
| 2026-03-26 | 4.2 | **P0 解决**：--enable-shared 重编译成功，libpython3.9.so 导出 1459 个 text 符号，make install 完成（72/72 导入）；移除 --host/--build（不欺骗构建系统）；移除 --with-openssl（pkg-config 已修复）；添加 CPPFLAGS/LDFLAGS（libintl 依赖） |

---

*维护者: OpenHarmony 社区*
--

*维护者: OpenHarmony 社区*
整参数；pipe 问题已修复；临时文件方案废弃；fork() 可用性确认；C 扩展测试结果补充；文档全面审计修正 |

---

*维护者: OpenHarmony 社区*
--

*维护者: OpenHarmony 社区*
