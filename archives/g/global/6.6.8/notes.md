# global 6.6.8 编译笔记

## 编译日期
2026-06-08

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 架构: aarch64
- 编译器: clang
- 工作目录: /data/storage/el2/base/cache（解决 HMDFS 权限问题）

## 编译状态
✅ 成功

## 主要修改
1. **config.guess**: 添加 HarmonyOS 系统识别（echo "aarch64-unknown-linux-ohos" && exit 0）
2. **config.sub**: 添加 linux-ohos 内核验证支持

## 编译产物
- global (880KB)
- gtags (860KB)
- htags (996KB)
- gtags-cscope (504KB)

## 遇到的问题及解决方案
1. **HMDFS 权限问题**: 在 /data/storage/el2/base/cache 目录下执行编译
2. **config.guess 不识别 HarmonyOS**: 在文件开头添加识别代码
3. **缺少 ncurses**: 使用预编译包安装