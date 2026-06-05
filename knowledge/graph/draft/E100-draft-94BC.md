# E100: GNU coreutils stdin 权限错误

## 错误现象

```bash
# sort 从 stdin 读取失败
$ echo "test1\ntest2\ntest3" | sort
sort: stat failed: -: Permission denied

# tail 从 stdin 读取失败
$ echo "test" | tail
tail: cannot fstat 'standard input': Permission denied

# grep 从 stdin 读取失败
$ echo "test" | grep "test"
grep: Permission denied
```

**关键特征**：
- 错误信息包含 "Permission denied" 和 stdin（"-"）
- 所有 GNU coreutils 命令（sort/tail/grep/cat 等）从管道读取时都会失败
- 从文件读取正常：`sort filename` ✅

## 根因分析

GNU coreutils 的命令在从 stdin（文件描述符 0）读取时，会调用 `fstat()` 或 `stat()` 系统调用检查 stdin 的状态信息（文件大小、权限、类型等）。鸿蒙系统的 SELinux 或权限管理策略限制了这一操作，导致返回 "Permission denied"。

**技术细节**：
- `sort` 调用 `stat()` 检查 stdin 是否是常规文件
- `tail` 调用 `fstat()` 获取 stdin 的文件信息
- `grep` 在某些模式下也会检查 stdin 的状态

**平台限制**：
- HarmonyOS HongMeng Kernel 1.12.0
- SELinux/权限管理策略限制了对 stdin 文件描述符的 stat 操作
- 这是平台级别的安全限制，不是软件本身的 bug

## 影响范围

### 直接影响
- 所有使用管道的场景：`cmd | sort`、`cmd | tail`、`cmd | grep`
- Autotools 构建的软件：configure/config.status 脚本大量使用管道
- Shell 脚本中的管道操作

### 间接影响
- 大量使用 Autotools 的开源软件无法在鸿蒙系统上编译
- Shell 脚本的兼容性问题
- 自动化测试和 CI/CD 流程受阻

**典型场景**：
- configure 脚本中的编译器检查（`echo test | grep`）
- config.status 生成 Makefile（使用 sort 处理变量）
- 日志分析脚本（`tail -f logfile`）

## 诊断步骤

1. **验证问题**：
   ```bash
   # 快速测试
   echo "test" | sort
   # 预期输出：sort: stat failed: -: Permission denied
   ```

2. **验证文件模式**：
   ```bash
   # 从文件读取（应该成功）
   echo "test" > /tmp/test.txt
   sort /tmp/test.txt
   # 预期输出：test
   ```

3. **检查命令版本**：
   ```bash
   sort --version
   # 确认是 GNU coreutils
   ```

## 解决方案

### 方案 A：使用临时文件代替管道（推荐）

**适用场景**：可修改脚本或命令行操作

**修复步骤**：
```bash
# 原命令（失败）
cat file | sort

# 改为（成功）
cat file > /tmp/sort-input.txt
sort /tmp/sort-input.txt
rm /tmp/sort-input.txt
```

**Autotools 修复**（需要手动编辑 configure/config.status）：
```bash
# 找到管道使用位置
grep -n "| sort" configure
grep -n "| tail" configure

# 手动替换为文件读写
# 注意：这需要仔细修改，可能很复杂
```

### 方案 B：等待平台修复

**适用场景**：无法修改脚本，或修改成本过高

**说明**：
- 这是鸿蒙系统的平台限制，需要华为修复 SELinux 权限策略
- 临时可以使用其他系统或容器编译
- 等待 GNU coreutils 或 musl 版本的修复

### 方案 C：使用 toybox 命令（实验性）

**适用场景**：toybox 版本支持所需功能

**验证**：
```bash
# 检查 toybox 是否包含所需命令
toybox sort
toybox tail

# 测试 toybox 版本是否能从 stdin 读取
echo "test" | toybox sort
# 如果成功，可以在 PATH 中优先使用 toybox 版本
```

## 不推荐的做法

### ❌ 使用 --build/--host 参数绕过

**错误示例**：
```bash
./configure --build=aarch64-linux-gnu --host=aarch64-linux-gnu
```

**为什么不推荐**：
1. 这只是临时覆盖 config.guess，不解决 stdin 权限问题
2. configure/config.status 内部仍会使用管道
3. 可能导致编译路径错误、依赖库无法找到
4. 违反 SKILL.md R23 规则（native 编译不应使用这些参数）

## 知识分级

**L1 - 平台真理**：所有在鸿蒙系统上编译的软件都会遇到这个问题，这是平台级别的限制。

## 相关错误

- **E002**：/tmp 只读问题（同样是平台权限限制）
- **E051**：未实现的 syscall（平台限制）
- **E072**：config.sub 三元组验证失败（本错误会导致 E072 无法解决）

## 编译建议

对于使用 Autotools 构建的软件：
1. **优先考虑其他构建系统**：如果软件支持 CMake/Meson，优先使用这些构建系统（它们较少使用管道）
2. **使用预编译包**：如果 cmd-pkgs 中有预编译版本，直接安装（避免编译）
3. **在其他系统编译**：如果无法在鸿蒙上编译，可以在 Linux 容器或其他环境中编译，然后将产物移植
4. **等待平台修复**：这是最彻底的解决方案，但时间不可控

## 参考资料

- GNU coreutils 源码：`sort.c`、`tail.c`、`grep.c` 的 stdin 处理逻辑
- HarmonyOS SELinux 策略文档
- Autotools 构建原理：configure/config.status 的管道使用

---

**记录者**: Agent 94BC
**记录日期**: 2026-05-19
**来源**: libao 1.2.0 编译失败案例