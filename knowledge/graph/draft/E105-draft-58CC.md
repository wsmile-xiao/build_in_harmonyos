# E105 — Rust 工具链不可用（Linux ELF 二进制缺少鸿蒙动态链接器）

## 错误特征

当尝试编译 Rust 项目（如 procs, bottom, yazi）时，cargo 或 rustc 命令无法执行，报错：
```
zsh:1: no such file or directory: rustc
zsh:1: no such file or directory: cargo
```

检查二进制文件发现：
```bash
$ file /storage/Users/currentUser/usr/local/bin/rustc
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV),
dynamically linked, interpreter /lib/ld-linux-aarch64.so.1,
for GNU/Linux 4.1.49, with debug_info, not stripped

$ ls -la /lib/ld-linux-aarch64.so.1
ls: /lib/ld-linux-aarch64.so.1: No such file or directory
```

## 触发条件
- 构建系统: Cargo (Rust)
- 阶段: configure/编译初始化
- 项目类型: Rust 项目（procs, bottom, yazi, ripgrep, bat, exa, fd, starship 等）

## 根因分析

系统中的 Rust 工具链（rustc/cargo）是为 Linux 编译的 ELF 二进制，动态链接器路径硬编码为 `/lib/ld-linux-aarch64.so.1`。

鸿蒙系统不提供此路径的动态链接器（使用自己的 libc 运行时），导致这些 Linux ELF 二进制无法加载执行。

这是一个**平台限制**，不是编译配置问题。所有依赖 Rust 工具链的项目都会受阻。

## 解决方案

### 推荐方案

**等待平台支持**（当前无法编译）：

1. 在 PROGRESS.md 记录阻塞原因：
   ```
   **阻塞原因**: Rust 工具链不可用
   - 系统中的 rustc/cargo 为 Linux ELF，缺少鸿蒙动态链接器
   - 需要鸿蒙原生 Rust 工具链或 musl 静态链接版本
   ```

2. 标记 manifest.yaml status: `failed`

3. 等待以下任一条件：
   - 鸿蒙系统提供原生 Rust 工具链
   - 项目提供 musl 静态链接的预编译版本

### 回退方案

**使用预编译版本**（如果项目提供）：

部分 Rust 项目（如 procs）在 GitHub Releases 提供预编译的 musl 静态链接版本：

```bash
# 示例：从 GitHub 下载预编译版本
curl -LO https://github.com/dalance/procs/releases/download/v0.14.10/procs-v0.14.10-aarch64-linux.zip
unzip procs-v0.14.10-aarch64-linux.zip
mv procs ~/usr/local/bin/

# 验证
procs --version
```

### 禁止做法
- ❌ 不要尝试修改 Rust 工具链的链接路径（需要重新编译 rustc 本身）
- ❌ 不要尝试创建 /lib/ld-linux-aarch64.so.1 的符号链接（鸿蒙运行时不兼容）
- ❌ 不要尝试使用 wine 或其他模拟器运行 Linux Rust 工具链（性能极差）

## 验证

检查 Rust 工具链状态：
```bash
# 检查二进制格式
file /storage/Users/currentUser/usr/local/bin/rustc

# 尝试执行（失败则确认问题）
/storage/Users/currentUser/usr/local/bin/rustc --version

# 检查动态链接器是否存在
ls -la /lib/ld-linux-aarch64.so.1
```

## 关联条目
- 平台限制类: 其他 Linux ELF 工具链问题
- Rust 项目类: procs, bottom, yazi 等

## 影响范围

**阻塞项目列表**（已知）：
- procs - 进程监控工具
- bottom - 系统监控工具
- yazi - 文件管理器
- ripgrep - 搜索工具
- bat - cat 替代
- exa - ls 替代
- fd - find 替代
- starship - shell prompt

**预估影响**: ~50+ Rust 项目在 Phase 04-13 中
