# fann 2.2.0 — 适配笔记

状态: published

## 基本信息
- 名称: fann
- 版本: 2.2.0
- 构建系统: cmake
- 语言: C/C++
- 许可证: LGPL-2.1-or-later
- 依赖: 无
- 源码URL: https://downloads.sourceforge.net/project/fann/fann/2.2.0/FANN-2.2.0-Source.tar.gz
- SHA256: 3d6ee056dab91f3b34a3f233de6a15331737848a4cbdb4e0552123d95eed4485

## 编译参数
```
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 适配修改

### 1. CMake 策略版本 (cmake_minimum_required)
- 问题: CMakeLists.txt 使用 `cmake_minimum_required(VERSION 2.8)`，cmake 4.x 不兼容
- 解决: 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数
- conanfile.py: 在 generate() 中设置 `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`

### 2. 静态链接 (R26)
- 问题: src/CMakeLists.txt 中 `ADD_LIBRARY(xxx SHARED ...)` 显式使用 SHARED 关键字
- BUILD_SHARED_LIBS=OFF 无法覆盖显式 SHARED
- 解决: 创建 patch `patches/0001-src-CMakeLists.txt.patch`，将 SHARED 改为 STATIC
- conanfile.py: generate() 中设置 `tc.variables["BUILD_SHARED_LIBS"] = "OFF"`

### 3. conanfile.py 构建系统修正
- 问题: conan-init 自动生成的 conanfile.py 使用 Autotools 模板，但 fann 使用 CMake
- 解决: 手动修正为 CMake 构建系统 (CMakeToolchain, CMake, cmake_layout)

### 4. 许可证修正
- 问题: conan-init 生成的许可证为 "MIT"
- 解决: 修正为 "LGPL-2.1-or-later"

## 测试
- ctest: 无测试定义（CMakeLists.txt 中无 enable_testing()）
- conan test_package: test_fann 编译链接成功，运行输出 "test fann 2.2.0: OK"，CTest 1/1 通过

## 产物
- lib: libfann.a, libfloatfann.a, libdoublefann.a, libfixedfann.a, pkgconfig/fann.pc
- include: fann.h, doublefann.h, floatfann.h, fixedfann.h, fann_internal.h, fann_data.h, compat_time.h, fann_activation.h, fann_cascade.h, fann_error.h, fann_train.h, fann_io.h, fann_cpp.h
- bin: 无（纯库）

### 对话 #1 — 初始编译与 Conan 配方生成

**用户**: 编译 fann 2.2.0，使用 openharmony-compile-agent 技能，按模式B（探索性编译）执行。

**助手**:
1. 加载 openharmony-compile-agent 技能，设置 SKILL_ROOT
2. 运行 init-build 下载源码包并初始化构建上下文
3. 探索阶段 CMake 编译：
   - 发现 cmake_minimum_required(VERSION 2.8) 与 cmake 4.x 不兼容 → 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   - 发现 src/CMakeLists.txt 显式使用 SHARED → 需 patch 改为 STATIC
   - 编译成功，生成 4 个静态库 .a 文件
4. make install 安装到 staging 目录
5. conan-init 生成 conanfile.py（自动检测为 autotools，手动修正为 CMake）
6. 创建 SHARED→STATIC patch 文件
7. conan-verify 全部 8 道门禁通过（G0-G4, L2/L4/L5）
8. finish 命令完成，状态 built

**关键决策**:
- conanfile.py 使用 CMakeToolchain 而非 Autotools
- patch 文件由 finish 的 refresh-patch 自动重新生成（0001-src-CMakeLists.txt.patch）
- conandata.yml 的 patch_file 引用需与磁盘文件名一致
---

**编译结束**: 2026-06-29 14:58
**最终状态**: published
