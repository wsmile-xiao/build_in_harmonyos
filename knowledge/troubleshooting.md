# 常见编译问题排查指南

## 快速诊断流程

```
编译失败 → 检查错误类型 → 查找对应解决方案 → 验证修复
```

## 问题分类索引

| 类别 | 常见问题 | 优先级 |
|------|----------|--------|
| [工具链问题](#1-工具链问题) | 找不到编译器、工具版本不对 | ⭐⭐⭐ |
| [环境问题](#2-环境问题) | 临时目录不可写、环境变量缺失 | ⭐⭐⭐ |
| [兼容性问题](#3-兼容性问题) | musl/glibc 差异、系统调用限制 | ⭐⭐ |
| [构建系统问题](#4-构建系统问题) | configure 失败、Makefile 错误 | ⭐⭐ |
| [链接问题](#5-链接问题) | 符号找不到、库加载失败 | ⭐⭐ |

---

## 1. 工具链问题

### 1.1 找不到 cc/c++

**现象**：
```
configure: error: C compiler cannot create executables
```

**原因**：PATH 中没有 cc 软链接

**解决**：
```bash
sudo ln -sf /data/service/hnp/bin/clang /usr/local/bin/cc
sudo ln -sf /data/service/hnp/bin/clang++ /usr/local/bin/c++
```

### 1.2 找不到 llvm-ar

**现象**：
```
ar: command not found
```

**原因**：使用了 GNU ar 而非 LLVM ar

**解决**：
```bash
export AR=llvm-ar
export RANLIB=llvm-ranlib
```

### 1.3 toybox 工具兼容性问题

**现象**：configure 生成的 Makefile 包含乱码

**原因**：toybox sed/expr 不支持复杂脚本

**解决**：编译安装 GNU coreutils 和 GNU sed
```bash
# 参考档案
archives/c/coreutils/9.10/
archives/s/sed/4.9/
```

---

## 2. 环境问题

### 2.1 临时目录不可写

**现象**：
```
configure: error: cannot create a temporary directory in /tmp
```

**原因**：鸿蒙 /tmp 是只读的

**解决**：
```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

### 2.2 找不到安装的库

**现象**：
```
configure: error: xxx library not found
```

**原因**：库路径未设置

**解决**：
```bash
export LIBRARY_PATH=$HOME/usr/local/lib:$LIBRARY_PATH
export C_INCLUDE_PATH=$HOME/usr/local/include:$C_INCLUDE_PATH
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
```

### 2.3 共享库加载失败

**现象**：
```
error while loading shared libraries: libxxx.so
```

**原因**：LD_LIBRARY_PATH 未设置

**解决**：
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

---

## 3. 兼容性问题

### 3.1 musl 与 glibc 差异

**现象**：
```
error: incomplete definition of type 'struct _IO_FILE'
```

**原因**：musl 的 FILE 是不透明类型

**解决**：使用条件编译
```c
#if defined(__OHOS__) || (defined(__linux__) && !defined(__GLIBC__))
  // musl 兼容代码
#endif
```

### 3.2 fstat 对管道返回 EACCES

**现象**：
```
cat: standard output: Permission denied
```

**原因**：鸿蒙限制对管道的 fstat 调用

**解决**：
```c
#ifdef __OHOS__
if (errno == EACCES || errno == EPERM) {
    st.st_blksize = 4096;
    st.st_mode = S_IFIFO;
    return 0;
}
#endif
```

### 3.3 SELinux 域转换限制

**现象**：子进程执行 SDK 工具失败（exit code 1，无输出）

**原因**：SELinux 域转换限制

**解决**：使用管道语法
```python
# Python
import os
os.system("clang --version | cat")  # 成功
```

### 3.4 libintl_gettext 链接失败

**现象**：
```
ld.lld: error: undefined symbol: libintl_gettext
ld.lld: error: undefined symbol: libintl_bindtextdomain
```

**原因**：GNU 软件默认启用 NLS（国际化），依赖 gettext 库（libintl），鸿蒙系统未预装。

**解决方案**：
```bash
./configure --disable-nls
```

**涉及软件**：gdbm、tar 等大多数 GNU 软件

---

## 4. 构建系统问题

### 4.1 config.guess 无法识别系统

**现象**：
```
configure: error: cannot guess build type
```

**原因**：config.guess 未添加 HarmonyOS 支持

**解决**：应用补丁修改 config.guess
```bash
patch -p1 < archives/l/libffi/3.4.4/patches/0001-port-for-ohos.patch
```

### 4.2 三元组验证失败

**现象**：
```
configure: error: invalid triplet aarch64-unknown-linux-ohos
```

**原因**：config.sub 未添加 ohos 支持

**解决**：修改 config.sub
```bash
# 在 android-linux 后添加
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

### 4.3 构建目录路径包含空格

**现象**：
```
No module named '_sysconfigdata__ohos_aarch64'
```

**原因**：平台字符串包含空格

**解决**：修改 sysconfig.py
```python
elif osname[:9] == "harmonyos":
    return "%s-%s" % (osname, machine)  # 跳过 release
```

---

## 5. 链接问题

### 5.1 符号找不到（BIND_NOW）

**现象**：
```
ImportError: symbol not found
```

**原因**：musl 默认 BIND_NOW，扩展模块未链接主库

**解决**：修改 LDSHARED
```makefile
LDSHARED = $(CC) -shared -L. -lpython$(VERSION)
```

### 5.2 静态库链接共享库失败

**现象**：
```
relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used; recompile with -fPIC
```

**原因**：静态库未用 -fPIC 编译

**解决**：
```bash
export CFLAGS="-fPIC -O2"
# 重新编译静态库
```

### 5.3 OpenSSL BAD_SIGNATURE

**现象**：
```
ssl.SSLError: [SSL: BAD_SIGNATURE] bad signature
```

**原因**：ARM64 汇编优化代码 bug

**解决**：使用 no-asm 编译
```bash
./Configure ... no-asm
```

### 5.4 用户编译的共享库与系统库冲突

**现象**：安装用户编译的 ncurses 共享库后，系统 zsh 崩溃，所有终端不可用。

**原因**：用户编译的共享库（如 libncursesw.so.6.4）安装到系统路径后，zsh 等系统工具的动态链接被劫持，且符号链接可能不完整。

**解决方案**：
```bash
# 推荐：只编译静态库
./configure --without-shared

# 如必须用共享库：确保符号链接完整
ls -la $HOME/usr/local/lib/libncursesw*
# 应该看到：libncursesw.so.6 → libncursesw.so.6.4
```

**预防**：所有用户编译的库优先使用静态链接。

### 5.5 动态库符号链接无法被用户进程加载

**现象**：软件编译安装成功，但运行时报 `error while loading shared libraries`，即使 .so 文件存在且路径正确。

**原因**：鸿蒙 SELinux 限制了用户进程加载某些上下文的 .so 符号链接（与 E018 "创建失败"不同，这里是"已存在但无法加载"）。

**解决方案**：
```bash
# 方案1：使用静态链接（推荐）
./configure --enable-static --disable-shared LDFLAGS=-static

# 方案2：设置 SELinux 上下文
chcon u:object_r:toybox_exec:s0 /path/to/libxxx.so
```

**涉及软件**：file 5.45（libmagic）、htop 3.4.1

---

## 6. 诊断命令

```bash
# 检查系统
uname -a

# 检查编译器
clang --version
which clang llvm-ar

# 检查环境变量
echo $CC $CFLAGS $LDFLAGS

# 检查库
llvm-readelf -d /path/to/binary | grep NEEDED

# 检查符号
llvm-nm /path/to/library

# 检查 SELinux
ls -Z /path/to/file
getfattr -d -m - /path/to/file
```

---

## 7. 进程意外退出（exit code 159 = SIGSYS）

### 症状

- 程序运行中突然退出，无错误信息
- Exit code 159（128 + signal 31 = SIGSYS）
- 可能产生 core dump

### 排查步骤

1. **确认信号编号**：
   ```bash
   echo $((159 - 128))  # → 31 = SIGSYS
   ```

2. **检查是否调用了未实现 syscall**：常见触发 syscall 包括 `setreuid`、`setregid`、`chroot`、`clock_settime`

3. **Python 快速复现**：
   ```bash
   python3 -c "import os; os.setreuid(0,0)"  # exit 159
   ```

4. **解决方案**：在 C 源码中添加 `#ifdef __OHOS__` 守卫，在 syscall 调用前返回 ENOSYS

### ⚠️ 注意

- `sigaction(SIGSYS, handler)` 对 `setreuid`/`setregid` **无效**——handler 不会触发
- **必须在源码层面拦截**，不能依赖信号处理
- 详细技术分析见 `error-patterns.md` E051
- 适配模式见 `ohos-adaptation-patterns.md` "未实现 syscall 提前拦截"

---

## 8. 子进程 exit code 127（找不到 libpython3.9.so）

### 症状

- `subprocess.Popen([sys.executable, ...])` 启动的子进程返回 exit code 127
- 不设 `LD_LIBRARY_PATH` 时直接运行 `python3.9` 也报错
- 错误信息：`Error loading shared library libpython3.9.so.1.0: No such file or directory`

### 排查步骤

1. **确认是 RPATH 问题**：
   ```bash
   unset LD_LIBRARY_PATH && python3.9 -c "print(1)"  # 失败?
   LD_LIBRARY_PATH=/path/to/python python3.9 -c "print(1)"  # 成功?
   ```

2. **检查是否有 RPATH**：
   ```bash
   # musl 环境下用 objdump 检查
   # 看 python3.9 是否有 RPATH/RUNPATH 段
   ```

3. **解决方案**：重新编译/链接时加 `-Wl,-rpath,$ORIGIN`
   - 或修改 `Makefile.pre.in` 的 `LINKFORSHARED`（补丁 0043）
   - 或临时重新链接：`clang -Wl,-rpath,$ORIGIN -o python3.9 Programs/python.o -L. -lpython3.9 ...`

### ⚠️ 注意

- 鸿蒙使用 musl ld.so，**不会**自动搜索 `$ORIGIN`
- glibc 发行版通常有默认的 `$ORIGIN` 搜索，鸿蒙没有
- 这影响所有通过 subprocess 启动 Python 子进程的场景
- 详细技术分析见 `error-patterns.md` E052

---

## 9. 获取帮助

1. 查看软件档案：`archives/{首字母}/{软件名}/{版本}/README.md`
2. 查看问题模式：`knowledge/error-patterns.md`
3. 查看环境特性：`knowledge/environment.md`
4. 检查缺失工具：`MISSING_TOOLS.md`