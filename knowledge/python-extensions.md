# Python 扩展模块编译指南

在鸿蒙系统上编译 Python 扩展模块需要特殊处理，本文档总结了常见问题和解决方案。

## 1. 核心问题：musl BIND_NOW

### 1.1 问题现象

```
ImportError: Error relocating _struct.so: _PyType_Name: symbol not found
```

### 1.2 根因分析

musl 默认启用 BIND_NOW，要求所有符号在加载时解析。扩展模块的 NEEDED 通常只有 libc.so，缺少 libpython，导致 Python API 符号无法解析。

### 1.3 验证命令

```bash
# 查看扩展模块动态段
llvm-readelf -d module.so | grep -E "NEEDED|BIND"

# 错误输出:
#   NEEDED: libc.so           # 只有 libc
#   FLAGS: BIND_NOW           # musl 默认

# 正确输出:
#   NEEDED: libpython3.9.so.1.0   # 有 libpython
#   NEEDED: libc.so
```

### 1.4 解决方案

修改 `Makefile.pre.in`，在 `LDSHARED` 中添加 libpython：

```makefile
# 修改前
LDSHARED=    $(CC) -shared $(PY_LDFLAGS)

# 修改后
LDSHARED=    $(CC) -shared $(PY_LDFLAGS) -L. -lpython$(LDVERSION)
```

**⚠️ 关键：BLDSHARED ≠ LDSHARED**

```makefile
# BLDSHARED 用于构建 libpython.so，不能包含 -lpython（循环依赖）
BLDSHARED='$(CC) -shared'

# LDSHARED 用于构建扩展模块，必须包含 -lpython
LDSHARED='$(CC) -shared -L. -lpython$(LDVERSION)'
```

---

## 2. 扩展模块编译通用模板

### 2.1 基本编译命令

```bash
# 通用编译标志
CFLAGS="-fPIC -DPy_BUILD_CORE_MODULE -I./Include/internal -I./Include -I. -I$HOME/usr/local/include"

# 链接标志（必须包含 libpython）
LDFLAGS="-shared -L. -lpython3.9"

# 编译单个源文件
clang $CFLAGS -c Modules/xxxmodule.c -o build/xxx.o

# 链接生成 .so
clang $LDFLAGS build/xxx.o -o xxx.so
```

### 2.2 需要 Py_BUILD_CORE_MODULE 的模块

以下模块需要添加 `-DPy_BUILD_CORE_MODULE`：

| 模块 | 原因 |
|------|------|
| math, cmath | 使用 `pycore_fileutils.h` |
| _sha256, _sha512 | 使用 `pycore_byteswap.h` |
| _sha3, _blake2 | 使用内部头文件 |
| _md5, _sha1 | 同上 |

```bash
clang -fPIC -DPy_BUILD_CORE_MODULE -I./Include/internal -I./Include -I. -c Modules/sha256module.c -o sha256.o
```

### 2.3 需要额外链接的模块

| 模块 | 额外链接 | 说明 |
|------|----------|------|
| math, cmath | `Modules/_math.o -lm` | 数学辅助函数 |
| pyexpat, _elementtree | `build/xmlparse.o build/xmlrole.o build/xmltok.o ...` | expat 解析器 |
| _blake2 | `build/blake2b.o build/blake2s.o build/blake2module.o` | 多文件链接 |

---

## 3. 常见问题及解决方案

### 3.1 问题：curses 模块编译失败（宽字符函数未定义）

**现象**：
```
error: unknown type name 'cchar_t'; did you mean 'wchar_t'?
error: call to undeclared function 'setcchar'
```

**原因**：ncurses 的宽字符函数需要 `_XOPEN_SOURCE_EXTENDED` 宏。

**解决**：

修改 `setup.py`：

```python
# 原代码
if MACOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))

# 修改后
if MACOS or OHOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))
```

#### ⭐ 重要：鸿蒙系统必须使用 ncurses 静态库

**背景**：鸿蒙系统 /bin/zsh 依赖 libncursesw.so.6，用户编译的共享库可能与之冲突。

**风险**：如果共享库冲突，可能导致 Shell 崩溃，所有终端无法使用！

**解决方案**：编译 ncurses 时使用 `--without-shared` 生成静态库：

