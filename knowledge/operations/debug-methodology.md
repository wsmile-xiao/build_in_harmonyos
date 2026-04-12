# 调试方法论

> 本文档提供鸿蒙系统上编译软件时的**系统性调试方法**。当编译遇到问题时，
> 不要盲目猜测方向，而是按照本文档的决策树逐步排查，精准定位根因。

**相关文档**：
- [`error-patterns.md`](error-patterns.md) — 已知错误模式库（优先查这个）
- [`musl-compat.md`](musl-compat.md) — musl libc 兼容性知识
- [`environment.md`](environment.md) — 环境配置与系统限制
- [`harmonyos-specifics.md`](harmonyos-specifics.md) — 鸿蒙特有机制与平台差异
- [`doc/E007.md`](doc/E007.md) — Autotools 修改模式

---

## 1. 调试总流程（决策树）

编译失败时，按照以下决策树确定排查方向：

```
编译失败
  │
  ├─ 错误在哪个阶段？
  │   ├─ configure       → 检查依赖/工具    → 见 §2
  │   ├─ make (编译)     → 检查源码/编译器  → 见 §3
  │   ├─ make (链接)     → 检查库/符号      → 见 §4
  │   ├─ make install    → 检查软链接/权限  → 见 §5
  │   └─ 运行时          → 检查环境/RPATH/SELinux → 见 §6
  │
  ├─ 是否见过这个错误？
  │   ├─ 是 → error-patterns.md 有对应条目 → 直接复用已知方案
  │   └─ 否 → 进入系统性排查
  │
  └─ 系统性排查第一步：精确提取错误信息
      → 从编译日志的最后一行往前看，找到第一个 error
      → 不要被 warning 淹没，只关注 error
      → 提取关键信息：错误消息、涉及的源文件、编译命令
```

### 1.1 第一步：精确提取错误信息

很多编译失败的根本原因被大量 warning 掩盖了。只关注 **error** 级别的信息：

```bash
# 提取关键错误（从日志尾部开始）
make 2>&1 | grep -E "error:|Error:|fatal:" | tail -20

# 如果是 cmake 项目
cmake --build . 2>&1 | grep -iE "error|fatal|failed" | tail -20
```

**提取后问自己三个问题**：
1. 这个 error 出现在哪个阶段？（configure / compile / link / install / runtime）
2. 错误消息的关键词是什么？（如 `undefined reference`、`No such file`、`Permission denied`）
3. 是否在 [`error-patterns.md`](error-patterns.md) 中能找到匹配的条目？

### 1.2 第二步：判断错误阶段

| 阶段 | 典型错误关键词 | 常见根因方向 |
|------|---------------|-------------|
| configure | `checking... no`、`cannot guess build type` | 依赖检测失败、config.guess 未适配 |
| 编译 | `fatal error:`、`error:` (源文件级别) | 头文件缺失、语法不兼容 |
| 链接 | `undefined reference`、`ld.lld: error` | 缺少库、musl 不提供的符号 |
| 安装 | `Permission denied`、`cannot create symbolic link` | SELinux 限制、软链接问题 |
| 运行时 | `Operation not permitted`、`cannot open shared object file` | ELF 签名、RPATH、SELinux |

### 1.3 第三步：查阅已知错误模式

在进入系统性排查之前，**务必先搜索** [`error-patterns.md`](error-patterns.md)：
- 如果错误模式已知且有解决方案，直接复用，节省大量时间
- 如果错误模式未知，进入对应阶段的详细排查章节

---

## 2. configure 阶段调试

configure 是编译的第一步，也是问题最早暴露的地方。configure 失败通常意味着
**环境配置**或**依赖检测**有问题。

### 2.1 检查 build/host/target 三元组

```bash
# 检查 configure 检测到的系统类型
./config.guess
# 期望输出: aarch64-unknown-linux-ohos

# 如果输出不是 linux-ohos，说明 config.guess 需要修改
# 详见 doc/E007.md §2-3
```

