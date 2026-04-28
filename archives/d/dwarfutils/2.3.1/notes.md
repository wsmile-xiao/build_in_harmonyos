# dwarfutils 2.3.1 适配笔记

## 编译环境
- 构建系统: cmake (autotools 在 HMDFS 上失败)
- 编译日期: 2026-04-28
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
```bash
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
cmake --build build -j$(nproc)
cmake --install build --prefix=$HOME/usr/local
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools config.status 在 HMDFS 上失败 | HMDFS 不支持临时文件创建 | 改用 CMake 构建 |
| 2 | config.guess 无法识别 HarmonyOS | 缺少 __OHOS__ 检测分支 | 补丁 0001/0002 添加 HarmonyOS 支持 |
| 3 | dwarfdump 配置文件路径警告 | 配置文件不在搜索路径 | 不影响核心 DWARF 解析功能 |

## 源码修改
- 0001-config.guess.patch: 添加 HarmonyOS 系统检测
- 0002-config.sub.patch: 添加 ohos-linux 三元组支持

## 验证结果
- dwarfdump --version = libdwarf 2.3.1, dwarfdump 2.3.1 ✅
- DWARF 解析功能正常 ✅

## 交付物
- bin/dwarfdump (1.33MB)
- lib/libdwarf.a (1.24MB)
- include/dwarf.h, include/libdwarf.h

## 注意事项
- autotools 在 HMDFS 上不可用，必须使用 CMake
- 配置文件路径警告不影响功能