```bash
# 编译 ncurses 静态库（推荐）
./configure --prefix=$HOME/usr/local \
    --without-shared \        # ⭐ 关键：不生成共享库
    --enable-widec \
    --enable-overwrite \      # 头文件安装到顶层目录
    --without-debug \
    --without-profile \
    --without-ada \
    --without-manpages \
    --without-progs \
    --without-tests \
    --without-cxx \
    --without-cxx-binding

make && make install
```

**安装后验证**：
```bash
# 应该只有静态库
ls -la $HOME/usr/local/lib/libncursesw.a   # ✅ 存在
ls -la $HOME/usr/local/lib/libncursesw.so  # ❌ 不应该存在
```

#### 手动编译 curses 模块（静态链接）

```bash
# 编译命令
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \   # ⭐ 关键：启用宽字符函数
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_cursesmodule.c \
    -o _cursesmodule.o

# 链接命令（静态链接 libncursesw.a）
clang -shared -L. -lpython3.9 \
    _cursesmodule.o \
    $HOME/usr/local/lib/libncursesw.a \
    -o _curses.so
```

#### setup.py 路径硬编码问题

**问题**：setup.py 中可能硬编码了 ncurses 头文件路径（如 `/usr/include/ncursesw`）。

**解决**：修改 setup.py 确保使用正确的路径：

```python
# 查找 ncurses 头文件
if platform.startswith('harmony') or platform.startswith('ohos'):
    # 鸿蒙系统：使用用户安装路径
    curses_inc_paths = [
        os.path.join(os.path.expanduser('~'), 'usr', 'local', 'include'),
        os.path.join(os.path.expanduser('~'), 'usr', 'local', 'include', 'ncursesw'),
    ]
```

**说明**：
- `-D_XOPEN_SOURCE_EXTENDED` 宏启用 ncurses 宽字符函数（setcchar, wget_wch 等）
- 静态链接避免运行时库冲突，更稳定
- terminfo 数据库缺失不影响 Python curses 模块编译，Python 会使用系统自带的 terminfo

### 3.2 问题：CAN socket 宏未定义

**现象**：
```
error: use of undeclared identifier 'CAN_RAW_FD_FRAMES'
error: use of undeclared identifier 'CAN_RAW_JOIN_FILTERS'
```

**解决**：修改 `pyconfig.h` 禁用这些宏：

```bash
sed -i 's/^#define HAVE_LINUX_CAN_RAW_FD_FRAMES 1/\/\* #undef HAVE_LINUX_CAN_RAW_FD_FRAMES \*\//' pyconfig.h
sed -i 's/^#define HAVE_LINUX_CAN_RAW_JOIN_FILTERS 1/\/\* #undef HAVE_LINUX_CAN_RAW_JOIN_FILTERS \*\//' pyconfig.h
```

### 3.3 问题：平台字符串包含空格导致构建目录异常

**现象**：
```
No module named '_sysconfigdata__ohos_aarch64_linux_ohos'
```

**原因**：`sysconfig.get_platform()` 返回含空格的字符串。

**解决**：修改 `Lib/sysconfig.py`：

```python
elif osname[:9] == "harmonyos" or osname[:4] == "ohos":
    # HarmonyOS: release contains spaces, skip it
    return "%s-%s" % (osname, machine)
```

### 3.4 问题：子进程执行 SDK 工具失败

**现象**：
```python
subprocess.run(['clang', '--version'])  # returncode: 1, 无输出
```

**原因**：SELinux 域转换限制。

**解决**：使用管道语法：

```python
os.system("clang --version | cat")  # 成功
```

详见 `knowledge/harmonyos-specifics.md` 第7节。

---

## 4. expat 内置依赖编译示例

```bash
# 编译 expat 库
for f in Modules/expat/*.c; do
    clang -fPIC -DHAVE_EXPAT_CONFIG_H=1 -DXML_POOR_ENTROPY=1 \
          -I./Modules/expat -I./Include -c "$f" -o build/$(basename $f .c).o
done

# 编译 pyexpat
clang -fPIC -DHAVE_EXPAT_CONFIG_H=1 -I./Modules/expat -I./Include -I. \
      -c Modules/pyexpat.c -o build/pyexpat.o

# 链接
clang -shared -L. -lpython3.9 build/pyexpat.o build/xmlparse.o build/xmlrole.o \
      build/xmltok.o build/xmltok_impl.o build/xmltok_ns.o -o pyexpat.so
```

