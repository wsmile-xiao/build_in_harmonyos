# vampire 5.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony ARM64 (aarch64)
- 状态: published

## 编译步骤

```bash
# 1. init-build
python3 $SKILL_ROOT/scripts/ohc-run.py init-build vampire 5.0.1

# 2. 加载构建上下文
source .build-context-vampire-5.0.1

# 3. CMake 配置
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF

# 4. 编译 (单线程，约 944 秒)
make -j1

# 5. 安装到测试目录
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py 使用 Autotools 而非 CMake | ohc-run.py 默认生成 Autotools 模板 | 手动改用 CMake/CMakeToolchain/cmake_layout |
| 2 | ConanException: CMakeToolchain 在 generators 和 generate() 中重复声明 | generators 属性和 generate() 方法同时实例化 CMakeToolchain | 从 generators 移除 CMakeToolchain，仅在 generate() 中使用 |
| 3 | test_package 报 "Library 'vampire' not found" | test_package 试图链接 vampire 为库，但 vampire 是二进制工具 | package_info 改为 bindirs=["bin"]，test_package 改为 smoke test |
| 4 | AttributeError: deps_cpp_info 不存在 | Conan 1 API 在 Conan 2 中已移除 | 改用 self.dependencies["vampire"].package_folder |
| 5 | conandata.yml sha256 为占位符 | 自动生成未计算校验和 | 手动计算: 3d991c914e9f400641d8b2e4362065c218c0ecb08079b96b0da1714aa6842520 |
| 6 | License 标记为 MIT | 模板默认值 | 修正为 BSD-3-Clause |
| 7 | E092: CMake 不识别 HarmonyOS 平台 (旧版 conan 2.12.0) | CMake 无 HarmonyOS platform module | 旧方案: 手动设置 CMAKE_SYSTEM_NAME=Linux；新方案: 升级到 OHOS 适配版 conan 2.29.1 后自动映射，无需手动覆盖 |
| 8 | CI L0e 检查失败: test_package/MANIFEST.yml 缺失 | CI 强制要求声明上游测试来源 | 创建 test_package/MANIFEST.yml，声明 vampire 无上游测试 + smoke test 内容 |
| 9 | conanfile.py 中 CMAKE_SYSTEM_NAME=Linux 覆盖与新版 conan 冲突 | OHOS 适配版 conan 2.29.1 自动映射 OHOS→HarmonyOS，手动覆盖会导致冲突 | 移除 CMAKE_SYSTEM_NAME 和 CMAKE_SYSTEM_PROCESSOR 手动覆盖 |

## 源码修改

无。本次编译未修改任何源码文件，所有适配通过 CMake 参数和 Conan 配方完成。

## 依赖版本

- 编译器: Clang 15.0.4 (路径: /data/service/hnp/bin/clang)
- CMake: 系统自带
- Conan: 2.12.0
- 无外部依赖（Vampire 内嵌 CaDiCaL 2.1.3、Minisat）

## 验证结果

```bash
$ vampire --version
Vampire 5.0.1 (Release build, commit )
CaDiCaL: cadical-2.1.3

$ echo 'fof(test,conjecture,![X]:(p(X) => p(X))).' | vampire
% SZS status Theorem for vampire_test
% Refutation found. Thanks to Tanya!

$ file build/vampire
ELF executable, 64-bit LSB arm64, static, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/vampire | 24,963,072 字节 (~24MB) | 静态链接的 ARM64 可执行文件 |

## 注意事项

- Vampire 是定理证明器（二进制工具），不是库；Conan 配方中 package_info 使用 bindirs 而非 libs
- make -j1 编译约 200 个 C++ 源文件，耗时约 15.7 分钟，建议有条件时使用 -j4 或更高并行度
- 内嵌 CaDiCaL 2.1.3 SAT 求解器，无需外部 Z3 依赖（Z3 可选，缺失时自动跳过 SMT 支持）

---

**编译结束**: 2026-06-29 15:01
**最终状态**: published
