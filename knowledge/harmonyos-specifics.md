# 鸿蒙系统特性和平台对比

本文档介绍鸿蒙系统与其他平台的差异，以及鸿蒙特有的一些机制。

---

## 🚨 鸿蒙移植铁律（所有软件适用）

### 铁律 #1：符号链接在 HMDFS 上不可靠，必须用 `cp` 替代 `ln -s`

**严重程度：🔴 阻塞级 — 违反此规则将导致所有 C 扩展编译失败**

#### 问题描述

HMDFS 文件系统**不正常跟踪符号链接**。`os.path.exists(symlink)` 返回 `False`，
动态链接器（ld.lld）通过 `-l` 搜索时**无法解析符号链接**。这导致：

- `make install` 创建的 `libXXX.so → libXXX.so.1.0` 符号链接无效
- 链接器报 `unable to find library -lXXX`
- **pip install / gem install / cpanm 等所有从源码编译扩展的操作全部失败**

#### 执行时机

```
代码下载完成
    ↓
⚡ 立即执行：扫描源码中所有 ln -s 操作（Makefile.am / Makefile.in / CMakeLists.txt / configure.ac）
    ↓
标记所有创建 .so / .a 符号链接的位置
    ↓
make install 之前
    ↓
⚡ 将所有 .so/.a 相关的 ln -s 替换为 cp -p
    ↓
make install
    ↓
⚡ 安装后验证：对所有 .so 符号链接执行 os.path.exists() 检查
    ↓
如有失败 → 确认根因并修复
```

#### 标准检查命令

```bash
# 1. 预扫描：代码下载后，标记所有 ln -s 创建 .so 的位置
grep -rn 'ln -s.*\.so\|LN.*\.so\|HARDLINK\|LN_FORCE' Makefile* configure.ac Makefile.am CMakeLists.txt

# 2. 安装后验证：检查所有 .so 文件是否可被找到
find $PREFIX/lib -name "*.so" -type l | while read link; do
    target=$(readlink "$link")
    if [ ! -e "$link" ]; then
        echo "❌ BROKEN: $link -> $target"
    else
        echo "✅ OK: $link"
    fi
done

# 3. Python 进程内验证（最严格）
python3 -c "
import os, glob
for f in glob.glob('/path/to/lib/*.so'):
    if not os.path.exists(f):
        print(f'BROKEN: {f} (symlink not tracked by HMDFS)')
"
```

#### 标准修复模式

**Makefile 项目**：
```makefile
# 修改前（configure 生成）：
(cd $(DESTDIR)$(LIBDIR); $(LN) -sf $(INSTSONAME) $(LDLIBRARY))

# 修改后（鸿蒙适配）：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); cp -p $(INSTSONAME) $(LDLIBRARY))
```

**CMake 项目**：
```cmake
# 修改前：
install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink ...)")

# 修改后：
install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E copy_if_different ...)")
```

**autotools 项目**（`configure.ac` / `Makefile.am`）：
```makefile
# 如果已有鸿蒙适配的 HARDLINK 变量，优先使用：
# $(HARDLINK) 替代 $(LN) 或 $(LN_FORCE)
```

#### 代价

每次用 `cp -p` 替代 `ln -s` 约多占用一份文件大小的磁盘空间。
对于 10MB 的共享库，代价是 10MB。**这与编译失败相比完全可以接受。**

#### 影响范围

| 软件类型 | 受影响？ | 说明 |
|----------|---------|------|
| Python + pip install | 🔴 是 | libpython3.9.so 符号链接 |
| Ruby + gem install | 🔴 是 | libruby.so 符号链接 |
| Node.js + npm install | 🔴 是 | node-gyp 编译原生模块 |
| Perl + cpanm | 🔴 是 | libperl.so 符号链接 |
| 任何 autoconf/automake 项目 | 🔴 是 | libtool 创建的 .la → .so 链接 |
| 任何 CMake 项目 | 🔴 是 | install(TARGETS) 创建的符号链接 |
| 纯 Python/Shell 脚本项目 | 🟢 否 | 不涉及 C 编译链接 |

