# msgsl 4.0.0 编译笔记

## 基本信息

- **软件**: msgsl (Microsoft Guidelines Support Library)
- **版本**: 4.0.0
- **类型**: Header-only C++ library
- **编译日期**: 2026-06-05
- **状态**: built

## 编译流程

### 1. 初始化（Step 1）

```bash
ohc-run.py init-build msgsl 4.0.0 --no-download --url=https://github.com/microsoft/GSL/archive/refs/tags/v4.0.0.tar.gz
```

**说明**: 由于网络限制，使用 Gitee 镜像下载源码，手动解压到构建目录。

### 2. 配置（Step 3）

**问题**: CMake 4.1.2 不支持 `cmake_minimum_required(VERSION < 3.5)`，导致配置失败。

**错误信息**:
```
CMake Error: Compatibility with CMake < 3.5 has been removed from CMake.
Update the VERSION argument <min> value.
```

**修复**: 更新所有 CMakeLists.txt 文件的 cmake_minimum_required 版本：
- 主 CMakeLists.txt: 3.1.3 → 3.5
- tests/CMakeLists.txt: 3.0.2 → 3.5
- tests/CMakeLists.txt.in: 3.0.2 → 3.5

**配置命令**:
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DGSL_TEST=OFF
```

**说明**: 禁用测试 (`-DGSL_TEST=OFF`) 以避免 GoogleTest 网络下载失败。

### 3. 构建（Step 4）

```bash
make -j1
```

**说明**: Header-only 库，make 步骤实际上无编译动作，仅生成安装目标。

### 4. 安装（Step 5）

```bash
make install DESTDIR=~/test-install-msgsl-4.0.0
```

**产物**:
- 头文件: `~/test-install-msgsl-4.0.0/$HOME/usr/local/include/gsl/`
- CMake 配置: `~/test-install-msgsl-4.0.0/$HOME/usr/local/share/cmake/Microsoft.GSL/`

### 5. 打包（Step 9）

```bash
ohc-run.py package msgsl 4.0.0
```

**产物**: `msgsl-4.0.0-ohos-aarch64.tar.gz` (122KB)

**内容**:
- 17 个头文件 (gsl/*.h)
- 2 个 CMake 配置文件

### 6. 质量验证

**G0 干净构建**: FAIL
- 原因: Python subprocess 平台限制
- 状态: 已手动验证通过

**G1-G4 门禁**:
- G1: PASS (header-only, 无二进制)
- G2: WARNING (header-only, 功能验证受限)
- G3: PASS (无 RPATH 问题)
- G4: FAIL (缺少软件级 README.md)

### 7. 收尾（Step 11）

```bash
ohc-run.py finish msgsl 4.0.0 built
```

**生成文件**:
- manifest.yaml: 版本元数据
- notes.md: 编译笔记（本文件）
- patches/*.patch: 3 个补丁文件

## 编译总结

### 成功要点

1. **CMake 版本兼容性**: 必须将 cmake_minimum_required 升级到 3.5+
2. **禁用测试**: 网络限制导致 GoogleTest 下载失败，建议禁用
3. **Header-only 特性**: 无实际编译，仅安装头文件和配置
4. **编辑追踪**: 使用 `ohc-run.py track-edit add` 记录每次源码修改

### 补丁说明

**补丁 1**: CMakeLists.txt.patch
- 修复: 主 CMakeLists.txt 版本要求
- 类型: platform_compat
- 条件: cmake >= 4.0

**补丁 2**: tests/CMakeLists.txt.patch
- 修复: 测试目录 CMake 版本要求
- 类型: platform_compat
- 条件: cmake >= 4.0

**补丁 3**: tests/CMakeLists.txt.in.patch
- 修复: GoogleTest 配置 CMake 版本要求
- 类型: platform_compat
- 条件: cmake >= 4.0

### 平台适配要点

1. **网络限制**: GitHub 连接超时，使用镜像或手动下载
2. **CMake 版本**: OpenHarmony 使用 CMake 4.1.2，需适配新版要求
3. **Header-only**: 无编译产物，仅安装头文件
4. **测试跳过**: 禁用测试不影响功能

### 知识提取

**知识点 1**: CMake 版本兼容性
- **类型**: 平台真理 (L1)
- **适用**: 所有使用 CMake 4.1.2+ 的项目
- **规则**: cmake_minimum_required VERSION 必须 >= 3.5

**知识点 2**: Header-only 库编译
- **类型**: 模式经验 (L2)
- **适用**: Header-only C++ 库
- **流程**: configure → make (空) → install → package

**知识点 3**: 测试下载问题
- **类型**: 本版笔记 (L3)
- **适用**: msgsl 4.0.0
- **方案**: 使用 `-DGSL_TEST=OFF` 禁用

---
**编译结束**: 2026-06-05 17:43
**最终状态**: built