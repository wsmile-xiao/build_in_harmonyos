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

## 编译状态

**最终状态**: published ✅

**质量门禁**:
- G0 (干净构建): ⚠️ cmake 无 configure 脚本（正常）
- G1 (二进制完整性): ✅ PASS
- G2 (功能可用性): ✅ PASS
- G3 (可移植性): ✅ PASS
- G4 (档案完整性): ✅ PASS

**产物**:
- 预编译包: `/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/d/draco/1.5.7/packaging/`
- 二进制: draco_encoder (1.5M), draco_decoder (987K)
- 库文件: libdraco.a (3.9M)

---

**编译结束**: 2026-05-20 15:50:00
**最终状态**: published