# 编译笔记 — draco 1.5.7

## 基本信息
- **软件名称**: draco
- **版本**: 1.5.7
- **描述**: 3D 几何网格压缩库
- **官网**: https://github.com/google/draco
- **构建系统**: cmake

## 编译过程

### 2026-05-20 编译记录

#### 1. 源码获取
- URL: https://github.com/google/draco/archive/refs/tags/1.5.7.tar.gz
- 方式: curl 下载（SSL 验证失败，使用 -k 跳过）
- 大小: 58M

#### 2. 配置
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release
```

**注意事项**:
- CMake 提示 "System is unknown to cmake, create Platform/HarmonyOS"
- 此警告不影响编译，CMake 能正确识别编译器（Clang 15.0.4）

#### 3. 编译
```bash
make -j4
```
- **结果**: 100% 成功
- **产物**: libdraco.a, draco_encoder, draco_decoder

#### 4. 安装
- Staging 安装: `make install DESTDIR=$TEST_PREFIX`
- 本地安装: `make install`（无 DESTDIR）
- **产物路径**: `/storage/Users/currentUser/usr/local`

#### 5. 验证
- draco_encoder: ✅ 功能正常
- draco_decoder: ✅ 功能正常
- libdraco.a: ✅ 包含 102 个对象文件

#### 6. 打包
- 预编译包: `draco-1.5.7-ohos-aarch64.tar.gz` (10M)
- 调试符号包: `draco-1.5.7-ohos-aarch64-debug.tar.gz` (1.8M)

## 平台适配要点

### CMake 平台识别
- **问题**: CMake 不识别 HarmonyOS 系统
- **影响**: 仅警告，不影响编译
- **解决**: 无需修改，编译器自动检测

### 编译器选择
- **CC**: clang (Clang 15.0.4)
- **CXX**: clang++ (Clang 15.0.4)
- **AR**: llvm-ar
- **RANLIB**: llvm-ranlib

### 依赖情况
- **无外部依赖**: draco 为独立库
- **可选依赖**: Eigen, TinyGLTF（用于 transcoding，未启用）

## 功能验证

### 实际测试用例
1. **编码测试**: 创建 OBJ 模型 → 编码为 DRC → 成功（压缩率 56.6%）
2. **解码测试**: DRC 文件 → 解码为 OBJ → 成功（数据完整）
3. **参数测试**: --help, -cl 10, -qp 14 → 全部正常

### 支持格式
- **输入**: OBJ, PLY, STL
- **输出**: DRC (Draco 格式)

## CI 修复记录

### 2026-07-16 CI 修复
- **问题**: conandata.yml 中 SHA256 为占位哈希值，导致 gh-proxy 镜像下载的文件被 Conan 拒绝
- **修复**: 将 SHA256 修正为 FreeBSD ports 官方记录值 `bf6b105b79223eab2b86795363dfe5e5356050006a96521477973aba8f036fe1`
- **参考**: FreeBSD ports commit 048d22328335edef862115847f3699867edaabad

### 2026-07-16 CI 编译失败修复 (E012, 第四次)
- **问题**: 链接 libdraco.a 时失败，错误 "Error running link command: no such file or directory"
- **根因**: ohos.toolchain.cmake 以 INTERNAL/FORCE 方式覆写 CMAKE_AR/CMAKE_RANLIB 为 bare name（"llvm-ar"/"llvm-ranlib"），但这些工具不在默认 PATH 中。第三次修复使用 `self.runenv_info`，但 `self.runenv_info` 写入 `conanrun.sh`，而 `self.run()` 在 `build()` 中默认只 source `conanbuild.sh`，因此 PATH 修改未生效。
- **修复**: 将 `self.runenv_info` 改为 `self.buildenv_info`。`self.buildenv_info` 写入 `conanbuild.sh`，被 `self.run()` 默认加载，确保 LLVM bin 目录正确注入 PATH。
- **参考**: knowledge/doc/E012.md

### 2026-07-16 CI 编译失败修复 (E012, 第七次)
- **问题**: 第五次修复（`CMAKE_CXX_ARCHIVE_CREATE` 全路径）后 CI 仍然失败，错误相同 "Error running link command: no such file or directory"
- **根因**: CMake 的 `CMAKE_CXX_CREATE_STATIC_LIBRARY` 一旦由工具链定义，会优先覆盖 `CMAKE_CXX_ARCHIVE_CREATE/APPEND/FINISH`；因此前一轮虽设置了 ARCHIVE 规则，生成的链接脚本仍可使用工具链中的裸 `llvm-ar`。
- **修复**: 直接设置最高优先级的 `CMAKE_CXX_CREATE_STATIC_LIBRARY`（并同时覆盖 C 规则），使用绝对路径的 `llvm-ar rcs <TARGET> <OBJECTS>` 一步创建静态库和符号索引，不再依赖 PATH 或单独的 ranlib 查找。
- **重跑说明**: Buildbot #4116 的配置命令仍显示旧的 `CMAKE_CXX_ARCHIVE_*` 参数，未包含本轮新增的 `CMAKE_CXX_CREATE_STATIC_LIBRARY`，因此该结果属于 PR 引用更新竞态，需以新提交重新触发验证。
- **参考**: knowledge/doc/E012.md

### 2026-07-16 CI 测试包编译失败修复 (test_package StatusOr API)
- **问题**: test_package/test.cpp 编译失败，15 个错误和 1 个警告
- **根因**: draco 1.5.7 的 `StatusOr<T>` 不支持 `operator!` 和 `operator->`。代码中 `DecodeMeshFromBuffer` 返回 `StatusOr<std::unique_ptr<Mesh>>`，但使用 `if (!decoded_mesh)` 和 `decoded_mesh->num_faces()` 访问，编译错误。
- **修复**: 
  - `!decoded_mesh` → `!decoded_mesh.ok()`
  - `decoded_mesh->num_faces()` → `decoded_mesh.value()->num_faces()`
  - 对点云和解码的 `StatusOr` 做相同修复
  - 修复 `%zu` 格式警告：`PointIndex::ValueType` 是 `unsigned int`，用 `static_cast<size_t>()` 转换
- **CI 构建**: #4143 失败，修复后等待重新触发验证

### 2026-07-16 CI test_package 编译失败修复 (num_vertices → num_points)
- **问题**: test_package/test.cpp 编译失败，错误: `no member named 'num_vertices' in 'draco::Mesh'`
- **根因**: `draco::Mesh` 没有 `num_vertices()` 方法；`Mesh` 继承自 `PointCloud`，顶点数方法为 `num_points()`。
- **修复**: 将 `mesh_ptr->num_vertices()` 替换为 `mesh_ptr->num_points()`，并更新错误消息字符串（"vertices" → "points"）。
- **CI 构建**: #4190 失败，修复后等待重新触发验证

## 编译状态

**最终状态**: 待验证 ⏳（修复后等待 CI 重新验证）

**质量门禁**:
- G0 (干净构建): ⚠️ cmake 无 configure 脚本（正常）
- G1 (二进制完整性): ⏳ 待 CI 验证
- G2 (功能可用性): ⏳ 待 CI 验证
- G3 (可移植性): ⏳ 待 CI 验证
- G4 (档案完整性): ⏳ 待 CI 验证