---

## 5. 快速编译脚本

```bash
#!/bin/bash
# compile_python_module.sh - 快速编译 Python 扩展模块

MODULE_NAME=$1
SOURCE_FILE=$2
EXTRA_CFLAGS="${3:-}"
EXTRA_OBJS="${4:-}"
NEEDS_CORE="${5:-}"

CFLAGS="-fPIC -I./Include/internal -I./Include -I. -I$HOME/usr/local/include"
LDFLAGS="-shared -L. -lpython3.9"

if [ "$NEEDS_CORE" = "yes" ]; then
    CFLAGS="$CFLAGS -DPy_BUILD_CORE_MODULE"
fi

# 编译
clang $CFLAGS $EXTRA_CFLAGS -c "$SOURCE_FILE" -o build/${MODULE_NAME}.o

# 链接
clang $LDFLAGS build/${MODULE_NAME}.o $EXTRA_OBJS -o ${MODULE_NAME}.so

echo "编译完成: ${MODULE_NAME}.so"
```

**使用示例**：

```bash
# 基本模块
./compile_python_module.sh _struct Modules/_struct.c

# 需要 BUILD_CORE 的模块
./compile_python_module.sh _sha256 Modules/sha256module.c "" "" yes

# 需要额外链接的模块
./compile_python_module.sh math Modules/mathmodule.c "" "Modules/_math.o -lm" yes
```

---

## 6. 验证扩展模块

```bash
# 检查链接
llvm-readelf -d module.so | grep NEEDED

# 应该看到:
#   NEEDED: libpython3.9.so.1.0
#   NEEDED: libc.so

# 测试导入
python3.9 -c "import module; print('OK')"
```

---

## 7. 详细编译案例

### 7.1 curses 和 _curses_panel 模块（静态链接）

**重要经验**：在鸿蒙系统上编译 curses 模块，建议使用**静态链接**，避免共享库问题影响系统稳定性。

#### 问题背景

1. **setup.py 路径硬编码**：Python 的 setup.py 中硬编码了 `/usr/include/ncursesw` 路径，在鸿蒙上不存在
2. **宽字符函数未定义**：缺少 `-D_XOPEN_SOURCE_EXTENDED` 宏导致 `cchar_t`、`setcchar` 等未定义
3. **系统崩溃风险**：创建共享库符号链接可能导致系统 shell (zsh) 崩溃

#### 解决方案：编译 ncurses 静态库

```bash
cd ncurses-6.4
./configure --prefix=$HOME/usr/local \
    --without-shared \          # 关键：只生成静态库
    --without-cxx \
    --without-cxx-binding \
    --enable-widec \            # 启用宽字符支持
    --enable-overwrite \        # 头文件安装到顶层
    --without-debug \
    --without-profile \
    --without-ada \
    --without-manpages \
    --without-progs \
    --without-tests
make -j$(nproc)
make install.libs
```

#### 手动编译 curses 模块

```bash
# 编译 _cursesmodule.c
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \   # ⭐ 关键：启用宽字符扩展
    -D_XOPEN_SOURCE=600 \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_cursesmodule.c \
    -o _cursesmodule.o

# 静态链接创建 _curses.so
clang -shared -L. -lpython3.9 \
    _cursesmodule.o \
    $HOME/usr/local/lib/libncursesw.a \   # 静态库
    -o _curses.so

# 编译 _curses_panel（类似）
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_curses_panel.c \
    -o _curses_panel.o

clang -shared -L. -lpython3.9 \
    _curses_panel.o \
    $HOME/usr/local/lib/libpanelw.a \
    $HOME/usr/local/lib/libncursesw.a \
    -o _curses_panel.so
```

#### 关键编译选项说明

| 选项 | 作用 |
|------|------|
| `-DHAVE_NCURSESW=1` | 指定使用 ncurses 宽字符版本 |
| `-D_XOPEN_SOURCE_EXTENDED` | 启用 X/Open 宽字符扩展函数（cchar_t、setcchar 等） |
| `-D_XOPEN_SOURCE=600` | 设置 X/Open 标准版本 |

