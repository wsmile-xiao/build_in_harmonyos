# olm 3.2.16 — OpenHarmony 编译记录

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | olm (Matrix 加密库) |
| 版本 | 3.2.16 |
| 构建系统 | CMake |
| 目标平台 | ohos-aarch64 |
| 状态 | ⚠️ partial (已弃用) |
| 编译日期 | 2026-04-24 |

## 源码信息
- **源码地址**: https://gitlab.matrix.org/matrix-org/olm/-/archive/3.2.16/olm-3.2.16.tar.gz
- **许可证**: Apache 2.0

## 编译指导

### 环境要求
- HarmonyOS/OpenHarmony aarch64 SDK
- CMake >= 3.10
- C++ 编译器（支持 C++11）

### 构建命令
```bash
# 解压源码
tar xzf olm-3.2.16.tar.gz && cd olm-3.2.16

# 配置
cmake -H. -Bbuild \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_SDK/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_BUILD_TYPE=Release

# 编译
cmake --build build

# 安装到临时目录
cmake --install build --prefix $TEST_PREFIX
```

## 补丁清单
无补丁文件

## 编译产物

### 预编译包
- `olm-3.2.16-ohos-aarch64.tar.gz` - 发布包
- `olm-3.2.16-ohos-aarch64-debug.tar.gz` - 调试符号包
- 包大小: 382.1KB

### 库文件
- `libolm.so.3.2.16` - 共享库
- `libolm.so.3.2.16.debug` - 调试符号

### 头文件
- `olm/olm.h` - 主头文件
- `olm/inbound_group_session.h` - 入站组会话
- `olm/outbound_group_session.h` - 出站组会话
- `olm/pk.h` - 公钥加密
- `olm/sas.h` - 短认证字符串
- 其他辅助头文件

### 安装脚本
- `install-olm-3.2.16.sh` - 自动安装脚本

## 已知限制
- ⚠️ 该版本已标记为弃用状态，仅保留编译记录
- 功能验证有限，生产环境不推荐使用
- 无完整的测试套件验证

## 功能验证
```bash
# 验证库文件
file $TEST_PREFIX/lib/libolm.so.3.2.16
# 输出: ELF 64-bit LSB shared object, ARM aarch64, ...

# 验证符号链接
ls -l $TEST_PREFIX/lib/libolm.so*
# 应显示 libolm.so -> libolm.so.3 -> libolm.so.3.2.16

# 验证头文件
ls $TEST_PREFIX/include/olm/*.h
```

## 质量报告
- **质量门禁**: ✅ PASS
- **G1 二进制完整性**: PASS
- **G2 功能性**: PASS (⚠️ 1 warning)
- **G3 可移植性**: PASS
- **G4 归档完整性**: PASS

## 相关文档
- [编译进度](./PROGRESS.md)
- [测试报告](./reports/test-report.md)
- [质量报告](./reports/quality-report.md)
- [Skill反馈](./reports/skill-feedback.md)
