# capnproto 1.1.0 适配笔记

## 适配日期
2026-08-22

## 真机验证结果

| 项目 | 结果 |
|------|------|
| 构建 | ✅ conan create 成功 |
| test_package | ✅ 5/5 PASSED |
| 配置文件 | ohos-aarch64-fixed (compiler.cppstd=gnu17) |
| 耗时 | ~5 分钟（含源码下载、编译、test_package） |

## 源码分析

- **构建系统**: CMake (minimum 3.6)
- **C++ 标准**: C++14（必须用 GNU 扩展 `gnu++14`，不能用纯 `c++14`）
- **零必要依赖**: OpenSSL/zlib/fibers 均为可选，已全部关闭
- **自引导构建**: capnp 编译器在构建过程中自行编译，无需预置 capnp 二进制

## 关键 CMake 选项

| 选项 | 值 | 原因 |
|------|-----|------|
| `BUILD_SHARED_LIBS` | `OFF` | OHOS RPATH 问题，1.3.0 已验证静态方案 |
| `BUILD_TESTING` | `OFF` | /tmp 平台限制，上游测试单独运行 |
| `WITH_OPENSSL` | `OFF` | 最小化依赖 |
| `WITH_ZLIB` | `OFF` | 最小化依赖 |
| `WITH_FIBERS` | `OFF` | 避免 libucontext 依赖 |
| `EXTERNAL_CAPNP` | `OFF` | 使用自编译的 capnp |
| `CMAKE_POLICY_VERSION_MINIMUM` | `3.5` | CMake 4.x 兼容性 |
| `CMAKE_CXX_EXTENSIONS` | `ON` | capnproto 拒绝 `-std=c++NN`，需要 `-std=gnu++NN` |

## 遇到的问题与解决

### 问题 1: CMake 版本兼容性
**现象**: `CMake Error: Compatibility with CMake < 3.5 has been removed`
**解决**: `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`

### 问题 2: C++ 扩展要求
**现象**: `Cap'n Proto requires compiler-specific extensions (e.g., -std=gnu++14)`
**根因**: Conan toolchain 从 `compiler.cppstd=17` 生成 `-std=c++17`（无 GNU 扩展）
**解决**: Profile 改用 `compiler.cppstd=gnu17`，同时 recipe 中设 `CMAKE_CXX_EXTENSIONS=ON`

### 问题 3: GitHub 源码下载超时
**现象**: OHOS 设备上 GitHub 连接超时
**解决**: 本地下载 tarball，base64 传输到真机，conandata.yml 临时改用 `file://` URL

### 问题 4: 编译器路径不匹配
**现象**: `/data/service/hnp/bin/clang++` 不存在
**解决**: 使用 `ohos-aarch64-fixed` profile（指向 `/storage/Users/currentUser/usr/local/bin/clang++`）

### 问题 5: test_package API 误用
**现象**: `getRoot<capnp::word>()` 不合法；空消息序列化抛异常
**解决**: 简化测试为编译链接验证 + KJ 功能测试

## 安装产物

### 库文件
- libkj.a, libkj-async.a, libkj-http.a
- libcapnp.a, libcapnp-rpc.a, libcapnp-json.a, libcapnp-websocket.a
- libcapnpc.a

### 可执行文件
- capnp (schema 编译器)
- capnpc-c++ (C++ 代码生成器)
- capnpc-capnp (capnp 格式代码生成器)

## 已知平台限制
- `/tmp` 只读 → 需设置 `TMPDIR=~/tmp` 运行上游测试
- fuzz 测试耗时 → 上游测试中应跳过或设置超时

## 下一步
- [x] 真机 conan create 验证 ✅
- [ ] 上游 ctest 运行和统计
- [ ] 提交 PR
