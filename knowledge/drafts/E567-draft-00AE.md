# E567 — 工程完全没有 cmake_minimum_required 时 CMake 4 直接硬报错

## 错误特征
```
CMake Error at CMakeLists.txt:1 (project):
  No cmake_minimum_required command is present.  A line of code such as

    cmake_minimum_required(VERSION 3.5)

  should be added at the top of the file.  The version specified may be lower
  if you wish to support older CMake versions for this project.
```
CMake 4.1.2 下 configure 直接 rc=1；若把该工程作为 add_subdirectory / install 的子目录引入，
则会在后两个阶段再次报 CMP0000 相关错误。

## 触发条件
- 构建系统: cmake（4.x；3.x 只给 CMP0000 兼容性警告，不报错）
- 阶段: configure / add_subdirectory / install
- 典型对象: 2007 年前后写成、当时 cmake_minimum_required 尚非强制的老工程

## 根因分析
CMake 4.0 起把「缺少 cmake_minimum_required」从弃用警告升级为硬错误。
`CMAKE_POLICY_VERSION_MINIMUM` 只在工程**已声明**某个 < 3.5 的版本时改变其策略下限，
对「完全没有该命令」的工程没有作用，因此不能作为兜底手段（本次实测 cache/环境/命令行
三种传法均是 rc=1）。E321 记录的是「已声明旧版本」场景下的 cache_variables 路线，
两者场景不同，不要混用。

## 解决方案

### 推荐方案
在顶层 CMakeLists.txt 最前面补一行，并以补丁形式归档（最小改动、可复核）：
```cmake
cmake_minimum_required(VERSION 3.5)
```
本次 dictconv 0.2 即用此方案（补丁 `0001-CMakeLists.txt.patch`），且该工程同时带
autotools，走 CMake 路径还顺带规避了 config.guess 识别不了本平台的问题（见 E568）。

### 禁止做法
- ❌ 只传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（或 tc.variables 同名变量）就认为解决：
  对「完全缺该命令」的工程无效，configure 仍 rc=1。
- ❌ 不要为了让旧工程过 configure 而整体降级到 CMake 3.x 工具链（与 OHOS SDK 工具链冲突）。

## 验证
```bash
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=ohos.toolchain.cmake && echo CONFIGURE_OK
grep -n '^cmake_minimum_required' CMakeLists.txt
```

## 关联条目
- 相关: E321（已声明 <3.5 的工程用 cache_variables 设 CMAKE_POLICY_VERSION_MINIMUM）
- 相关: E568（同一工程 autotools 侧不可用，改走 CMake）
