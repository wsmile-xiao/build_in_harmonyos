# aws-c-io 0.26.3 Release Note

## 基本信息
- **软件名称**: aws-c-io
- **版本**: 0.26.3
- **发布日期**: 2026-04-24
- **编译状态**: partial
- **目标平台**: ohos-aarch64

## 编译说明

### 编译配置
本版本使用 `-DBYO_CRYPTO=ON` 选项编译，禁用了 s2n TLS 库依赖。

### 依赖关系
本版本依赖以下已编译完成的库：
- aws-c-common 0.12.6
- aws-c-cal 0.9.13  
- aws-c-compression 0.3.2

### 编译产物
- **静态库**: libaws-c-io.a (422KB)
- **预编译包**: aws-c-io-0.26.3-ohos-aarch64.tar.gz (703KB)
- **安装脚本**: install-aws-c-io-0.26.3.sh

### 功能说明
aws-c-io 是 AWS C SDK 的 IO 库，提供：
- Event loop 实现（基于 Linux epoll）
- Socket 和 channel 管理
- Host resolver
- TLS channel handler（本版本已禁用）

## 安装方法

### 使用预编译包安装
```bash
# 解压预编译包
tar xzf aws-c-io-0.26.3-ohos-aarch64.tar.gz

# 运行安装脚本
./install-aws-c-io-0.26.3.sh
```

### 验证安装
```bash
# 检查库文件
ls ~/usr/local/lib/libaws-c-io.a

# 检查头文件
ls ~/usr/local/include/aws/io/

# 检查 CMake 配置
ls ~/usr/local/lib/cmake/aws-c-io/
```

## 已知限制

### 测试状态
- 测试套件未执行（BUILD_TESTING=OFF）
- 功能验证通过质量门禁（G1-G4）

### TLS 功能
- 本版本禁用了 s2n TLS 实现
- 如需 TLS 功能，需重新编译并安装 s2n 库

## 使用建议

### 作为依赖使用
在其他 AWS C 库的 CMake 配置中添加：
```cmake
find_package(aws-c-io REQUIRED)
target_link_libraries(your_target PRIVATE AWS::aws-c-io)
```

### 注意事项
- 确保依赖库（aws-c-common, aws-c-cal, aws-c-compression）已正确安装
- 禁用 TLS 功能可能会影响部分 AWS 服务连接

---
**编译者**: OpenHarmony Compile Agent
**审核状态**: 待审核