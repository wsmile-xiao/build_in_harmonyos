# PROGRESS.md - Scintilla 5.6.1

## 当前状态

- **阶段**: Phase 4 归档完成
- **更新时间**: 2026-03-31 12:00
- **源码目录**: ${TMPDIR:-$HOME/tmp}/builds/scintilla
- **构建目录**: ${TMPDIR:-$HOME/tmp}/sci_ohos

## 编译方案

**策略**: 核心库独立编译（无 GTK）

Scintilla 标准构建依赖 GTK，而 HarmonyOS 不可用。采用以下方案：
1. 仅编译 src/ 下 33 个平台无关的核心源文件
2. 新增 PlatOHOS.cxx 提供最小 Platform 命名空间实现
3. 产出静态库 libscintilla_core.a

## 错误记录

### E001: CA 证书缺失导致下载失败
- **阶段**: Phase 0
- **错误**: `curl: (77) error setting certificate file: /etc/ssl/certs/ca-certificates.crt`
- **根因**: HarmonyOS 未预装 CA 证书包
- **解决**: 使用 `curl --insecure` 跳过证书验证
- **跨软件通用性**: 高（所有 HTTPS 下载都会遇到）

### E002: 核心库链接缺少 Platform 符号
- **阶段**: Phase 3
- **错误**: `undefined symbol: Scintilla::Internal::Platform::DebugPrintf` 和 `Platform::Assert`
- **根因**: src/ 中的 CellBuffer 等文件调用了 Platform 命名空间的调试函数
- **解决**: 创建 PlatOHOS.cxx 提供 DebugPrintf、Assert 等最小实现
- **跨软件通用性**: 低（Scintilla 特有的 Platform 抽象层设计）

## 源码修改清单

| 文件 | 修改原因 | 补丁状态 |
|------|---------|---------|
| (无 src/ 文件修改) | 核心代码零修改 | N/A |
| ohos/PlatOHOS.cxx (新增) | 提供平台桩实现 | 新文件 |

## 测试结果

- **官方单元测试**: 52/52 通过，3791 断言
- **外部链接测试**: 通过（Document、Selection、Undo/Redo 正常工作）

## 待办

- [x] 编译核心库
- [x] 运行单元测试
- [x] 创建 PlatOHOS.cxx
- [x] 生成静态库
- [x] 安装库和头文件
- [x] 验证外部链接
- [x] 完善归档

## 编译结束

- **时间**: 2026-03-31
- **最终状态**: partial（核心库成功，GUI 组件不可用）
