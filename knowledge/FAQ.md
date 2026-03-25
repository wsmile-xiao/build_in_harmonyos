# 鸿蒙编译常见问题快速问答 (FAQ)

本文档提供鸿蒙系统上编译软件的常见问题快速解答。

---

## 一、环境配置

### Q1: 如何设置编译环境变量？

```bash
# 添加到 ~/.zshrc
export CC="clang"
export CXX="clang++"
export AR="llvm-ar"
export RANLIB="llvm-ranlib"
export NM="llvm-nm"
export STRIP="llvm-strip"
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"
export LDFLAGS="-L$HOME/usr/local/lib"
export TMPDIR=$HOME/tmp
export PATH=$HOME/usr/local/bin:$PATH
```

### Q2: 为什么 /tmp 不可写？

鸿蒙系统的 `/tmp` 以只读方式挂载（erofs）。

**解决**：设置 `TMPDIR` 环境变量：
```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

### Q3: 如何检查编译器是否正确？

```bash
# 检查 clang
clang --version
# 应显示: clang version 15.0.4

# 检查预定义宏
clang -dM -E - < /dev/null | grep OHOS
# 应看到: #define __OHOS__ 1
```

---

## 二、编译错误

### Q4: configure 提示找不到 cc 命令？

```
configure: error: C compiler cannot create executables
cc: command not found
```

**解决**：创建 cc 软链接：
```bash
ln -sf $(which clang) $HOME/usr/local/bin/cc
ln -sf $(which clang++) $HOME/usr/local/bin/c++
```

### Q5: configure 提示无法猜测构建类型？

```
configure: error: cannot guess build type
```

**原因**：config.guess 未添加 HarmonyOS 支持。

**解决**：应用补丁修改 config.guess，参考 `knowledge/autotools-patterns.md`。

### Q6: 编译时找不到 pthread？

```
undefined reference to 'pthread_create'
```

**解决**：
```bash
export CFLAGS="-pthread $CFLAGS"
# 或
export LDFLAGS="-lpthread $LDFLAGS"
```

### Q7: 静态库链接共享库失败？

```
relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used; recompile with -fPIC
```

**解决**：重新编译静态库，添加 `-fPIC`：
```bash
export CFLAGS="-fPIC -O2"
make clean && make && make install
```

---

## 三、链接错误

### Q8: Python 扩展模块符号找不到？

```
ImportError: symbol not found: _PyType_Name
```

**原因**：musl 默认 BIND_NOW，扩展模块未链接 libpython。

**解决**：修改 LDSHARED 添加 `-lpython`：
```makefile
LDSHARED = $(CC) -shared -L. -lpython$(VERSION)
```

详见 `knowledge/musl-compat.md`。

### Q9: OpenSSL BAD_SIGNATURE 错误？

```
ssl.SSLError: [SSL: BAD_SIGNATURE] bad signature
```

**原因**：OpenSSL ARM64 汇编优化有 bug。

**解决**：使用 `no-asm` 重新编译 OpenSSL：
```bash
./Configure --prefix=$HOME/usr/local no-asm
```

### Q10: 找不到已安装的库？

```
configure: error: xxx library not found
```

**解决**：确保 `PKG_CONFIG_PATH` 包含库的 .pc 文件所在目录：
```bash
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
```

> ⚠️ **不要设置 `C_INCLUDE_PATH`**：该变量会与 pkg-config 冲突，导致 `pkg-config --cflags` 返回空。详见 `environment.md` §11。

如果库没有提供 .pc 文件，可通过构建系统变量指定：
```bash
# CMake 项目
cmake .. -DCMAKE_PREFIX_PATH=$HOME/usr/local

# Autotools 项目
./configure --prefix=$HOME/usr/local CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib"
```

---

## 四、运行时错误

### Q11: pkg-config --cflags 返回空字符串？

```bash
$ pkg-config --cflags openssl
（空）

# 但 .pc 文件明确写了 Cflags
$ cat /path/to/openssl.pc
  Cflags: -I${includedir}
```

**原因**：`C_INCLUDE_PATH` 环境变量包含了 .pc 文件中 `includedir` 的路径。pkg-config 会将 `C_INCLUDE_PATH` 中的路径视为"系统目录"并自动过滤掉匹配的 `-I` 标志。

**排查**：
```bash
# 检查是否设置了 C_INCLUDE_PATH
echo $C_INCLUDE_PATH

# 用 --debug 确认
pkg-config --debug --cflags openssl 2>&1 | grep "Removing"
```

**解决**：
```bash
# 方案 1（推荐）：从 .zshrc 中移除 C_INCLUDE_PATH
unset C_INCLUDE_PATH
unset CPLUS_INCLUDE_PATH

# 方案 2：临时允许系统 Cflags
PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1 pkg-config --cflags openssl
```

详见 `environment.md` §11。

### Q12: 子进程执行 SDK 工具失败？

```python
subprocess.run(['clang', '--version'])  # returncode: 1, 无输出
```

**原因**：SELinux 域转换限制。

**解决**：使用管道语法绕过：
```python
os.system("clang --version | cat")  # 成功
```

详见 `knowledge/harmonyos-specifics.md`。

### Q12: cat/head 等命令报 Permission denied？

```
cat: standard output: Permission denied
```

**原因**：鸿蒙限制对管道的 `fstat()` 调用。

**解决**：使用修复的 GNU coreutils，参考 `archives/c/coreutils/9.10/`。

### Q13: 软链接无法访问或创建？

```
ln: cannot create symbolic link: Permission denied
```

**解决**：使用 `cp` 复制替代 `ln -s`：
```bash
cp source.txt link.txt
```

### Q14: 共享库加载失败？

```
error while loading shared libraries: libxxx.so
```

**解决**：
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

---

## 五、工具问题

### Q15: toybox expr/sed 有什么问题？

| 工具 | 问题 | 影响 |
|------|------|------|
| expr | 不支持复合正则 `\|` | autotools 项目失败 |
| sed | 不支持复杂脚本 | configure 生成乱码 |

**解决**：安装 GNU 工具：
```bash
# GNU coreutils (包含 expr)
# 参考: archives/c/coreutils/9.10/

