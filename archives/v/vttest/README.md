# vttest — VT100/VT220/VT320/VT420/VT520 终端测试程序

vttest 是一个用于测试终端模拟器功能的交互式程序，支持 VT100、VT220、VT320、VT420、VT520 等终端协议的验证。

## 基本信息

- **名称**: vttest
- **版本**: 20251205 (v2.7)
- **构建系统**: autotools
- **语言**: C
- **License**: BSD-3-Clause
- **源码**: https://invisible-mirror.net/archives/vttest/vttest-20251205.tgz
- **依赖**: 无（仅依赖标准 C 库和 POSIX 终端接口）

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 20251205 | published | 2026-06-16 |

## 鸿蒙适配要点

- config.guess 需添加 HarmonyOS case 返回 `aarch64-unknown-linux-ohos`
- 脚本 shebang 需改为 `/data/service/hnp/bin/bash`（toybox sh 无法写 /tmp）
- config.status 临时目录需改为当前目录（HMDFS sandbox 权限限制）
- make check 需交互式终端，无法自动化测试
