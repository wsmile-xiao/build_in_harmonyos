# crossguid

## 软件描述

crossguid 是一个轻量级跨平台 C++ GUID/UUID 库，对各平台使用其原生 GUID/UUID 生成器，并提供解析、字符串化与比较的通用类。

## 功能概述

- **GUID 生成**：`GuidGenerator::newGuid()`（Linux 经 libuuid `uuid_generate`）
- **字符串互转**：`Guid(string)` 解析与 `operator<<` 字符串化
- **比较语义**：`==` / `!=` 值比较
- **跨平台**：Linux（libuuid）/ macOS（CFUUID）/ Windows（CoCreateGuid）/ Android（JNI）分支

## OHOS 适配

### 构建方式

- **custom 直接编译**：2015 快照无 `CMakeLists.txt`（CMake 重构 2018 年才引入），按上游 `linux.sh` 等价执行——`clang++ -std=c++11 -DGUID_LIBUUID -I<uuid include> guid.cpp`，`llvm-ar` 归档为 `libcrossguid.a`。
- 上游测试同样直编直跑：`test.cpp + testmain.cpp + guid.cpp` 链 `libuuid.a`。

### 关键攻坚点

1. **版本考据**：`0.0-git200150803` 为 Debian 系 `0.0+git200150803` 快照口径（`150803` = 2015-08-03），取上游官方提交 `8f399e8`（当日 master 头），codeload 包 sha256 已本地验算。
2. **libuuid 依赖**：`guid.cpp` 的 `GUID_LIBUUID` 分支需 `uuid/uuid.h`；复用制品仓已发布的 `uuid/2.40.1`（transitive），头文件与静态库直传编译命令行，不经过共享系统前缀。
3. **R33 合规**：编译器/ar 均经 `tools.build:compiler_executables` 获取，真机绝对路径仅作回退。

### 与 Linux 的差异

- 无行为差异。OHOS 走与 Linux 相同的 `GUID_LIBUUID` 路径；macOS/Windows/Android 分支不参与本次构建。

## 依赖关系

- 编译依赖：uuid/2.40.1（transitive_headers + transitive_libs）
- 无其他依赖。

## 版本记录

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.0-git200150803 | built | 2026-09-10 | 2015 快照 custom 适配，待真机预检 |

## 参考资料

- 上游仓库：https://github.com/graeme-hill/crossguid
- 快照提交：https://github.com/graeme-hill/crossguid/commit/8f399e8bd4252be9952f3dfa8199924cc8487ca4