# GNU sed
# 参考: archives/s/sed/4.9/

export PATH=$HOME/usr/local/bin:$PATH
```

### Q16: 如何检查使用的是哪个工具？

```bash
# 查看命令路径
which sed expr

# 查看版本
sed --version    # GNU sed 显示版本，toybox 不显示
expr --version   # GNU expr 显示版本

# 检查 toybox
ls -la $(which sed) | grep toybox
```

---

## 六、构建系统

### Q17: 如何识别软件使用的构建系统？

```bash
# Autotools
[ -f "configure" ] && echo "Autotools"

# CMake
[ -f "CMakeLists.txt" ] && echo "CMake"

# OpenSSL 风格
[ -f "Configure" ] && echo "Custom-Perl"

# Meson
[ -f "meson.build" ] && echo "Meson"

# Makefile
[ -f "Makefile" ] && echo "Makefile"
```

### Q18: Autotools 项目如何适配 HarmonyOS？

修改 `config.guess` 和 `config.sub`：

1. 在 config.guess 添加 `__OHOS__` 检测
2. 在 config.guess 添加 `HarmonyOS` 系统识别
3. 在 config.sub 添加 `ohos-linux` 支持

详见 `knowledge/autotools-patterns.md`。

### Q20: CMake 项目如何适配 HarmonyOS？

```bash
cmake -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      ..
```

### Q20: make clean 后重新编译失败？

**原因**：`make clean` 不完全，残留变量导致问题。

**解决**：
```bash
# 使用 distclean
make distclean

# 或删除 build 目录
rm -rf build

# 然后重新配置编译
./configure --prefix=$HOME/usr/local
make
```

---

## 七、Python 相关

### Q22: 如何编译 Python 扩展模块？

详见 `knowledge/python-extensions.md`。

基本模板：
```bash
# 编译
clang -fPIC -I./Include -I. -c module.c -o module.o

# 链接（必须包含 libpython）
clang -shared -L. -lpython3.9 module.o -o module.so
```

### Q22: curses 模块编译失败？

```
error: unknown type name 'cchar_t'
```

**解决**：添加 `_XOPEN_SOURCE_EXTENDED` 宏：
```bash
clang -fPIC -D_XOPEN_SOURCE_EXTENDED \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    -c Modules/_cursesmodule.c -o _curses.o
```

### Q23: Python 测试套件大量失败？

**原因**：
- 共享库路径未设置
- 签名机制限制
- 系统能力缺失（PTY、locale）

**解决**：
```bash
# 安装后再测试
make install
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
python3.9 -m test -x test_openpty test_pty test_locale
```

---

## 八、调试技巧

### Q24: 如何追踪 configure 执行过程？

```bash
# 使用 bash -x
bash -x ./configure --prefix=$HOME/usr/local 2>&1 | tee trace.log

# 查看变量赋值
grep "^[+] ac_" trace.log
```

### Q25: 如何检查进程卡住？

```bash
# 找到卡住的进程
ps aux | grep configure

# 查看进程命令
cat /proc/<pid>/cmdline | tr '\0' ' '

# 查看调用栈
cat /proc/<pid>/stack
```

### Q26: 如何验证补丁是否正确？

```bash
# 干跑测试
patch -p1 --dry-run < patch.diff

# 检查修改内容
grep -n "HarmonyOS\|__OHOS__" config.guess
```

---

## 九、快速参考

### 环境变量速查

| 变量 | 推荐值 | 用途 |
|------|--------|------|
| CC | clang | C 编译器 |
| CXX | clang++ | C++ 编译器 |
| AR | llvm-ar | 归档工具 |
| RANLIB | llvm-ranlib | 库索引 |
| CFLAGS | -fPIC -O2 | 编译标志 |
| TMPDIR | $HOME/tmp | 临时目录 |
| PATH | $HOME/usr/local/bin:$PATH | 命令路径 |
| LD_LIBRARY_PATH | $HOME/usr/local/lib | 共享库路径 |

### 三元组格式

| 架构 | 三元组 |
|------|--------|
| ARM64 | aarch64-unknown-linux-ohos |
| ARM32 | arm-unknown-linux-ohos |
| x86_64 | x86_64-unknown-linux-ohos |

### 知识文件索引

| 文件 | 内容 |
|------|------|
| environment.md | 系统环境特性 |
| build-systems.md | 构建系统识别 |
| troubleshooting.md | 问题排查流程 |
| error-patterns.md | 44种错误模式 |
| musl-compat.md | musl/glibc 差异 |
| python-extensions.md | Python 扩展编译 |
| autotools-patterns.md | Autotools 适配 |
| harmonyos-specifics.md | 鸿蒙特异性 |
| dependencies.md | 依赖关系图 |

---

*文档版本: 1.1*  
*最后更新: 2026-03-26*