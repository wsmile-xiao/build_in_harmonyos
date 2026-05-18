# E092: 外部依赖预编译包处理

## 概述
当编译过程中发现缺少库依赖，但本地编译遇到工具链限制时，应遵循**预编译包优先原则（R18）**，优先从 cmd-pkgs 获取预编译包。

## 错误特征

### 触发场景
- configure 输出 `checking for xxx... no`
- configure 输出 `Package 'xxx' not found`
- make 输出 `cannot find -lxxx`
- 编译输出 `fatal error: xxx.h: No such file`

### 工具链限制示例
- bison/flex 编译时遇到 pipe 限制（E010）
- config.guess 无法识别平台（E007）
- musl libc 缺少某些功能

## 解决方案

### 推荐方案：使用预编译包（优先级 1）

**适用条件**：
1. cmd-pkgs 中有该软件的预编译包
2. 预编译包版本与需求兼容
3. 预编译包无特殊编译选项需求

**执行步骤**：
```bash
# 1. 查询预编译包列表
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --list-available --refresh

# 2. 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- <name> <ver>

# 3. 验证安装
pkg-config --modversion <name>  # 或
<name> --version

# 4. 继续编译
python3 $SKILL_ROOT/scripts/ohc-run.py build <software> <version> --resume-from=StepN
```

**优势**：
1. ✅ 预编译包已通过 ELF 签名，可直接执行
2. ✅ 已处理平台适配（config.guess、umask 等）
3. ✅ 避免编译链过长浪费时间
4. ✅ 本地编译可能引入新问题

**案例**：hping 3.0.0-alpha-1
- 问题：libpcap 本地编译遇到 bison/flex pipe 限制
- 解决：从 Alpine Linux 预编译包获取 libpcap.a
- 结果：编译成功，功能验证通过

### 回退方案：手动编译依赖（优先级 2）

**适用条件**：
1. cmd-pkgs 中无该软件预编译包
2. 需要特定版本（预编译包版本不兼容）
3. 需要特殊编译选项

**执行步骤**：
```bash
# 1. 查依赖编译顺序
cat $SKILL_ROOT/knowledge/operations/dependencies.md

# 2. 创建子任务编译依赖
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch plan <dependency_name>

# 3. 等待依赖编译完成

# 4. 继续主软件编译
python3 $SKILL_ROOT/scripts/ohc-run.py build <software> <version> --resume-from=StepN
```

## 禁止策略

### 禁止使用 cross-compile 参数
**模式**: `--build=|--host=|--target=`
**原因**: 本平台是 native 编译
**后果**: 虽能暂时通过 configure，但会引入隐患且违反 R15

**正确做法**: 修改 config.guess/config.sub（见 E007）

## 相关原则

- **R18**: 预编译包优先原则（核心）
- **R11**: 失败先查归档再动手
- **R12**: 先匹配错误模式再修复

## 关系图

### 根因关系
- **caused_by**: [E010, E007]（工具链限制和平台识别问题）
- **causes**: []

### 相似模式
- **similar_to**: [E018]（依赖版本不兼容）

## 应用案例

### hping 3.0.0-alpha-1
**依赖**: libpcap
**问题**: bison/flex 编译 libpcap 时遇到 pipe 限制（E010）
**解决**: 
1. 从 Alpine Linux 预编译包获取 libpcap.a（1.10.5）
2. 绕过本地编译工具链问题
3. hping 编译成功（682KB）

**验证**:
```bash
$ ls ~/usr/local/lib/libpcap.a
-rw-r--r-- 1 root root 364K 2026-05-13 16:33 ~/usr/local/lib/libpcap.a

$ hping3 -v
hping version 3.0.0-alpha-1
```

### 其他适用场景
1. **zlib**: 本地编译无问题，优先使用预编译包节省时间
2. **openssl**: 本地编译需要特殊选项（如 `--no-asm`），优先使用预编译包
3. **ncurses**: 本地编译必须 `--without-shared`，使用预编译包避免错误

## 元数据

- **创建日期**: 2026-05-14
- **触发事件**: hping 3.0.0-alpha-1 编译（libpcap 依赖处理）
- **贡献者**: 7EAB
- **状态**: draft