# LibIME

LibIME 是 Fcitx5 输入法框架的核心引擎库，提供拼音和表格输入法的底层支持。

## 功能概述

- **拼音引擎**：支持全拼、双拼、智能纠错
- **表格引擎**：支持码表输入法（如五笔、郑码）
- **语言模型**：基于 kenlm 的统计语言模型
- **历史记录**：用户词频学习

## OHOS 适配要点

### C++20 兼容性

OpenHarmony 的 libc++ 未实现 C++20 ranges/views 特性，需要将以下代码替换为传统 C++：

- `std::views::take(n)` → 手动计数循环
- `std::ranges::reverse()` → `std::reverse()`
- `std::views::filter()` → 手动过滤循环

### RPATH 问题

libIMEPinyin.so 和 libIMETable.so 对 libIMECore.so 的依赖路径可能使用相对路径（如 `../../../lib/libIMECore.so`），需要使用 patchelf 修复：

```bash
patchelf --replace-needed ../../../lib/libIMECore.so libIMECore.so libIMEPinyin.so
patchelf --set-rpath /storage/Users/currentUser/usr/local/lib libIME*.so
```

### ELF 签名

鸿蒙系统要求所有可执行的 ELF 文件必须签名，共享库也不例外。签名可通过：
- cmd-pkgs 公共安装脚本自动签名
- ohc-run.py sign-elf 命令

## 编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ECM | 6.26.0 | KDE Extra CMake Modules |
| Fcitx5Utils | 5.1.13 | Fcitx5 核心工具库 |
| Boost | 1.87.0 | C++ 工具库（需要 iostreams） |
| libzstd | 1.5.6 | 压缩库 |
| libuv | 1.48.0 | 事件循环库（可选） |

## 参考资料

- 源码仓库：https://github.com/fcitx/libime
- Fcitx5 官网：https://fcitx-im.org