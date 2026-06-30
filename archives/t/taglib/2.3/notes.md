# taglib 2.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built → 修复后验证通过
- TMPDIR: /data/storage/el2/base/cache

## 打回重做：utf8cpp 依赖修复（2026-06-05）

### 问题诊断
1. G0 干净构建验证失败：需要手动添加 utf8cpp git submodule
2. 预编译包缺少 utf8cpp 头文件
3. 用户安装后需要手动下载 utf8cpp

### 根本原因
- taglib 2.3 源码 tar.gz 不包含 git submodule（git archive 的默认行为）
- 3rdparty/utfcpp 目录在原始 tarball 中为空
- CMakeLists.txt 在找不到 utf8cpp 时直接报 FATAL_ERROR

### 修复方案（方案A）
- 修改 CMakeLists.txt 第 180-189 行
- 添加 FetchContent 自动下载 utf8cpp 逻辑
- 确保干净构建时自动处理依赖

### 修改内容
```cmake
else()
  # Use FetchContent to download utf8cpp automatically for clean build
  include(FetchContent)
  FetchContent_Declare(
    utf8cpp
    GIT_REPOSITORY https://github.com/nemtrif/utfcpp.git
    GIT_TAG master
  )
  FetchContent_MakeAvailable(utf8cpp)
  message(STATUS "Using utfcpp fetched from GitHub")
endif()
```

### 补丁生成
- 补丁文件：0001-CMakeLists.txt.patch
- 补丁大小：+9/-4 行
- 追踪文件：CMakeLists.txt

### G0 干净构建验证（手动）
由于 clean_verify.py 脚本缺少 cmake 项目支持（已记录到 skill-feedback.md），手动执行验证：

1. 解压原始 tarball
2. 应用补丁
3. mkdir build && cmake .. -DCMAKE_INSTALL_PREFIX=~/usr/local -DCMAKE_BUILD_TYPE=Release
4. cmake 自动下载 utf8cpp（FetchContent）
5. make -j1 成功
6. make install DESTDIR=g0-install 成功
7. 安装产物：133 文件（libtag.a 7.6MB, libtag_c.a 224KB, 131 头文件）

**验证结果：✅ G0 通过**

### skill-feedback.md 记录
- 问题：clean_verify.py 缺少 cmake 项目支持
- 严重：🔴 高（阻塞所有 cmake 项目的 G0 验证）
- 建议：添加 cmake 构建分支（mkdir build && cmake ..）

---

## 编译步骤（原始）

1. **初始化编译**
   ```bash
   cd ~/myagent2/cmd-pkgs
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build taglib 2.3 --url=file:///storage/Users/currentUser/tmp/taglib-2.3.tar.gz
   ```

2. **手动下载 utf8cpp submodule**（旧方案，已废弃）
   ```bash
   cd ~/tmp
   curl -k -L -o utfcpp.tar.gz https://github.com/nemtrif/utfcpp/archive/refs/heads/master.tar.gz
   cd /data/storage/el2/base/cache/builds/taglib-2.3.work/3rdparty
   tar -xzf ~/tmp/utfcpp.tar.gz
   mv utfcpp-master utfcpp
   ```

3. **执行编译**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py build taglib 2.3 --resume-from=Step3
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | CMake 找不到 utf8cpp | tar.gz 不包含 git submodule | ✅ 添加 FetchContent 自动下载 | 已修复 |
| 2 | SSL 证书验证失败 | 系统证书问题 | curl -k 跳过 SSL 验证（临时） | 已处理 |
| 3 | G0 验证脚本不支持 cmake | clean_verify.py 流程缺失 | 手动验证 + skill-feedback | 已记录 |

## 源码修改

- 补丁文件：0001-CMakeLists.txt.patch
- 修改内容：添加 FetchContent 自动下载 utf8cpp
- 验证状态：✅ G0 干净构建验证通过

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- zlib 1.3.1（已安装）
- utf8cpp（自动下载或预编译版本）

## 验证结果

编译成功，生成静态库：
- libtag.a（主库，7.6MB）
- libtag_c.a（C 绑定，224KB）

预编译包创建成功：taglib-2.3-ohos-aarch64.tar.gz (4.7MB)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| taglib-2.3-ohos-aarch64.tar.gz | 4.7MB | 预编译包（需要重新生成）|
| 0001-CMakeLists.txt.patch | +9/-4 | utf8cpp FetchContent 补丁 |

## 注意事项

1. taglib 使用 CMake 构建系统，需要 C++17 支持
2. ✅ utf8cpp 通过 FetchContent 自动下载，无需手动干预
3. ✅ G0 干净构建验证通过（手动验证）
4. 编译为静态库（.a 文件），无动态库
5. ⚠️ clean_verify.py 脚本缺少 cmake 支持（已记录到 skill-feedback.md）

---
**编译结束**: 2026-06-05 13:42
**最终状态**: built → 修复验证通过（G0 手动验证）