**⚠️ 缺少 `-D_XOPEN_SOURCE_EXTENDED` 会导致 `cchar_t` 等类型未定义！**

#### 静态链接 vs 动态链接

| 方式 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **静态链接** | 不影响系统；无运行时依赖；更稳定 | 文件较大；更新需重新编译 | ⭐⭐⭐ 推荐 |
| **动态链接** | 文件小；多程序共享；更新方便 | 可能影响系统；需正确配置库路径 | ⚠️ 有风险 |

---

### 7.2 math 和 cmath 模块

**问题**：`_Py_log1p` 等数学辅助函数找不到。

**原因**：这些函数定义在 `Modules/_math.c`，math/cmath 模块需要链接 `_math.o`。

**编译命令**：

```bash
# math 模块
clang -fPIC -DPy_BUILD_CORE_MODULE \
    -I./Include -I./Include/internal -I. \
    -c Modules/mathmodule.c -o math.o

clang -shared -L. -lpython3.9 \
    math.o Modules/_math.o -lm \
    -o math.so

# cmath 模块
clang -fPIC -DPy_BUILD_CORE_MODULE \
    -I./Include -I./Include/internal -I. \
    -c Modules/cmathmodule.c -o cmath.o

clang -shared -L. -lpython3.9 \
    cmath.o Modules/_math.o -lm \
    -o cmath.so
```

**关键点**：
- 必须添加 `-DPy_BUILD_CORE_MODULE`
- 必须链接 `Modules/_math.o`
- 必须添加 `-lm`

### 7.2 _ssl 模块

**问题**：HTTPS 连接报 `BAD_SIGNATURE` 错误。

**原因**：OpenSSL ARM64 汇编优化有 bug，需要用 `no-asm` 编译 OpenSSL。

**编译命令**：

```bash
# 确保 OpenSSL 已用 no-asm 编译
# 参考: archives/o/openssl/1.1.1w/

# 编译 _ssl 模块
clang -fPIC -I./Include -I$HOME/usr/local/include \
    -c Modules/_ssl.c -o _ssl.o

# 链接（关键：必须链接 libssl 和 libcrypto）
clang -shared -L. -lpython3.9 \
    -L$HOME/usr/local/lib -lssl -lcrypto \
    _ssl.o -o _ssl.so

# 验证链接
llvm-readelf -d _ssl.so | grep NEEDED
# 应该看到: libssl.so.1.1, libcrypto.so.1.1
```

### 7.3 expat 相关模块（pyexpat, _elementtree）

**问题**：需要编译 expat 内置库。

**编译命令**：

```bash
# 1. 编译 expat 库（Python 内置版本）
for f in Modules/expat/*.c; do
    clang -fPIC -DHAVE_EXPAT_CONFIG_H=1 -DXML_POOR_ENTROPY=1 \
          -I./Modules/expat -I./Include \
          -c "$f" -o build/$(basename $f .c).o
done

# 2. 编译 pyexpat
clang -fPIC -DHAVE_EXPAT_CONFIG_H=1 \
    -I./Modules/expat -I./Include -I. \
    -c Modules/pyexpat.c -o pyexpat.o

# 3. 链接
clang -shared -L. -lpython3.9 \
    pyexpat.o build/xmlparse.o build/xmlrole.o \
    build/xmltok.o build/xmltok_impl.o build/xmltok_ns.o \
    -o pyexpat.so

# 4. 编译 _elementtree（类似）
clang -fPIC -DHAVE_EXPAT_CONFIG_H=1 \
    -I./Modules/expat -I./Include -I. \
    -c Modules/_elementtree.c -o _elementtree.o

clang -shared -L. -lpython3.9 \
    _elementtree.o build/xmlparse.o build/xmlrole.o \
    build/xmltok.o build/xmltok_impl.o build/xmltok_ns.o \
    -o _elementtree.so
```

### 7.4 _blake2 模块

**问题**：多文件链接。

**编译命令**：

```bash
# 编译 blake2 实现
clang -fPIC -DPy_BUILD_CORE_MODULE \
    -I./Include/internal -I./Include -I. \
    -c Modules/_blake2/blake2b.c -o blake2b.o

clang -fPIC -DPy_BUILD_CORE_MODULE \
    -I./Include/internal -I./Include -I. \
    -c Modules/_blake2/blake2s.c -o blake2s.o

clang -fPIC -DPy_BUILD_CORE_MODULE \
    -I./Include/internal -I./Include -I. \
    -c Modules/_blake2/blake2module.c -o blake2module.o

# 链接
clang -shared -L. -lpython3.9 \
    blake2b.o blake2s.o blake2module.o \
    -o _blake2.so
```