**参考**：[E050](error-patterns.md#e050-hmdfs-符号链接不可跟踪导致链接器找不到库)、[§11](#11-hmdfs-符号链接限制e051)

### 铁律 #2：make install 产出的 ELF 不含 RPATH，必须 post-install 处理

**严重程度：🔴 阻塞级（所有 C/C++ 软件）**

#### 问题描述

HarmonyOS 上 `make install` 产出的可执行文件**不会自动嵌入 RPATH/RUNPATH**，即使：
- Makefile 中正确设置了 `LDFLAGS="-Wl,-rpath,$ORIGIN"`
- configure 检测结果正确
- build 目录中的中间产物看起来正确

实测表现：`llvm-readelf -d` 显示无任何 `(RPATH)` 或 `(RUNPATH)` 条目。

**影响范围**：所有通过 autotools/cmake/meson 编译并 `make install` 的 C/C++ 软件。
如果可执行文件依赖 `libxxx.so`（非系统库），不设 `LD_LIBRARY_PATH` 就无法运行。

#### 根因

推测与 HarmonyOS 工具链（clang 15 + lld + binary-sign-tool）交互有关：
1. `make install` 可能在 install 阶段重新链接或 strip 了二进制
2. lld 链接时可能忽略了 `-Wl,-rpath` 参数
3. binary-sign-tool 可能影响了 ELF 动态段

#### 必须的 post-install 步骤（四步，顺序不可变）

```bash
# 假设可执行文件为 $PREFIX/bin/foo，依赖库在 $PREFIX/lib/

# Step 1: 移除旧 ELF 签名（必须先做，否则 patchelf 被拒绝）
/data/service/hnp/bin/llvm-objcopy --remove-section .codesign $PREFIX/bin/foo

# Step 2: 设置 RPATH（使用 $ORIGIN 相对路径，确保可移植）
/data/service/hnp/bin/patchelf --set-rpath '$ORIGIN/../lib' $PREFIX/bin/foo

# Step 3: 重新 ELF 签名（修改 ELF 后必须重新签名）
/data/service/hnp/bin/binary-sign-tool sign -inFile $PREFIX/bin/foo -outFile $PREFIX/bin/foo -selfSign 1

# Step 4: 恢复执行权限（签名后权限丢失）
chmod a+x $PREFIX/bin/foo
```

#### 顺序不可变的原因

| 顺序错误 | 后果 |
|---------|------|
| 不移除 .codesign 就 patchelf | `patchelf: open: Operation not permitted` |
| 不签名就运行 | `Operation not permitted`（内核拒绝未签名 ELF） |
| 不 chmod +x | `Permission denied`（签名后权限归零） |
| 先签名再 patchelf | 需要再次移除签名，浪费签名次数 |

#### 验证命令

```bash
# 确认 RPATH 已嵌入
/data/service/hnp/bin/llvm-readelf -d $PREFIX/bin/foo | grep -i "rpath\|runpath"
# 期望: 0x000000000000001d (RUNPATH) Library runpath: [$ORIGIN/../lib]

# 确认不设 LD_LIBRARY_PATH 也能运行
unset LD_LIBRARY_PATH
$PREFIX/bin/foo --version
```

#### 需要处理的文件范围

安装后需要逐个处理所有依赖非系统共享库的 ELF 文件：
1. `$PREFIX/bin/*` — 可执行文件
2. `$PREFIX/lib/lib*.so` — 共享库（如被其他 .so NEEDED）
3. `$PREFIX/lib/*/lib-dynload/*.so` — 扩展模块（如依赖外部 .so）

可参考 `scripts/package_python.sh` 中的 `patch_strip_sign()` 函数批量处理。

#### 工具路径

| 工具 | 路径 |
|------|------|
| patchelf | `/data/service/hnp/bin/patchelf` |
| binary-sign-tool | `/data/service/hnp/bin/binary-sign-tool` |
| llvm-objcopy | `/data/service/hnp/bin/llvm-objcopy` |
| llvm-readelf | `/data/service/hnp/bin/llvm-readelf` |

#### 关联

- 长期记忆：`HarmonyOS ELF 签名与可移植打包流程`
- 错误模式：`libpython3.9.so: No such file or directory`（启动时报动态链接器错误）
- 实际案例：Python 3.9.0 `make install` 后 python3.9 不含 RPATH（2026-03-29 确认）

---

## 1. 与其他平台对比

### 1.1 vs Linux

| 方面 | Linux | HarmonyOS | 说明 |
|------|-------|-----------|------|
| **核心功能** | 100% | 100% ✅ | 完全兼容 |
| **编译选项** | 完全相同 | 完全相同 ✅ | 继承 Linux 配置 |
| **线程支持** | pthreads | pthreads ✅ | 完全兼容 |
| **动态链接** | dlfcn | dlfcn ✅ | 完全兼容 |
| **系统宏** | 无 | `__OHOS__` | 鸿蒙特有 |
| **编译器** | gcc | clang | 使用 LLVM 工具链 |
| **C 库** | glibc | musl libc | 有差异需注意 |
| **sed** | GNU sed | toybox sed | 功能受限 |
| **awk** | gawk/mawk | toybox awk | 功能受限 |
| **shell** | bash | mksh/sh | 语法略有差异 |
| **/tmp** | 可写 | 只读 | 需设置 TMPDIR |

### 1.2 vs Android

| 方面 | Android | HarmonyOS | 说明 |
|------|---------|-----------|------|
| **基础继承** | linux-generic32 | linux-generic32.0 ✅ | 相同 |
| **汇编方案** | linux64 | linux64 ✅ | 相同 |
| **bn_ops** | RC4_CHAR | RC4_CHAR ✅ | 相同 |
| **NDK 检测** | 复杂 | 无 | 更简洁 |
| **环境变量** | 动态检测 | 依赖系统 | 更简单 |
| **SELinux** | 强制 | 强制 | 都有限制 |

### 1.3 vs iOS

| 方面 | iOS | HarmonyOS | 说明 |
|------|-----|-----------|------|
| **工具链** | Xcode (xcrun) | LLVM (clang) | 不同 |
| **汇编方案** | ios64 | linux64 | 不同 |
| **SDK** | iPhoneOS SDK | 系统自带 | 不同 |
| **版本限制** | 需要 | 不需要 | 更简单 |

### 1.4 toybox 工具兼容性

| 工具 | GNU 版本 | toybox 版本 | 差异点 |
|------|----------|-------------|--------|
| **sed** | GNU sed | toybox sed | 不完全支持复杂脚本（多行块、分支命令） |
| **awk** | gawk/mawk | toybox awk | 功能有限，某些扩展不可用 |
| **expr** | GNU expr | toybox expr | **不支持复合正则表达式 `\|`** |
| **grep** | GNU grep | toybox grep | 基本功能相同 |
| **sh** | bash | mksh | 语法略有差异 |

**toybox sed 已知问题**：
1. 复杂的多行命令块 `{...}` 处理可能异常
2. 分支命令 `:label` 和 `b`、`t` 跳转可能不完整
3. 某些正则表达式特性不支持
4. 建议对于复杂的 autotools 项目，configure 后检查生成的 Makefile

---

## 1.5 HarmonyOS 三层安全模型 ⭐ 重要

HarmonyOS 采用三层安全架构，理解这个模型是做好鸿蒙移植的基础：

### 第一层：SELinux (MAC — 强制访问控制)

**实际权限的最终裁决者**。SELinux 通过安全上下文（Security Context）控制进程对文件的访问。

关键上下文类型：

| 上下文 | 说明 | 权限 |
|--------|------|------|
| `hishell_hap:s0` | Shell 进程 | 高权限，可执行 hnp_file |
| `adhoc_bin:s0` | 用户程序（Python、用户编译的 C 程序） | 受限，不能执行 hnp_file |
| `hnp_file:s0` | SDK 工具（clang、linker 等） | 被执行的对象 |
| `hmdfs:s0` | 用户文件 | 用户数据 |

**核心限制**：`adhoc_bin` 域的进程通过 **fork + execve** 执行 `hnp_file` 类型的 SDK 工具时被 SELinux 拦截。
但 **posix_spawn() 不受此限制**——这是 musl 实现的特性或内核策略差异，Python 3.9.0 已验证
通过 `subprocess.run(["clang", ...])` 可以正常编译 C 程序。

```
Shell (hishell_hap) → exec 用户程序 → adhoc_bin
                                        │
                              fork + execve(hnp_file) ❌ 被拦截
                              posix_spawn(hnp_file)  ✅ 正常
```

**对移植的影响**：
- fork() 本身可用，但 fork 后 execve SDK 工具受限制
- **posix_spawn() 不受此限制**（推荐路径，已验证 clang 编译可用）
- pipe 绕过法 `cmd | cat` 可用于 bootstrapping（仅构建时）
- Python subprocess 在 `_use_posix_spawn()` 对 musl 返回 True 后，所有子进程操作正常

### 第二层：HMDFS (文件系统虚拟化)

**UID 映射层**。HMDFS 是鸿蒙的文件系统，它进行 UID 虚拟映射：

- 进程看到的 UID ≠ 文件实际的 UID
- symlink 创建和访问受限
- hardlink 在用户目录不可用

**⚠️ chmod 行为约束（HMDFS 特有，实测 2026-03-29）**

HMDFS 上 `chmod()` 不是简单的空操作，而是有**三个硬性规律**：

| 规律 | 说明 |
|------|------|
| **other 固定为 0** | 无论设置什么值（0-7），other 位始终为 `---`（0o0） |
| **group 固定为 6** | 无论设置什么值（0-7），group 位始终为 `rw-`（0o6） |
| **owner 有最低权限下限** | 即使设 0o000，owner 也会变为 `rw-`（0o6） |

实测数据（/storage hmdfs 和 ~/usr/local hmdfs 结果完全一致）：

| chmod 设置 | 实际结果 | 差异 |
|-----------|---------|------|
| 0o700 | 0o760 | group: 0→6 |
| 0o740 | 0o760 | group: 4→6, other: 4→0 |
| 0o704 | 0o760 | group: 0→6, other: 4→0 |
| 0o644 | 0o660 | group: 4→6, other: 4→0 |
| 0o666 | 0o660 | other: 6→0 |
| 0o777 | 0o770 | other: 7→0 |
| 0o600 | 0o660 | group: 0→6 |
| **0o000** | **0o660** | **owner: 0→6, group: 0→6** |

**关键结论**：

1. `chmod()` 在 HMDFS 上会强制覆盖 group=6、other=0，owner 保底 rw-
2. **不能依赖 chmod 做权限隔离**：`chmod 600`（保护私钥）实际变成 660
3. **不能依赖 `chmod 000` 阻止访问**：实际变成 660，文件仍可读写
4. **`umask()` 在文件创建时生效**：`umask(077)` 后新建文件确实是 0o600
5. **ELF 签名文件 chmod 返回 Permission denied**：编译产出的二进制（有 .codesign 段）无法 chmod
6. **不同文件系统行为可能不同**：/data/app、/data/local/tmp（hmfs）因权限限制无法测试，
   /（tmpfs rootfs）返回 Operation not permitted。已确认 hmdfs 上的行为一致。

**对测试的影响**：
- `test_tarfile`：`test_file_mode` 断言磁盘文件权限为 0o644，实际为 0o660（other 4→0）
- `test_httpservers`：`test_get` 期望 `chmod(tempdir, 0)` 后服务器返回 404，实际仍可读取
- 两者都是验证 HMDFS 的权限限制，不是模块本身有 bug

**对移植的影响**：
- 不能依赖 Unix 权限位做访问控制
- 文件权限断言在测试中会失败
- 如需权限隔离，依赖 HarmonyOS MAC 策略（SELinux context）而非 DAC

**对移植的影响**：
- 不能依赖 Unix 权限位做访问控制
- symlink 需降级处理（makedirs 替代 symlink）
- 文件权限断言在测试中会失败（chmod 无效）

### 第三层：Unix 权限位 (DAC — 装饰性)

**纯装饰性元数据，不参与实际访问判定**。

- `chmod()` 调用返回成功，但权限不变
- `chown()` 调用返回成功，但 owner 不变
- `stat()` 返回的 st_mode 反映的是创建时的权限，不是 chmod 后的
- 文件创建时 other-read 位会被额外清除（与 umask 无关）

**实际访问判定链**：
```
文件访问请求
    ↓
SELinux (MAC) → 拒绝/允许 ← 这是最终裁决
    ↓ (通过)
HMDFS (UID 映射) → 映射到实际文件
    ↓
Unix 权限位 (DAC) → 忽略（装饰性）
```

### 安全模型对常见操作的影响

| 操作 | Linux | HarmonyOS | 影响 |
|------|-------|-----------|------|
| fork() + exec() | ✅ | ⚠️ SELinux 限制 | 用 posix_spawn 替代 |
| chmod() | ✅ 生效 | ⚠️ HMDFS: group固定6/other固定0; hmfs: 未测试 | 测试断言失效 |
| symlink() | ✅ | ❌ 受限 | venv 需降级 |
| /dev/shm | ✅ | ❌ 不存在 | 共享内存回退 |
| mmap RWX | ✅ | ❌ W^X 策略 | ctypes 回调不可用 |
| PTY | ✅ | ❌ 不可用 | 终端调试受限 |

---

## 2. ELF 可执行文件签名

### 2.1 签名机制

在鸿蒙系统上，ELF 可执行文件需要正确的签名才能运行。当使用 `patchelf`、`strip` 等工具修改 ELF 文件后，签名会失效，需要重新签名。

**签名文件结构**：
- `.note.ohos.ident` — HarmonyOS 平台标识段（不可删除）
- `.codesign` — 签名数据段（4KB 对齐）

```bash
# 查看签名信息
llvm-readelf -S binary | grep -E "codesign|note"
# [35] .note.ohos.ident  NOTE   ...
# [36] .codesign         PROGBITS ...
```

### 2.2 问题场景

```bash
# 使用 patchelf 修改 RPATH
patchelf --set-rpath /new/path myprogram

# 使用 strip 移除调试符号
llvm-strip myprogram

# 以上操作后，签名失效，执行时会报错
./myprogram  # zsh: operation not permitted
```

### 2.3 解决方案

**关键发现**：`binary-sign-tool` 无法覆盖已有的 `.codesign` 段（报错 "section already exists"），
必须先用 `llvm-objcopy --remove-section .codesign` 移除旧签名，再重新签名。

#### 基本重新签名（三步）

```bash
# 1. 移除旧签名段
llvm-objcopy --remove-section .codesign myprogram

# 2. 重新签名
binary-sign-tool sign -inFile myprogram -outFile myprogram -selfSign 1

# 3. 恢复可执行权限（签名后权限会丢失）
chmod +x myprogram
```

#### Strip + Debug 分离 + 重新签名（五步）

用于发布版本，减小体积同时保留调试能力：

```bash
# 1. 提取 debug info 到单独文件
llvm-objcopy --only-keep-debug myprogram myprogram.debug

# 2. 从主文件移除 debug sections
llvm-objcopy --strip-debug myprogram myprogram.tmp && mv myprogram.tmp myprogram

# 3. 在主文件中添加指向 debug 文件的链接（GDB 自动加载）
llvm-objcopy --add-gnu-debuglink=myprogram.debug myprogram

# 4. 移除旧签名 + 重新签名
llvm-objcopy --remove-section .codesign myprogram
binary-sign-tool sign -inFile myprogram -outFile myprogram -selfSign 1

# 5. 恢复权限
chmod +x myprogram
```

**分离打包**：
```bash
# 主包（不含 debug）
tar -czf myapp.tar.gz --exclude=debug/ myapp/
# Debug 符号包（需要时再安装）
tar -czf myapp-debug.tar.gz myapp/debug/
```

**调试使用**：将 `debug/` 目录解压到主程序同级目录，GDB 会通过 `.gnu_debuglink` 自动加载。

#### patchelf + 签名（四步）

```bash
# 1. 修改 RPATH
patchelf --set-rpath '$ORIGIN/../lib' myprogram

# 2. 移除旧签名
llvm-objcopy --remove-section .codesign myprogram

# 3. 重新签名
binary-sign-tool sign -inFile myprogram -outFile myprogram -selfSign 1

# 4. 恢复权限
chmod +x myprogram
```

#### 完整流程（patchelf + strip + 签名，七步）

```bash
# 1. patchelf 修改 RPATH
patchelf --set-rpath '$ORIGIN/../lib' myprogram

# 2. 提取 debug info
llvm-objcopy --only-keep-debug myprogram myprogram.debug

# 3. Strip debug sections
llvm-objcopy --strip-debug myprogram myprogram.tmp && mv myprogram.tmp myprogram

# 4. 添加 debuglink
llvm-objcopy --add-gnu-debuglink=myprogram.debug myprogram

# 5. 移除旧签名
llvm-objcopy --remove-section .codesign myprogram

# 6. 重新签名
binary-sign-tool sign -inFile myprogram -outFile myprogram -selfSign 1

# 7. 恢复权限
chmod +x myprogram
```

### 2.4 实际案例：Python 3.9.0 可移植打包

| 文件 | Strip 前 | Strip 后 | Debug Info |
|------|----------|----------|------------|
| python3.9 | 84K | 74K | 6K |
| libpython3.9.so.1.0 | **9.6M** | **3.4M** | 6.7M |
| libgdbm.so.6 | 174K | 158K | 9K |
| liblzma.so.5 | 244K | 230K | 4K |

`libpython3.9.so` 的 debug info 占 64%，strip 后主包从 177MB 降到 165MB。

### 2.5 注意事项

1. **签名后权限丢失**：每次签名后需要重新 `chmod +x`
2. **首次执行确认**：首次运行需要用户在弹窗中确认
3. **修改即失效**：任何对 ELF 文件的修改都会使签名失效
4. **不能覆盖签名**：`binary-sign-tool` 无法覆盖已有 `.codesign`，必须先 `llvm-objcopy --remove-section`
5. **debuglink 路径**：`.gnu_debuglink` 中存储的是文件名（不含路径），GDB 在默认搜索路径中查找
6. **不要删除 `.note.ohos.ident`**：这是平台标识段，删除会导致系统无法识别文件类型

---

## 3. Shell 脚本 Shebang 写法

### 3.1 推荐写法

在鸿蒙系统上，推荐使用以下 Shebang 写法：

```bash
#!/bin/sh
# 或
#!/usr/bin/env bash
```

### 3.2 不推荐的写法

```bash
#!/bin/bash  # 可能不存在
#!/usr/bin/bash  # 可能不存在
```

### 3.3 原因

- 鸿蒙 HiShell 的 `/bin/sh` 是 **toybox ash**，不是 bash
- **不支持** `${BASH_SOURCE}`、`[[ ]]`、数组等 bash 特性
- `/usr/bin/env` 不存在（HiShell 没有），`#!/usr/bin/env xxx` 会直接失败
- DevBox 提供的 bash 安装在用户目录（如 `$HOME/usr/local/bin/bash`）
- 推荐统一使用 `#!/bin/sh` + POSIX 兼容语法

### 3.4 检查 Shell

```bash
# 检查系统 shell（HiShell）
ls -la /bin/sh
# 输出: /bin/sh -> toybox

# 检查 bash 是否可用（DevBox 安装后）
which bash
# 可能输出: $HOME/usr/local/bin/bash
```

### 3.5 常见 bash 特性不可用

| 特性 | bash | HiShell (toybox ash) |
|------|------|---------------------|
| `${BASH_SOURCE[0]}` | ✅ | ❌ 为空 |
| `[[ ... ]]` | ✅ | ❌ 语法错误 |
| 数组 `arr=()` | ✅ | ❌ 语法错误 |
| `${var:offset:length}` | ✅ | ❌ |
| `$(cd "$(dirname "$0")" && pwd)` | ✅ | ✅ 替代方案 |

---

## 4. 典型问题排查案例：toybox expr bug

### 4.1 问题现象

编译 ncurses 时，`config.status` 执行过程中 sed 进程卡住，生成的 Makefile 包含乱码。

### 4.2 排查过程

```bash
# 第一步：找到卡住的进程
$ ps aux | grep sed
USER  PID  ... COMMAND
user  60545 ... sed s,@top_srcdir@,../<乱码>...,;t t

# 第二步：查看进程命令行
$ cat /proc/60545/cmdline | tr '\0' ' '
sed s,@top_srcdir@,../...乱码...,;t t

# 第三步：分析乱码来源
# 乱码在 $ac_top_srcdir 变量中

# 第四步：追踪 config.status
$ bash -x ./config.status --file=ncurses/Makefile 2>&1 | grep ac_dots
+ ac_dots='../<乱码>...'

# 第五步：分析 ac_dots 的计算
# ac_dots 来自 expr 命令的输出

# 第六步：对比测试
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
mOkk...  # toybox expr 输出乱码！

$ /path/to/gnu/expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
ncurses  # GNU expr 正确！
```

### 4.3 根因分析

| 因素 | 说明 |
|------|------|
| 触发条件 | config.status 使用复合正则表达式（`\|` 操作符） |
| 问题工具 | toybox expr |
| 问题表现 | 复合正则表达式输出乱码 |
| 影响范围 | 所有使用 autotools 的项目 |

### 4.4 解决方案

```bash
# 编译安装 GNU coreutils（包含 GNU expr）
# 参考: archives/c/coreutils/9.10/

# 设置 PATH 优先使用 GNU 工具
export PATH=$HOME/usr/local/bin:$PATH
```

### 4.5 经验总结

1. **工具兼容性问题可能很隐蔽**：简单命令正常，复杂命令出错
2. **对比测试很重要**：与已知正确的工具对比行为
3. **追踪变量来源**：使用 `bash -x` 追踪脚本执行
4. **系统化排查**：从现象 → 进程 → 变量 → 命令 → 工具

---

## 5. 测试流程规范

### 5.1 官方测试

```bash
# 运行官方测试套件
make check

# 或
make test
```

**注意事项**：
- 鸿蒙系统的签名机制可能导致测试二进制无法直接运行
- 可能需要手动确认弹窗
- 某些测试依赖 PTY 功能（系统限制）

### 5.2 自定义测试

当官方测试无法运行时，创建自定义测试：

```bash
#!/bin/bash
# test-basic.sh - 基本功能测试

echo "=== 基本功能测试 ==="

# 测试 1: 检查可执行文件
if [ -x ./myprogram ]; then
    echo "✅ 可执行文件存在"
else
    echo "❌ 可执行文件不存在"
    exit 1
fi

# 测试 2: 基本运行
./myprogram --version
if [ $? -eq 0 ]; then
    echo "✅ 基本运行成功"
else
    echo "❌ 基本运行失败"
    exit 1
fi

# 测试 3: 功能验证
result=$(./myprogram --test-feature)
if [ "$result" = "expected" ]; then
    echo "✅ 功能测试通过"
else
    echo "❌ 功能测试失败"
    exit 1
fi

echo "=== 所有测试通过 ==="
```

### 5.3 测试报告规范

测试报告应包含：

1. **测试环境**
   - 系统版本
   - 编译器版本
   - 依赖版本

2. **测试统计**
   - 总测试数
   - 通过数
   - 失败数
   - 跳过数

3. **失败详情**
   - 失败测试名称
   - 失败原因
   - 错误输出

4. **已知限制**
   - 系统限制导致的失败
   - 功能缺失

---

## 6. 总结

### 6.1 鸿蒙特有机制

| 机制 | 说明 | 处理方式 |
|------|------|----------|
| ELF 签名 | 可执行文件需要签名 | 修改后重新签名 |
| SELinux | 强制访问控制 | fork+exec 受限，用 posix_spawn 替代 |
| toybox | 工具功能受限 | 编译 GNU 工具替代 |
| /tmp 只读 | 临时目录限制 | 设置 TMPDIR |
| musl libc | C 库差异 | 条件编译处理 |

### 6.2 迁移建议

从 Linux 迁移到 HarmonyOS 时：

1. **工具链**：使用 clang + LLVM 工具链
2. **脚本**：注意 shebang 写法，测试 toybox 兼容性
3. **测试**：准备自定义测试方案
4. **签名**：修改 ELF 后重新签名

---

## 7. SELinux 域转换对子进程执行 SDK 二进制的限制 ⭐ 重要

### 7.1 限制描述

HarmonyOS 使用 SELinux 强制访问控制，存在**域转换（Domain Transition）**机制。当用户进程创建子进程执行 SDK 工具时，子进程会因 SELinux 策略而执行失败。

### 7.2 根因分析

| 场景 | 进程类型 | SELinux Context |
|------|----------|-----------------|
| Shell 进程 | 受信任进程 | `u:r:hishell_hap:s0` |
| Python 解释器 | 用户程序 | `u:r:adhoc_bin:s0` |
| 用户编译的 C 程序 | 用户程序 | `u:r:adhoc_bin:s0` |
| SDK clang-15 | 系统工具 | `u:object_r:hnp_file:s0` |
| 用户编译的文件 | 用户文件 | `u:object_r:hmdfs:s0` |

**域转换流程：**

```
hishell_hap:s0          执行用户程序           adhoc_bin:s0
(Shell 进程)   ───────────────────────>    (Python/C程序)

✅ 可以执行 hnp_file    ───────────────>    ❌ 不能执行
   (SDK 工具)                              hnp_file
```

### 7.3 问题现象（仅限 fork + execve）

> **⚠️ 重要更新**：通过 `posix_spawn()` 调用 SDK 工具**不受此限制**。
> 以下失败现象仅在使用 `fork() + execve()` 路径时出现。

```python
import subprocess, os

# ✅ 正常工作（Python 3.9 已通过 posix_spawn 适配）
subprocess.run(['clang', '--version'])  # returncode: 0
r = subprocess.run(['clang', 'test.c', '-o', 'test'], capture_output=True, text=True)  # 编译成功

# ❌ 以下场景仍然受限（直接 execve 调用）
os.execvp('clang', ['clang', '--version'])  # 如果 C 层直接 execve
```

**关键点**：SDK 的 clang-15 是一个 109MB 的 ELF 二进制，当 `adhoc_bin` 域的进程尝试通过 `fork() + execve()` 执行它时：

1. `execve()` 系统调用成功（没有返回错误）
2. SELinux 在内核层面拦截了执行
3. 进程立即以 exit code 1 退出
4. **没有任何错误输出**（因为二进制根本没有真正开始执行）

**但 `posix_spawn()` 不受此限制**——Python 3.9.0 已验证通过 `subprocess.run(["clang", ...])` 可以正常编译和执行 C 程序。推测原因是 musl 的 `posix_spawn()` 实现或内核对该系统调用的 SELinux 策略与 `execve()` 不同。

### 7.4 解决方案：优先 posix_spawn（管道语法作为备选）

> **推荐方案**：使用 `posix_spawn()` 替代 `fork() + execve()`。Python 3.9 在 musl 平台默认使用
> `posix_spawn()`，无需额外配置即可正常执行 SDK 工具。

```c
/* C 代码中使用 posix_spawn 替代 fork+exec */
#include <spawn.h>
extern char **environ;

pid_t pid;
char *argv[] = {"clang", "test.c", "-o", "test", NULL};
posix_spawn(&pid, "/usr/bin/clang", NULL, NULL, argv, environ);
```

```python
# Python 代码直接可用（默认 posix_spawn）
import subprocess
subprocess.run(["clang", "test.c", "-o", "test"])  # ✅ 正常工作
```

#### 备选方案：管道语法绕过（仅限构建时 bootstrapping）

在 Python 还未适配 posix_spawn 的早期阶段，或者无法修改源码的情况下，
使用管道语法 `cmd | cat` 可以绕过 SELinux 限制：

```python
# 仅作为 bootstrapping 备选方案
os.system("clang test.c -o test | cat")  # exit code: 0
```

**原理**：管道强制 shell 创建子进程来执行管道的左侧命令。这个子进程的 SELinux 上下文可能具有不同的权限。

### 7.5 方案对比

| 方法 | Exit Code | 文件生成 | 适用场景 |
|------|-----------|----------|---------|
| `subprocess.run(["clang", ...])` | 0 | ✅ Yes | ⭐ **推荐**（posix_spawn） |
| `posix_spawn()` (C 层) | 0 | ✅ Yes | ⭐ **推荐**（C/C++ 项目） |
| `clang ... \| cat` | 0 | ✅ Yes | 备选（bootstrapping） |
| `clang ... \| head -N` | 0 | ✅ Yes | 备选 |
| `clang ... \| true` | 0 | ✅ Yes | 备选 |
| `clang ...`（裸 fork+execve） | 1 | ❌ No | ❌ 受 SELinux 限制 |
| `clang ... & wait` | 0 | ❌ No | ❌ 不稳定 |

> **历史记录**：Python 3.9.0 适配初期（补丁 0016 前），`subprocess.run(["clang", ...])`
> 确实因 fork+execve 路径而失败。通过补丁 0020 修改 `_use_posix_spawn()` 对 musl 返回 True 后解决。

### 7.6 正确实现（使用 `pipefail` 获取真实退出码）

```python
# HarmonyOS workaround
cmd_str = f"set -o pipefail; {cmd} 2>&1 | cat"
status = os.system(cmd_str)
```

### 7.7 受影响的软件

- **Python**: `setup.py` 通过 `_bootsubprocess.Popen` 调用 `clang` 编译扩展模块
- **Perl**: `ExtUtils::CBuilder` 编译 XS 模块
- **Ruby**: `mkmf.rb` 编译原生扩展
- **任何**通过子进程调用 SDK 编译器的构建系统

---

## 8. 软链接访问和创建限制

### 8.1 访问限制

**根本原因**：HarmonyOS 的 SELinux 策略限制了用户进程对软链接的访问。

| 系统/工具 | SELinux Context | readlink/lstat |
|-----------|-----------------|----------------|
| toybox | `u:object_r:toybox_exec:s0` | ✅ 成功 |
| 用户程序 | `u:object_r:hmdfs:s0` | ❌ EACCES |

### 8.2 受影响的 GNU coreutils 命令

| 命令 | toybox | GNU coreutils | 原因 |
|------|--------|---------------|------|
| ls | ✅ | ❌ | lstat 获取链接属性 |
| stat | ✅ | ❌ | lstat 获取链接状态 |
| rm | ✅ | ❌ | lstat 检查文件类型 |
| cp | ✅ | ❌ | lstat 检查是否为链接 |
| mv | ✅ | ❌ | lstat 检查源文件 |
| chmod | ✅ | ❌ | lstat 获取文件状态 |
| readlink | ✅ | ❌ | readlink 系统调用受限 |

### 8.3 解决方案

对于涉及软链接的操作，使用 toybox 命令作为兜底：

```bash
# 在 .zshrc 或脚本中添加别名
alias ls='/bin/ls'
alias rm='/bin/rm'
alias cp='/bin/cp'
alias mv='/bin/mv'
alias stat='/bin/stat'
```

### 8.4 创建软链接受限

在某些场景下，用户进程**创建软链接也会失败**：

```bash
# 在用户安装目录创建软链接可能失败
ln -s ncursesw/curses.h curses.h
# 错误: ln: cannot create symbolic link 'curses.h': Permission denied
```

**通用解决方案：使用 `cp` 复制代替 `ln -s` 软链接**

```bash
# 不要使用软链接
ln -s source.txt link        # ❌ 可能失败

# 使用复制代替
cp source.txt link           # ✅ 成功

# 对于目录中的多个文件
for f in ncursesw/*.h; do
    cp "$f" "$(basename $f)"
done
```

### 8.5 toybox ln -sf 的特殊问题

```bash
# 正常创建
ln -s source.txt link        # 创建: link -> source.txt ✓

# 强制覆盖问题
ln -sf source.txt link       # 创建: link_GdinNM -> source.txt ✗ (随机后缀)
```

建议在鸿蒙系统上避免使用 `ln -sf`，改用：
```bash
rm -f link && ln -s source.txt link
```

---

## 8.6 共享库安全警告案例：ncurses 编译导致 Shell 崩溃 ⚠️ 严重

### 问题背景

鸿蒙系统的 `/bin/zsh` 依赖系统预装的 `libncursesw.so.6`。如果用户编译 ncurses 时生成了共享库，可能覆盖或干扰系统库，导致严重后果。

### 事故经过

```
用户编译 ncurses（默认生成共享库）
    ↓
安装后系统库路径被影响
    ↓
所有 zsh 进程启动时加载错误的 libncursesw.so.6
    ↓
Shell 崩溃，所有终端无法打开
    ↓
系统陷入不可用状态
```

### 影响范围

- 所有依赖 Shell 的终端应用无法使用
- 无法通过终端执行任何命令
- 只能通过文件管理器或系统恢复

### 根因分析

1. **系统关键组件依赖共享库**：`/bin/zsh` → `libncursesw.so.6`
2. **共享库版本冲突**：用户编译的库与系统库冲突
3. **库加载顺序问题**：LD_LIBRARY_PATH 或 rpath 导致加载错误版本
4. **无恢复机制**：Shell 崩溃后无法通过终端修复

### 正确做法

**✅ 鸿蒙系统编译 ncurses 时必须使用静态库**

```bash
./configure --prefix=$HOME/usr/local \
    --without-shared \        # ⭐ 关键：不生成共享库
    --enable-widec \
    --enable-overwrite \
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

### 通用原则

| 库类型 | 编译选项 | 适用场景 | 风险 |
|--------|----------|----------|------|
| **静态库** | `--without-shared` | 系统关键依赖的库 | ✅ 安全 |
| 共享库 | `--with-shared` | 非系统关键库 | ⚠️ 需谨慎 |

**判断标准**：
- 如果系统已有同名共享库（如 libncursesw.so），优先使用静态库
- 如果是新库，不影响系统组件，可以考虑共享库
- Python 扩展模块可以静态链接库（如 `_curses.so` 静态链接 `libncursesw.a`）

### 紧急恢复方案

如果已经发生 Shell 崩溃：

```bash
# 方案 1: 通过文件管理器
# 删除用户安装的共享库
rm -f $HOME/usr/local/lib/libncursesw.so*

# 方案 2: 通过 Android Debug Bridge (ADB)
adb shell
rm -f /data/service/el2/user/0/users/currentUser/usr/local/lib/libncursesw.so*

# 方案 3: 系统恢复
# 重置应用数据（最后手段）
```

### 经验教训

1. **编译前检查系统依赖**：`ldd /bin/zsh` 查看系统关键组件依赖的库
2. **优先使用静态库**：避免共享库冲突风险
3. **不要修改系统库路径**：保持 LD_LIBRARY_PATH 在用户目录
4. **备份关键配置**：在修改库之前做好恢复准备

---

## 9. fstat() 对管道/终端的限制

### 9.1 限制描述

| 文件描述符类型 | fstat() 结果 | write() 结果 | 说明 |
|---------------|-------------|--------------|------|
| 普通文件 | ✅ 成功 | ✅ 成功 | 正常 |
| 管道 (pipe) | ❌ EACCES | ✅ 成功 | 可以写入，但无法获取元信息 |
| 终端 (tty) | ❌ EACCES | ✅ 成功 | 可以输出，但无法获取元信息 |
| 套接字 (socket) | ❌ EACCES | ✅ 成功 | 可以通信，但无法获取元信息 |

### 9.2 受影响的软件

- GNU coreutils: cat, head, tail, dd, split, tee 等
- 其他调用 `fstat(STDIN_FILENO)` 或 `fstat(STDOUT_FILENO)` 的软件

### 9.3 解决方案模板

```c
/* harmonyos-fstat-compat.h */
#ifdef __OHOS__

static inline int
ohos_fstat_compat (int fd, struct stat *st)
{
  if (fstat (fd, st) == 0)
    return 0;

  if (errno == EACCES || errno == EPERM)
    {
      /* HarmonyOS returns EACCES for pipes/terminals/sockets */
      memset (st, 0, sizeof (*st));
      st->st_blksize = 4096;      /* Default I/O block size */
      st->st_mode = S_IFIFO;      /* Treat as pipe/FIFO */
      return 0;
    }

  return -1;
}

#define OHOS_FSTAT(fd, st) ohos_fstat_compat ((fd), (st))

#else /* !__OHOS__ */

#define OHOS_FSTAT(fd, st) fstat ((fd), (st))

#endif /* __OHOS__ */
```

**参考补丁**：`archives/c/coreutils/9.10/patches/0002-fix-fstat-for-harmonyos.patch`

---

*文档版本: 1.6
最后更新: 2026-03-29
更新内容: v1.6 新增 §12 distutils spawn 吞 stderr 问题（pipe + clang 交互 bug）*

## 12. distutils spawn 吞掉编译器 stderr 输出 ⚠️

### 现象

Python 3.9 的 `distutils.spawn.spawn()` 调用 `subprocess.Popen(cmd, env=env)` 启动 clang 时：
- clang 返回 exit code 1（编译失败）
- **stderr 和 stdout 均为空**，无法看到编译错误信息
- 直接在 shell 中运行相同的 clang 命令，stderr 正常输出

### 影响范围

| 方式 | 是否受影响 | 说明 |
|------|-----------|------|
| `python setup.py build_ext` (distutils) | ❌ 失败 | spawn 吞 stderr，无法诊断编译错误 |
| `pip install` (setuptools) | ✅ 正常 | setuptools 使用不同的 spawn 实现 |
| 直接 shell `clang` 命令 | ✅ 正常 | shell 的 pipe 对 clang 正常 |
| Python subprocess (其他场景) | ✅ 正常 | 仅 distutils+clang 组合有问题 |

### 受影响的测试

- `test_peg_generator.test_c_parser` — 20 个 ERROR（distutils 编译 C parser 失败）
- 任何使用 `distutils` 编译 C 扩展的测试

### 不影响的场景

- `pip install` 安装 C 扩展包（使用 setuptools）
- PEG parser 功能本身（已预编译到 Python 中）
- Python 语法解析（完全正常）

### 根因分析

与 `poll() + /dev/null` 内核 bug（详见 troubleshooting.md §7）类似，是鸿蒙 pipe 子系统的问题。
`distutils.spawn.spawn()` 使用 `subprocess.Popen(cmd, env=env)` 时，pipe 对 clang 的 stderr 连接异常。
可能原因：
1. 传递 `env=env` 参数时 subprocess 创建的 pipe 与鸿蒙的进程模型不兼容
2. clang 在鸿蒙上的 stderr 输出使用了某种非标准管道机制

### 解决方案

**方案 1：使用 setuptools 代替 distutils（推荐）**
```bash
pip install setuptools  # setuptools 的编译流程不受影响
```

**方案 2：跳过受影响测试**
```python
@unittest.skipIf(sys.platform == "ohos",
                 "distutils spawn swallows clang stderr on HarmonyOS")
class TestCParser(unittest.TestCase):
    ...
```

**方案 3：修复 distutils spawn（见补丁）**
在 `Lib/distutils/spawn.py` 的 `spawn()` 函数中，显式捕获并打印 stderr：
```python
proc = subprocess.Popen(cmd, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
stdout, _ = proc.communicate()
if proc.returncode and stdout:
    sys.stderr.write(stdout.decode(errors='replace'))
```

### 注意

distutils 在 Python 3.10+ 中已移除（PEP 632），被 setuptools 完全替代。
此问题仅在 Python 3.9 及更早版本存在。

---

*文档版本: 1.6
最后更新: 2026-03-29
更新内容: v1.6 新增"铁律 #2：make install 产出的 ELF 不含 RPATH，必须 post-install 处理"*

## 11. HMDFS 符号链接限制（E051）

### 现象

- `os.path.exists(symlink)` 返回 `False`，即使目标文件存在
- 动态链接器（ld.lld）通过符号链接找不到共享库：`unable to find library -lXXX`
- Python `import` 能找到 `.so`（通过 dlopen 的 real-path 解析），但**编译链接阶段**失败

### 根因

HMDFS 文件系统不正常跟踪符号链接。`os.stat()` 对符号链接返回的 inode 与目标文件不同，
导致链接器的库搜索路径遍历时无法解析符号链接。

### 影响

- `make install` 创建的 `libpython3.9.so → libpython3.9.so.1.0` 符号链接无效
- 导致 `pip install` 编译所有 C 扩展包时链接失败
- 任何依赖 `-l` 链接符号链接 `.so` 的操作都会受影响

### 解决方案

**用文件副本替代符号链接**。Python 3.9.0 补丁 0024：

```makefile
# Makefile.pre.in sharedinstall 部分
# 修改前：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(LN_FORCE) $(INSTSONAME) $(LDLIBRARY))
# 修改后：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(HARDLINK) $(INSTSONAME) $(LDLIBRARY))
```

其中 `$(HARDLINK)` 在鸿蒙上定义为 `cp -p`（补丁 0007 已有）。

### 代价

额外占用约 10MB 磁盘空间（libpython3.9.so.1.0 的副本）。

### 验证

修复后 greenlet、brotli、netifaces 等包编译链接正常。

## 10. SIGSYS 信号行为（与 Linux seccomp 完全不同）⚠️ 重要

### 问题描述

HarmonyOS 内核对未实现的 syscall（如 `setreuid`、`setregid`、`chroot`、`clock_settime`）发送 SIGSYS 信号（signal 31），但其行为与 Linux seccomp SIGSYS **完全不同**。

### 行为对比

| 特性 | Linux seccomp SIGSYS | HarmonyOS 未实现 syscall |
|------|---------------------|------------------------|
| 信号编号 | SIGSYS (31) | SIGSYS (31) |
| `sigaction` 可捕获？ | ✅ 全部可捕获 | ❌ **部分不可捕获** |
| handler 中 `si_syscall` | ✅ 包含 syscall 号 | ❌ 不可靠 |
| handler 返回后 | 返回 `-ENOSYS` | 进程被终止（不可捕获时） |
| errno 设置 | EPERM/ENOSYS | 不确定/垃圾值 |

### 不可捕获的 syscall（最危险）

- **`setreuid()`** — 进程直接终止，任何 signal handler 都不触发
- **`setregid()`** — 同上

### 可捕获但行为异常的 syscall

- **`chroot()`** — handler 可触发，但 syscall 返回垃圾值（如 ret=158431531, errno=0）
- **`clock_settime()`** — handler 可触发，但 errno 不可靠

### 正确做法

**在 C 源码中用 `#ifdef __OHOS__` 守卫，避免进入内核**。详见 `ohos-adaptation-patterns.md` 的"未实现 syscall 提前拦截"模式和 `error-patterns.md` E051。

### 影响

所有从 Linux 移植到鸿蒙的 C/C++ 软件都可能遇到此问题。如果程序中调用了上述 syscall 且鸿蒙内核未实现，进程会直接崩溃。

---

## 11. Perl 测试框架依赖问题

### 问题描述

许多 GNU 软件的测试套件使用 Perl 编写，需要额外的 CPAN 模块。系统预装的 Perl 5.42.0 缺少这些模块。

### 常见缺失模块

- `HTTP::Daemon` - HTTP 服务器模拟（wget 测试需要）
- `HTTP::Request` / `HTTP::Response` - HTTP 消息处理
- `Test::More` - 测试框架
- `Module::Build::Tiny` - 构建工具

### 解决方案

**推荐：安装 cpanm**

```bash
# 下载 cpanm
curl -L https://cpanmin.us -o cpanm
chmod +x cpanm

# 安装模块
./cpanm --notest HTTP::Daemon HTTP::Message LWP
```

**配置本地 Perl 库**

```bash
# 创建本地库目录
mkdir -p ~/perl-lib

# 设置环境变量
export PERL5LIB="$HOME/perl-lib/lib/perl5:$PERL5LIB"
export PERL_MM_OPT="INSTALL_BASE=$HOME/perl-lib"
export PERL_MB_OPT="--install_base $HOME/perl-lib"
```

### 受影响的软件测试

| 软件 | 测试依赖 | 状态 |
|------|----------|------|
| wget | HTTP::Daemon, HTTP::Message | 需安装模块 |
| curl | HTTP::Daemon 等 | 需安装模块 |
| 其他 Perl 测试软件 | 各种 CPAN 模块 | 视情况而定 |

### 替代验证方式

当测试框架无法运行时，采用手动验证：

```bash
# 功能测试
wget --version
wget --no-check-certificate -q https://example.com/ -O /dev/null && echo "OK"

# 断点续传测试
wget -c ...

# 递归下载测试
wget -r ...
```
## 11. /proc 文件系统访问限制

### 问题描述

鸿蒙系统的 SELinux 策略限制了普通用户对 `/proc` 文件系统的访问。即使文件权限显示所有用户可读（`-r--r--r--`），普通用户仍然无法读取。

### 现象

```bash
$ cat /proc/stat
cat: /proc/stat: Permission denied

$ ls -la /proc/stat
-r--r--r-- 1 root root 0 2026-03-16 22:23 /proc/stat

$ ls -Z /proc/stat
u:object_r:proc_stat_file:s0 /proc/stat
```

### 受影响的工具

- **htop** - 需要 sudo 运行
- **top** - 可能受影响
- **ps** - 可能受影响
- 任何需要读取 `/proc` 的进程监控工具

### 解决方案

1. 使用 `sudo` 运行受影响的工具
2. 或使用鸿蒙提供的替代方案

> **注意**：鸿蒙 sudo 是自研极简实现（仅 31KB），不支持 `-E`、`-u`、`-s`、`-i` 等标准选项，每次执行都需输入锁屏 PIN 且无凭据缓存。
> 完整的 sudo 功能差异分析、编译场景影响和规避方案详见 `sudo-analysis.md`。

### 相关信息

- 用户组 `readproc(3009)` 可能与进程读取权限相关
- SELinux 上下文类型：`proc_stat_file`, `proc_t` 等

