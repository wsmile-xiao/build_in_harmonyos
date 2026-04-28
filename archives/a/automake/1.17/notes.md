# automake 1.17 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-25
- 编译器: clang/clang++
- 状态: partial（编译完成但部分流程未走完）

## 编译步骤
（PROGRESS.md 为空模板，无实际编译记录）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|

## 源码修改
- `lib/config.guess` — HarmonyOS 系统检测 (0001)
- `lib/config.sub` — linux-ohos OS 识别 (0002)

## 注意事项
- 状态为 partial
- 可能需要类似 1.16.5 的鸡生蛋问题处理方案（gen-all.pl）
- 补丁覆盖 config.guess 和 config.sub