### 7.5 _hashlib 模块（依赖 OpenSSL）

**编译命令**：

```bash
clang -fPIC -I./Include -I$HOME/usr/local/include \
    -c Modules/_hashopenssl.c -o _hashopenssl.o

clang -shared -L. -lpython3.9 \
    -L$HOME/usr/local/lib -lcrypto \
    _hashopenssl.o -o _hashlib.so
```

### 7.6 _ctypes 模块（依赖 libffi）

**编译命令**：

```bash
# 确保 libffi 已安装
# 参考: archives/l/libffi/3.4.4/

clang -fPIC -I./Include -I$HOME/usr/local/include \
    -c Modules/_ctypes/_ctypes.c -o _ctypes.o
clang -fPIC -I./Include -I$HOME/usr/local/include \
    -c Modules/_ctypes/callbacks.c -o callbacks.o
clang -fPIC -I./Include -I$HOME/usr/local/include \
    -c Modules/_ctypes/callproc.c -o callproc.o
clang -fPIC -I./Include -I$HOME/usr/local/include \
    -c Modules/_ctypes/stgdict.c -o stgdict.o

clang -shared -L. -lpython3.9 \
    -L$HOME/usr/local/lib -lffi \
    _ctypes.o callbacks.o callproc.o stgdict.o \
    -o _ctypes.so
```

---

## 8. 批量编译脚本

```bash
#!/bin/bash
# compile_all_extensions.sh - 批量编译 Python 扩展模块

PYTHON_VERSION="3.9"
PREFIX="$HOME/usr/local"

# 设置环境
export CFLAGS="-fPIC -I./Include/internal -I./Include -I. -I$PREFIX/include"
export LDFLAGS="-shared -L. -lpython$PYTHON_VERSION -L$PREFIX/lib"

# 需要编译的模块列表
MODULES=(
    "_struct:Modules/_struct.c::no"
    "math:Modules/mathmodule.c:Modules/_math.o -lm:yes"
    "cmath:Modules/cmathmodule.c:Modules/_math.o -lm:yes"
    "_sha256:Modules/sha256module.c::yes"
    "_sha512:Modules/sha512module.c::yes"
    "_random:Modules/_randommodule.c::no"
    "_json:Modules/_json.c::no"
)

for entry in "${MODULES[@]}"; do
    IFS=':' read -r name src extra_objs needs_core <<< "$entry"
    
    echo "=== 编译 $name ==="
    
    cflags="$CFLAGS"
    if [ "$needs_core" = "yes" ]; then
        cflags="$cflags -DPy_BUILD_CORE_MODULE"
    fi
    
    # 编译
    clang $cflags -c "$src" -o ${name}.o
    
    # 链接
    clang $LDFLAGS ${name}.o $extra_objs -o ${name}.so
    
    # 验证
    if [ -f "${name}.so" ]; then
        echo "✅ $name 编译成功"
    else
        echo "❌ $name 编译失败"
    fi
done

echo "=== 批量编译完成 ==="
```

---

## 9. 验证所有扩展模块

```bash
#!/bin/bash
# verify_extensions.sh - 验证所有扩展模块

EXTENSIONS=(
    "_struct" "math" "cmath" "_sha256" "_sha512" "_random"
    "_json" "_pickle" "_ssl" "_hashlib" "_ctypes" "_curses"
    "readline" "zlib" "bz2" "lzma" "sqlite3"
)

echo "=== 扩展模块验证 ==="

passed=0
failed=0

for ext in "${EXTENSIONS[@]}"; do
    python3.9 -c "import $ext; print('$ext: OK')" 2>/dev/null
    if [ $? -eq 0 ]; then
        ((passed++))
    else
        echo "$ext: FAILED"
        ((failed++))
    fi
done

echo ""
echo "=== 验证结果 ==="
echo "通过: $passed"
echo "失败: $failed"
```

---

*文档版本: 1.1*  
*最后更新: 2024-03-22*