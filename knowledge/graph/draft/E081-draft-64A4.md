# E081: HarmonyOS CMake相对路径链接行为

## 问题概述

**类别**：L1平台真理（影响所有软件）
**优先级**：P1-阻塞（违反零介入原则）
**影响范围**：所有使用CMake构建的、包含内部库链接的项目

## 错误特征

### 错误日志示例

```bash
Error loading shared library ../libheif/libheif.so: (needed by /path/to/bin/heif-info)
Error relocating /path/to/bin/heif-info: heif_get_version: symbol not found
```

### 验证命令

```bash
strings $BIN | grep '\.\./.*\.so'
# 输出：../libheif/libheif.so（错误的相对路径）

strings $BIN | grep 'lib.*\.so'
# 标准Linux：libheif.so（正确的SONAME）
```

## 根本原因

HarmonyOS平台的CMake在链接同一项目内的库时，使用**相对路径作为库名称**，而非标准的SONAME。

**技术细节**：
- **标准Linux CMake**：链接时使用`libheif.so`（SONAME）
- **HarmonyOS CMake**：链接时使用`../libheif/libheif.so`（相对路径）
- **RPATH设置无效**：问题不是RPATH，而是链接时的库名称本身就是相对路径

**readelf对比**：
```bash
# 标准Linux
readelf -d libheif.so | grep SONAME
# 0x000000000000000e (SONAME)             Library soname: [libheif.so]

# HarmonyOS
readelf -d libheif.so | grep SONAME
# 无输出（SONAME字段缺失）
```

## 受影响的软件

**已知案例**：
- **libheif 1.17.6**：heif-info、heif-convert、heif-enc依赖`../libheif/libheif.so`
- **其他潜在受影响软件**：所有使用CMake构建、包含内部库链接的项目

**典型场景**：
```
project/
  ├── lib/CMakeLists.txt    → 生成lib/libproject.so
  └── tools/CMakeLists.txt  → 链接lib/libproject.so
                             → 在HarmonyOS上：依赖../lib/libproject.so
                             → 在Linux上：依赖libproject.so
```

## 解决方案

### 方案1：临时解决方案（Phase 3可用）

**适用场景**：快速交付，接受partial状态

```bash
# 创建额外的libname/目录结构
mkdir -p $PREFIX/libname
cp $PREFIX/lib/libname.so $PREFIX/libname/libname.so

# 可执行文件运行方式
cd $PREFIX/bin && ./tool --version
```

**优点**：
- 简单快速
- 库文件可用（pkg-config正常）
- 可执行文件可运行（在bin目录下）

**缺点**：
- 目录结构不标准（libname/额外目录）
- 违反零介入原则（需特定目录运行）
- 无法制作预编译包（结构非标准）

### 方案2：长期解决方案（需平台适配）

**研究方向**：
1. 修改HarmonyOS Platform/HarmonyOS.cmake配置
2. 修改CMake模块处理相对路径依赖
3. 在打包流程中自动修复非标准依赖路径

**代码修改示例**（待验证）：
```cmake
# 在libheif/libheif/CMakeLists.txt中添加
set_target_properties(heif PROPERTIES
    OUTPUT_NAME "heif"  # 确保输出名称
    PREFIX "lib"        # 确保前缀
    SOVERSION ${PROJECT_VERSION_MAJOR}
    LINK_FLAGS "-Wl,--soname,libheif.so"  # 强制SONAME（待验证）
)
```

### 方案3：打包流程处理

在打包脚本中自动处理：
```python
# package.py中添加
def fix_relative_path_dependency(binary_path, lib_name):
    """修复相对路径依赖"""
    # 使用patchelf修改依赖（需要权限）
    # 或在打包时创建正确的目录结构
```

## 验证步骤

### 1. 检查问题是否存在

```bash
strings $PREFIX/bin/tool | grep '\.\./.*\.so'
# 如果输出：../libname/libname.so → 存在问题
# 如果输出：libname.so → 正常
```

### 2. 测试临时解决方案

```bash
mkdir -p $PREFIX/libname
cp $PREFIX/lib/libname.so $PREFIX/libname/
cd $PREFIX/bin && ./tool --version
```

### 3. pkg-config验证

```bash
pkg-config --modversion libname
pkg-config --libs libname
pkg-config --cflags libname
```

## 与其他错误模式的区别

| 错误模式 | 问题类型 | 解决方法 | 本问题 |
|---------|---------|---------|--------|
| E007（config.guess） | 平台识别 | 修改配置文件 | ❌ 源码修改无效 |
| E002（/tmp只读） | 环境限制 | 使用$TMPDIR | ❌ 环境变量无效 |
| E046（chmod失败） | SELinux限制 | 记录为限制 | ✅ 类似（平台限制） |
| **E081（本问题）** | CMake链接行为 | 平台适配 | ⭐ 需要平台适配 |

**关键差异**：
- E007等可以通过修改源码/配置解决
- E081是CMake平台行为，无法通过常规修改解决

## 知识提取价值

**为什么这是L1平台真理**：
- 影响所有使用CMake构建的项目
- 无法通过软件级修改解决
- 需要平台级适配或打包流程处理

**对后续工作的建议**：
1. 在skill中添加HarmonyOS CMake特殊行为检测
2. 在打包流程中自动处理相对路径依赖
3. 创建HarmonyOS CMake配置最佳实践文档

## 参考资料

- libheif 1.17.6编译案例：archives/l/libheif/1.17.6/notes.md
- CMake文档：https://cmake.org/cmake/help/latest/
- HarmonyOS平台特性：（待补充）

---

**状态**：草稿（需主编审核）
**创建时间**：2026-05-19
**贡献者**：64A4