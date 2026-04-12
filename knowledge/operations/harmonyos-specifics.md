# 鸿蒙系统特性和平台对比

本文档介绍鸿蒙系统与其他平台的差异，以及鸿蒙特有的一些机制。

---

## 🚨 鸿蒙移植铁律（所有软件适用）

<!-- ~~### 铁律 #1：HMDFS 符号链接必须用 cp 替代 ln -s~~ → 已迁移至 graph/E050.kv + doc/E050.md, graph/E073.kv + doc/E073.md -->

<!-- ~~### 铁律 #2：make install 产出 ELF 不含 RPATH~~ → 已迁移至 graph/E077.kv + doc/E077.md (ELF签名+RPATH四步流程) -->

## 1. 与其他平台对比

<!-- ~~### 1.1 vs Linux~~ → 已迁移至各对应条目（E002,E001/E012,E009,E018,E037,E034,E031） -->| **shell** | bash | mksh/sh | 语法略有差异 |
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

<!-- ~~## 3. Shell 脚本 Shebang 写法~~ → 已迁移至 graph/E037.kv + doc/E037.md -->

<!-- ~~## 4. toybox expr bug~~ → 已迁移至 graph/E017.kv + doc/E017.md -->

<!-- ~~§5-6 测试流程+总结~~ → 已迁移至 best-practices.md -->

<!-- ~~## 7. SELinux 域转换对子进程执行的限制~~ → 已迁移至 graph/E009.kv + doc/E009.md -->

<!-- ~~## 8.1-8.5 软链接访问/创建限制~~ → 已迁移至 E018, E050, E073 -->

<!-- ~~## 8.6 共享库安全警告：ncurses 编译导致 Shell 崩溃~~ → 已迁移至 graph/E028.kv + doc/E028.md（共享库冲突/系统崩溃/--without-shared） -->

---

<!-- ~~## 9. fstat()/lseek() 对非文件 fd 返回 EACCES~~ → 已迁移至 graph/E076.kv + doc/E076.md -->

<!-- ~~## 10. SIGSYS 信号行为~~ → 已迁移至 graph/E051.kv + doc/E051.md -->

<!-- ~~## 11. /proc 访问限制~~ → 已迁移至 graph/E031.kv + doc/E031.md -->

<!-- ~~## 12. distutils spawn 吞 stderr~~ → Python 3.9 特有，distutils 已废弃(PEP 632)，不提取为独立条目 -->

<!-- ~~## 13. HMDFS 符号链接限制~~ → 已迁移至 graph/E050.kv + doc/E050.md -->

## 14. Perl 测试框架依赖问题

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


---

<!-- ~~## 15. configure 不识别 OHOS 平台变量~~ → 已迁移至 graph/E007.kv + doc/E007.md -->

<!-- ~~## 16. pthread_cond_timedwait 行为差异~~ → 已合并至 graph/E022.kv + doc/E022.md (POSIX API 行为差异类) -->

<!-- ~~## 17. 系统 POSIX 头文件缺失~~ → 已迁移至 E015, E014, E051 -->

<!-- ~~## 18. 外来二进制首次执行确认弹窗~~ → 已迁移至 graph/E054.kv + doc/E054.md -->

> 来源：`archives/p/python/3.9.0/manifest.yaml`