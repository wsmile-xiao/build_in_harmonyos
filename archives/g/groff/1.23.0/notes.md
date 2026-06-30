# groff 1.23.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码解压到: /storage/Users/currentUser/builds/groff-1.23.0.work
2. 应用 config.guess/config.sub 鸿蒙平台补丁
3. 添加 linux-ohos 内核组合例外
4. 运行 configure --prefix=/storage/Users/currentUser/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少平台检测逻辑 | 应用 patch-autotools-ohos.pl 补丁 ✅ |
| 2 | config.sub 三元组验证失败 | 缺少 ohos OS 识别规则 | 添加 ohos-linux 三元组 + OS白名单 ✅ |
| 3 | Kernel 'linux' not known to work with OS 'ohos' | 缺少 kernel-OS 组合白名单 | 手动添加 linux-ohos*) 例外 ✅ |
| 4 | **cat - Permission denied** | 鸿蒙平台限制：`cat - <<HEREDOC` 无法从 stdin 读取 heredoc 内容 | ⚠️ **未解决** — 这是平台底层限制，configure 无法创建 conftest 文件 |

## 问题详情 (问题 #4)

**错误现象**：
```
cat: -: Permission denied
configure: error: C compiler cannot create executables
```

**根本原因**：
- autotools configure 使用 `cat confdefs.h - <<_ACEOF >conftest.$ac_ext` 创建测试文件
- 鸿蒙 HMDFS 文件系统不支持 `cat -` 从 stdin（heredoc）读取数据
- 影响 configure 中 269 处此类用法，导致无法创建 conftest.c 测试文件

**尝试的方案**：
- 使用 bash 替代 zsh 运行 configure → 失败
- 设置 TMPDIR → 无效（问题不在临时目录）
- 手动测试编译器能力 → 编译器可正常工作
- 问题定位在 autotools 的 cat heredoc 机制

**建议后续方案**：
1. 等待鸿蒙平台修复 HMDFS 对 cat stdin 的支持
2. 或开发 configure 脚本预处理工具，将 heredoc 替换为临时文件方式
3. 或使用 cmake 替代 autotools 构建（如果有 cmake 支持）

## 源码修改

- `build-aux/config.guess` — HarmonyOS 系统检测补丁（patch-autotools-ohos.pl 应用）
- `build-aux/config.sub` — ohos OS 识别 + linux-ohos 内核组合补丁（手动添加）

## 依赖版本

无依赖

## 验证结果

```bash
# 编译器能力测试（手动）
echo 'int main() { return 0; }' > test.c
clang test.c -o test && ./test  # ✅ 成功

# configure 测试（成功）
./configure --prefix=...  # ✅ 成功（使用 bash + toybox cat）
```

## 注意事项

⚠️ **关键发现 (E076)**：
- GNU coreutils cat 在 heredoc 输出到 stdout 时有 Permission denied
- **解决方案**：使用 `/usr/bin/cat`（toybox 版本）替代 GNU cat
- **已解决**: HongMeng Kernel 1.12.0 已修复管道 fd 的 fstat 问题

## 编译关键修复（重做成功）

1. **PATH 调整**：`export PATH=/usr/bin:$HOME/usr/local/bin:$PATH`（让 toybox cat 优先）
2. **使用 bash**：configure 必须用 `/data/service/hnp/bin/bash` 运行
3. **umask 修改**：修改 config.status 中 `umask 077` 为 `umask 000`（解决临时目录权限问题）
4. **补丁应用**：
   - E007: `build-aux/config.guess` HarmonyOS 平台识别
   - E072: `build-aux/config.sub` linux-ohos kernel 组合 + ohos OS 识别
**成功原因**: PATH 调整 + bash 运行 + umask 修改 + 补丁应用
---

**编译结束**: 2026-05-21 20:47
**最终状态**: published
