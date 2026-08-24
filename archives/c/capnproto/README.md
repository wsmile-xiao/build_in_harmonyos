# capnproto — OpenHarmony 编译记录

## 基本信息
- 软件: Cap'n Proto
- 描述: 高性能数据交换格式和基于能力的 RPC 系统
- 官网: https://capnproto.org/
- 仓库: https://github.com/capnproto/capnproto
- 构建系统: cmake
- 目标: ohos-aarch64

## 已编译版本

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.1.0 | 🔄 前置适配中 | Conan 配方已编写，待真机验证 |

## 参考版本

本项目中 `archives/c/capnp/1.3.0` 已在真机验证通过（2026-05-12），功能可用率 100%。

## 补丁清单
- 无补丁

## 已知限制
| 限制 | 影响 | 规避方案 |
|------|------|----------|
| /tmp 只读 | 上游单元测试部分失败 | `export TMPDIR=~/tmp` |
| fuzz 测试耗时 | ctest 超时 | 单独处理 |