**常见问题**：
- `Invalid configuration 'aarch64-unknown-linux-ohos'` → config.sub 未添加 ohos 支持
- `cannot guess build type` → config.guess 未添加 HarmonyOS 检测
- 参见 [`error-patterns.md` E007](error-patterns.md#e007-configguess-无法识别系统)

### 2.2 检查依赖检测

configure 找不到某个库或功能时：

```bash
# 检查 PKG_CONFIG_PATH 是否包含安装路径
echo $PKG_CONFIG_PATH
# 应包含: $HOME/usr/local/lib/pkgconfig

# 手动验证 pkg-config 能否找到库
pkg-config --cflags --libs openssl  # 示例

# 如果 pkg-config --cflags 返回空，可能是 C_INCLUDE_PATH 干扰
# 详见 environment.md §11
unset C_INCLUDE_PATH  # 临时移除后再试
```

**常见原因**：
| 现象 | 根因 | 解决方案 |
|------|------|----------|
| `checking for xxx... no` | PKG_CONFIG_PATH 未设置 | `export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig` |
| `pkg-config --cflags` 返回空 | C_INCLUDE_PATH 干扰 | `unset C_INCLUDE_PATH` |
| 头文件检测通过但编译失败 | 头文件存在但内容不完整 | 手动修正 config.h 或使用 cache variable |

### 2.3 鸿蒙特有问题

#### 2.3.1 configure 不识别 `aarch64-unknown-linux-ohos`

```bash
# 现象
configure: error: Invalid configuration `aarch64-unknown-linux-ohos`

# 解决：修改 config.guess 和 config.sub
# 详细步骤见 doc/E007.md §2-3
```

#### 2.3.2 configure 硬编码检查 glibc 功能

有些 configure 脚本会硬编码检查 glibc 特有的功能（如 syslog、epoll 等），
在鸿蒙上这些 syscall 可能不存在，导致检测结果错误。

**解决方案：使用 cache variable 绕过**

```bash
# 创建 config.cache 跳过有问题的检测
cat > config.cache << 'EOF'
ac_cv_func_syslog=no
ac_cv_func_epoll_create=no
ac_cv_header_sys_syslog_h=no
EOF

./configure --config-cache --prefix=$HOME/usr/local
```

也可以在 configure 命令行直接指定：

```bash
./configure \
    ac_cv_func_syslog=no \
    ac_cv_func_epoll_create=no \
    --prefix=$HOME/usr/local
```

#### 2.3.3 autotools 宏需要 patch

某些 autotools 生成的检测宏（如 `AC_CHECK_HEADERS`、`AC_CHECK_FUNCS`）
在鸿蒙上可能产生错误的检测结果。

- `AC_CHECK_HEADERS` 报告头文件存在，但实际编译时缺少关键定义
- `AC_CHECK_FUNCS` 报告函数可用，但运行时触发 SIGSYS
- `AC_RUN_IFELSE` 运行时检测受 SELinux 限制导致测试程序异常退出

详见 [`doc/E007.md` §10](doc/E007.md#10-autotools-宏在鸿蒙上需要-patch)

### 2.4 TMPDIR 未设置

```bash
# 现象
configure: error: cannot create a temporary directory in /tmp

# 解决
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

# 详见 error-patterns.md E002
```

---

## 3. 编译阶段调试

编译阶段的错误通常与**源码兼容性**或**编译器差异**有关。
鸿蒙使用 clang 15 + musl libc，与 gcc + glibc 的组合有显著差异。

### 3.1 预处理错误：`#include` 找不到头文件

```bash
# 现象
fatal error: 'xxx.h' file not found

# 排查步骤
# 1. 确认头文件确实存在
ls $HOME/usr/local/include/xxx.h

# 2. 检查编译命令中的 -I 路径
make -n 2>&1 | grep "cc\|clang" | head -5

# 3. 手动测试
clang -I$HOME/usr/local/include -c test.c

# 常见原因
# - PKG_CONFIG_PATH 未设置，导致 pkg-config --cflags 未返回 -I 路径
# - C_INCLUDE_PATH 设置干扰了 pkg-config（见 environment.md §11）
```

### 3.2 编译器错误：语法/类型/声明兼容性

鸿蒙用 clang 15 + musl，**C11 标准支持良好，但 GNU 扩展受限**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| GNU 变长数组报错 | clang 对 VLA 限制更严格 | 改用固定大小数组或 `malloc` |
| `__attribute__` 不可识别 | 部分 GCC 特有属性不被 clang 支持 | 条件编译或移除 |
| `_GNU_SOURCE` 未定义 | musl 需要 `_GNU_SOURCE` 暴露完整 API | `CFLAGS="-D_GNU_SOURCE"` |
| `_XOPEN_SOURCE_EXTENDED` 未定义 | musl 不自动启用宽字符接口 | `CFLAGS="-D_XOPEN_SOURCE_EXTENDED"` |
| `_IO_read_ptr` 等字段不存在 | musl FILE 是不透明类型 | 使用公开 API 或安全回退 |

**musl FILE 结构差异**详见 [`musl-compat.md` §2](musl-compat.md#2-file-结构差异详解)

### 3.3 警告变错误：`-Werror` 导致编译失败

```bash
# 现象
error: '-Werror=xxx' 将警告升级为错误

# 思考：是否真的需要修复这个 warning？
# 评估标准：
# - 如果是无关紧要的 warning（如 unused parameter）→ 可以安全地取消 -Werror
# - 如果是真正的代码问题 → 应该修复源码

# 方案 1：取消 -Werror（谨慎使用）
sed -i 's/-Werror[^ ]*//g' Makefile
# 或
CFLAGS="-Wno-error" ./configure

# 方案 2：只禁用特定的 warning
CFLAGS="-Wno-error=unused-parameter" ./configure
```

### 3.4 clang 特有问题

#### 3.4.1 `cc1plus` 不可用

```bash
# 现象
cc1plus: error: unrecognized command-line option '-Wno-deprecated-register'
CXX compiler cannot create executables

# 原因：鸿蒙 SDK 不提供 cc1plus（GCC C++ 前端），必须使用 clang++
export CXX=clang++
./configure CXX=clang++

# 详见 error-patterns.md E053
```

#### 3.4.2 内联汇编语法差异

clang 的内联汇编语法与 GCC 略有差异：

```c
// GCC 接受但 clang 可能拒绝的写法
asm volatile("instruction %0" : : "r"(value));

// clang 严格模式可能需要更明确的约束
// 如果无法修改源码，尝试：
// 1. 禁用汇编优化：./configure --disable-asm
// 2. OpenSSL 项目：./Configure ... no-asm
```

#### 3.4.3 查看预处理结果

当宏展开导致的问题难以定位时，可以查看预处理结果：

```bash
# 查看预处理后的源码
clang -E file.c | less

# 查看宏定义
clang -dM -E - < /dev/null | grep OHOS
```

---

## 4. 链接阶段调试

链接阶段的错误通常表现为 `undefined reference`，意味着某个符号被声明使用了
但没有找到实现。

### 4.1 `undefined reference`：函数声明了但没找到实现

```bash
# 现象
ld.lld: error: undefined symbol: 'pthread_create'
ld.lld: error: undefined reference to 'dlopen'

# 排查步骤
# 1. 确定缺少哪个库
#    pthread_create → -lpthread
#    dlopen         → -ldl
#    syslog         → musl 提供，但鸿蒙内核可能不支持该 syscall

# 2. 添加缺少的库
export LDFLAGS="-lpthread -ldl $LDFLAGS"

# 3. 或在 configure 中指定
./configure LIBS="-lpthread -ldl"
```

**常见 undefined reference 及对应库**：

| 符号 | 缺少的库 | 鸿蒙特殊说明 |
|------|----------|-------------|
| `pthread_*` | `-lpthread` | 正常添加即可 |
| `dlopen`/`dlsym` | `-ldl` | 正常添加即可 |
| `syslog` | — | 鸿蒙内核不支持，需 `--disable-syslog` |
| `libintl_gettext` | `-lintl` | 鸿蒙未预装 gettext，建议 `--disable-nls` |
| `_PyType_Name` | `-lpython` | musl BIND_NOW 问题，详见 [`musl-compat.md` §3](musl-compat.md#3-bind_now-问题最重要) |

### 4.2 musl 不提供的符号

musl libc 是精简的 C 库，部分 glibc 提供的函数在 musl 中不存在或行为不同：

| 函数 | glibc | musl (鸿蒙) | 替代方案 |
|------|-------|------------|----------|
| `crypt()` | ✅ | ❌ | 禁用加密功能或自行实现 |
| `backtrace()` | ✅ | ❌ | 平台不支持，`--disable-backtrace` |
| `__xmknod`/`__fxstat` | ✅ | ❌ | glibc 内部函数，条件编译跳过 |
| `getrandom()` | ✅ | ⚠️ | 可能不可用，检查内核支持 |

**完整的 musl 兼容性对比**详见 [`musl-compat.md`](musl-compat.md)

### 4.3 LDFLAGS 问题：库搜索路径不正确

```bash
# 现象
ld.lld: error: unable to find library -lxxx

# 排查步骤
# 1. 确认库文件确实存在
ls $HOME/usr/local/lib/libxxx.so*

# 2. 检查 -L 搜索路径
make -n 2>&1 | grep "ld\|LDFLAGS" | head -5

# 3. 检查 PKG_CONFIG_PATH
pkg-config --libs xxx  # 确认返回了正确的 -L 路径

# 4. 手动测试链接
clang -L$HOME/usr/local/lib -lxxx test.c -o test
```

### 4.4 RPATH 问题：运行时找不到库

编译链接成功，但运行时报 `cannot open shared object file`。

```bash
# 检查二进制依赖
/data/service/hnp/bin/llvm-readelf -d binary | grep NEEDED

# 检查 RPATH 是否设置
/data/service/hnp/bin/patchelf --print-rpath binary

#鸿蒙上 make install 后 ELF 不含 RPATH（已确认的系统性问题）
# 必须执行 post-install 四步流程：
# Step 1: 移除旧签名
# Step 2: patchelf --set-rpath '$ORIGIN/../lib' binary
# Step 3: 重新签名
# Step 4: chmod +x
# 详见 harmonyos-specifics.md 铁律 #2
```

**鸿蒙 RPATH 问题**详见 [`harmonyos-specifics.md`](harmonyos-specifics.md) 铁律 #2 和 §2（ELF 签名机制）

---

## 5. 安装阶段调试

安装阶段的错误通常与**鸿蒙的安全机制**有关：SELinux 限制软链接创建、
ELF 签名清除权限位等。

### 5.1 软链接失败：SELinux 限制

```bash
# 现象
ln: cannot create symbolic link 'xxx': Permission denied
ln -sf 创建带随机后缀的文件

# 这是鸿蒙最常见的问题之一
# SELinux + HMDFS 策略限制软链接的创建和访问

# 解决方案
# 方案 1：用 wrapper 脚本替代软链接（推荐）
cat > $HOME/usr/local/bin/tool << 'EOF'
#!/bin/sh
exec /actual/path/to/tool "$@"
EOF
chmod +x $HOME/usr/local/bin/tool

# 方案 2：用 cp 复制替代 ln -s
cp /source/file /target/link

# 注意：ln -sf 在鸿蒙上会创建带随机后缀的文件！
# 必须使用 rm -f + ln -s 的方式
rm -f /path/to/link && ln -s /target /path/to/link

# 详见 environment.md §9（软链接处理规范）
# 详见 harmonyos-specifics.md 铁律 #1
```

### 5.2 权限问题：安装后权限归零

```bash
# 现象
make install 成功，但二进制文件无法执行
ls -la $PREFIX/bin/tool  # 显示权限为 ----------

# 原因：ELF 签名会清除权限位

# 解决
chmod +x $PREFIX/bin/tool

# 如果 chmod 也被拒绝（ELF 签名文件特殊限制）：
# 需要完整的签名流程：
# 1. llvm-objcopy --remove-section .codesign tool
# 2. binary-sign-tool sign -inFile tool -outFile tool -selfSign 1
# 3. chmod +x tool
```

### 5.3 文件覆盖：安装路径与系统文件冲突

```bash
# 现象
用户编译的 libncursesw.so 覆盖系统版本 → Shell 崩溃！

# 原因：共享库安装到了系统路径

# 预防措施
# 1. 始终使用 --prefix 指定用户目录
./configure --prefix=$HOME/usr/local

# 2. 系统关键依赖的库使用静态编译
./configure --without-shared  # 不生成共享库

# 详见 harmonyos-specifics.md §8.6（共享库安全警告案例）
# 详见 error-patterns.md E028
```

### 5.4 安装后验证清单

每次 `make install` 后执行以下检查：

```bash
#!/bin/bash
PREFIX=$HOME/usr/local

echo "=== 安装后验证 ==="

# 1. 检查软链接是否可用
echo "--- 软链接检查 ---"
find $PREFIX/bin -type l | while read link; do
    if "$link" --version >/dev/null 2>&1; then
        echo "✅ $(basename $link) 可用"
    else
        echo "❌ $(basename $link) 不可用: $(readlink $link)"
    fi
done

# 2. 检查 .so 符号链接
echo "--- 共享库符号链接检查 ---"
find $PREFIX/lib -name "*.so" -type l | while read link; do
    if [ -e "$link" ]; then
        echo "✅ $(basename $link)"
    else
        echo "❌ $(basename $link) -> $(readlink $link) (broken!)"
    fi
done

# 3. 检查二进制可执行权限
echo "--- 可执行权限检查 ---"
find $PREFIX/bin -type f | while read f; do
    if [ -x "$f" ]; then
        echo "✅ $(basename $f)"
    else
        echo "❌ $(basename $f) 无执行权限"
    fi
done
```

---

## 6. 运行时调试

编译安装都成功了，但运行时出问题。这是最容易让人困惑的阶段。

### 6.1 ELF 签名问题：修改后未重新签名

```bash
# 现象
./binary  # zsh: operation not permitted

# 原因：任何对 ELF 的修改（patchelf、strip 等）都会使签名失效
# 鸿蒙内核拒绝执行未签名的 ELF

# 解决：重新签名（必须先移除旧签名）
/data/service/hnp/bin/llvm-objcopy --remove-section .codesign binary
/data/service/hnp/bin/binary-sign-tool sign -inFile binary -outFile binary -selfSign 1
chmod +x binary

# 详见 harmonyos-specifics.md §2
```

### 6.2 RPATH 问题：运行时找不到库

```bash
# 现象
error while loading shared libraries: libxxx.so: cannot open shared object file

# 排查步骤
# 1. 检查库依赖
/data/service/hnp/bin/llvm-readelf -d binary | grep NEEDED

# 2. 检查 RPATH
/data/service/hnp/bin/patchelf --print-rpath binary

# 3. 临时验证：设置 LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 4. 永久修复：设置 RPATH
# （参考 §4.4 的 post-install 流程）
```

### 6.3 SELinux 权限：Permission denied

```bash
# 现象
./binary  # Permission denied（但 chmod +x 已设置）

# 排查：不是所有 Permission denied 都是 SELinux 的问题
# 按优先级排查：

# 1. 首次执行确认弹窗？
#   鸿蒙要求用户确认非系统预装的二进制
#   解决：手动执行一次 binary --version 完成确认
#   详见 harmonyos-specifics.md §18、error-patterns.md E054

# 2. SELinux 域转换限制？
#   用户程序（adhoc_bin 域）无法执行 SDK 工具（hnp_file 域）
#   解决：使用 HARMONYOS_BUILD_SCRIPT 模式
#   详见 harmonyos-specifics.md §7

# 3. TMPDIR 未设置？
#   程序尝试写入 /tmp 但 /tmp 只读
#   解决：export TMPDIR=$HOME/tmp

# 4. /proc 访问受限？
#   程序读取 /proc/stat 等文件被 SELinux 拒绝
#   详见 harmonyos-specifics.md §11

# 检查 SELinux 状态
getenforce  # Enforcing = 已启用
```

### 6.4 弹窗确认：首次运行需要用户确认

```bash
# 现象
编译产物首次执行时 Permission denied
第二次执行后正常

# 原因：鸿蒙安全机制要求用户确认非系统预装的二进制
# 必须在 30 秒内点击确认

# 批量触发确认
find $HOME/usr/local/bin -type f -exec {} --version \; 2>&1 | head -1

# make check 前必须先触发确认，否则测试全部失败
# 详见 harmonyos-specifics.md §18、error-patterns.md E054
```

### 6.5 `/tmp` 不可写：TMPDIR 未设置

```bash
# 现象
程序报错 cannot create temporary file /tmp/xxx
configure 报错 cannot create a temporary directory in /tmp

# 解决
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

# 详见 error-patterns.md E002
```

### 6.6 子进程失败：SELinux 域限制

```bash
# 现象
程序（如 Python）内部调用 clang 编译扩展模块失败
subprocess.run(['clang', ...]) 返回 exit code 1，无错误输出

# 原因：adhoc_bin 域的进程无法通过任何子进程方式调用 SDK 工具
# fork+exec、posix_spawn、pipe 绕过均已被 SELinux 策略阻止

# 解决：HARMONYOS_BUILD_SCRIPT 模式
# 1. 设置环境变量 HARMONYOS_BUILD_SCRIPT=/path/to/build.sh
# 2. 进程内的 spawn() 不实际执行命令，而是将命令写入脚本
# 3. 脚本由 shell（hishell_hap 域）执行

# 详见 harmonyos-specifics.md §7
```

### 6.7 运行时问题排查流程图

```
运行时错误
  │
  ├─ Operation not permitted
  │   ├─ 修改过 ELF？ → 重新签名（§6.1）
  │   ├─ 首次执行？ → 用户确认弹窗（§6.4）
  │   ├─ SELinux 域？ → HARMONYOS_BUILD_SCRIPT（§6.6）
  │   └─ chmod 失败？ → HMDFS 权限限制（environment.md §5.2）
  │
  ├─ cannot open shared object file
  │   ├─ RPATH 未设置？ → patchelf --set-rpath（§6.2）
  │   ├─ LD_LIBRARY_PATH？ → 检查环境变量
  │   └─ 库文件不存在？ → 重新编译安装
  │
  ├─ /tmp 相关错误
  │   └─ TMPDIR 未设置？ → export TMPDIR=$HOME/tmp（§6.5）
  │
  ├─ 进程意外退出 (exit 159)
  │   └─ SIGSYS？ → 未实现 syscall（harmonyos-specifics.md §10）
  │
  └─ 其他
      ├─ 查 error-patterns.md
      └─ 查 harmonyos-specifics.md
```

---

## 7. 降级策略（修不了怎么办）

当某个编译问题无法在合理时间内修复时，不要死磕。按以下优先级尝试降级：

### 7.1 优先级 1：禁用功能

```bash
# 如果某个可选功能导致编译失败，先禁用它
./configure --disable-{feature}

# 常见可禁用的功能
--disable-nls          # 禁用国际化（gettext 相关）
--disable-shared       # 只编译静态库
--without-xxx          # 禁用可选依赖
--disable-asm          # 禁用汇编优化
```

**判断标准**：禁用后软件的核心功能是否仍然可用？
- 禁用 nls → 功能正常，只是没有多语言支持 ✅
- 禁用 ssl → 可能影响核心功能 ❌ 需评估

### 7.2 优先级 2：降级版本

```bash
# 当前版本不兼容鸿蒙，试试上一个版本
# 很多情况下，旧版本的代码对平台依赖更少

# 示例：Python 3.9.25 在鸿蒙上有更多 SELinux 限制
# 而 Python 3.9.0 的 posix_spawn 方案曾经可用
```

**版本选择建议**：
- 选择稳定版本（x.y.z 的偶数 y 通常更稳定）
- 避免选择刚发布的新版本（可能引入新的平台依赖）
- 查看 `archives/` 目录下是否已有适配过的版本

### 7.3 优先级 3：寻找替代

```bash
# 这个软件有功能类似的替代品吗？
# 替代品的编译可能更容易

# 示例
# GNU sed → toybox sed（基本功能够用）
# GNU awk → toybox awk / gawk
# groff → 系统预装的 man 命令
```

### 7.4 优先级 4：静态编译

```bash
# 动态链接有问题？试试静态链接
./configure --enable-static --disable-shared

# 优点：避免共享库相关的所有问题（RPATH、符号链接、BIND_NOW）
# 缺点：二进制体积更大、无法共享代码段
```

**适用场景**：
- 系统关键库（如 ncurses），避免与系统库冲突
- 简单工具，不需要考虑磁盘空间
- 调试阶段，排除动态链接问题的干扰

### 7.5 优先级 5：记录为已知限制

如果以上都无法解决，将问题记录为已知限制：

```bash
# 在 knowledge/ 文档中标记
# status: partial 表示部分功能可用

# 在 error-patterns.md 中添加新条目
# 在软件的 manifest.yaml 中记录限制
```

---

## 8. 日志分析技巧

### 8.1 提取关键错误

```bash
# 从编译日志中提取 error 级别信息
make 2>&1 | grep -E "error:|Error:|fatal:" | tail -20

# 排除特定文件（如第三方代码）
make 2>&1 | grep -E "error:" | grep -v "third_party/" | tail -20

# 统计错误数量
make 2>&1 | grep -c "error:"
```

### 8.2 查看预处理结果

```bash
# 查看宏展开后的源码
clang -E file.c | less

# 只看特定宏的定义
clang -dM -E file.c | grep MACRO_NAME

# 查看编译器预定义的所有宏
clang -dM -E - < /dev/null | grep -E "OHOS|GLIBC|MUSL"
```

### 8.3 查看实际编译命令

```bash
# 显示但不执行编译命令（dry run）
make -n 2>&1 | grep "cc\|clang\|ld\|llvm"

# 查看完整的编译命令（包括所有参数）
make -n 2>&1 | grep "cc1\|cc1plus" | head -3

# cmake 项目
make VERBOSE=1 2>&1 | grep "clang\|lld" | head -5
```

### 8.4 链接过程详细输出

```bash
# 显示详细的链接过程
make V=1

# 或
make VERBOSE=1

# 查看链接器搜索路径
ld.lld --verbose 2>&1 | grep "SEARCH_DIR"
```

### 8.5 分析 config.log

当 configure 失败时，`config.log` 包含了详细的检测过程：

```bash
# 查看最后失败的部分
tail -100 config.log

# 查看某个特定检测的详情
grep -A 20 "checking for pthread_create" config.log

# 查看 configure 的完整输出
./configure --prefix=$HOME/usr/local 2>&1 | tee configure-output.log
```

### 8.6 运行时调试命令速查

```bash
# 查看二进制的动态库依赖
/data/service/hnp/bin/llvm-readelf -d binary | grep NEEDED

# 查看二进制的 RPATH
/data/service/hnp/bin/patchelf --print-rpath binary

# 查看符号表
/data/service/hnp/bin/llvm-nm library.a | grep symbol_name

# 查看 ELF 段信息（签名等）
/data/service/hnp/bin/llvm-readelf -S binary | grep -E "codesign|note"

# 查看进程的系统调用（如果 strace 可用）
strace -f -e trace=file binary 2>&1 | tail -50

# 检查 SELinux 上下文
ls -Z /path/to/file
```

---

## 附录 A：常见错误关键词 → 排查方向速查表

| 错误关键词 | 最可能的原因 | 排查方向 |
|-----------|-------------|---------|
| `command not found` | 工具未安装或不在 PATH | 检查 PATH、创建 wrapper |
| `cannot create temp` | /tmp 只读 | `export TMPDIR=$HOME/tmp` |
| `cannot guess build type` | config.guess 未适配 | §2.1、doc/E007.md |
| `No such file or directory` (头文件) | -I 路径缺失 | §3.1、检查 PKG_CONFIG_PATH |
| `undefined reference` | 缺少库或 musl 不提供 | §4.1、§4.2、musl-compat.md |
| `recompile with -fPIC` | 静态库未用 -fPIC 编译 | `CFLAGS="-fPIC"` 重新编译 |
| `cannot create symbolic link` | SELinux 限制 | §5.1、environment.md §9 |
| `operation not permitted` | ELF 未签名 / SELinux | §6.1、§6.3 |
| `cannot open shared object file` | RPATH / LD_LIBRARY_PATH | §6.2 |
| `BAD_SIGNATURE` | OpenSSL ARM64 汇编 bug | `no-asm` 重新编译 |
| `exit code 1 (无输出)` | SELinux 域转换 | §6.6、harmonyos-specifics.md §7 |
| `exit code 159` | SIGSYS 未实现 syscall | harmonyos-specifics.md §10 |
| `set -o pipefail` | pipe 子系统兼容性 | 尝试不同执行方式 |

---

## 附录 B：调试检查清单

每次编译遇到问题时，按此清单逐项检查：

- [ ] **环境变量**：`TMPDIR`、`CC`、`CXX`、`CFLAGS`、`LDFLAGS`、`PKG_CONFIG_PATH` 是否设置？
- [ ] **编译器**：`clang --version` 是否正常？`CC=clang` / `CXX=clang++` 是否设置？
- [ ] **工具链**：`AR=llvm-ar`、`RANLIB=llvm-ranlib` 是否设置？
- [ ] **错误阶段**：错误发生在 configure / compile / link / install / runtime？
- [ ] **错误模式**：在 [`error-patterns.md`](error-patterns.md) 中搜索关键词
- [ ] **错误日志**：`config.log`（configure 失败）或 `make 2>&1 | grep error`（编译失败）
- [ ] **依赖库**：`pkg-config --cflags --libs xxx` 是否返回正确值？
- [ ] **符号链接**：软链接是否可用（不只是存在）？参考 environment.md §9
- [ ] **ELF 签名**：修改过的二进制是否重新签名？参考 harmonyos-specifics.md §2
- [ ] **降级选项**：是否可以通过 `--disable-xxx` 或降级版本绕过？

---

*文档版本: 1.0*
*创建日期: 2026-03-30*
*适用范围: 鸿蒙系统 (HarmonyOS / OpenHarmony) 上的 C/C++ 软件编译调试*
