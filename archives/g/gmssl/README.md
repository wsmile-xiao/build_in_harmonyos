# gmssl — OpenHarmony 编译记录

## 软件简介

GmSSL 是支持国密算法的密码库，实现了中国国家密码标准（SM2/SM3/SM4等）和 OpenSSL 兼容的 API 接口。

### 核心特性
- 支持 SM2 椭圆曲线公钥密码算法
- 支持 SM3 密码杂凑算法
- 支持 SM4 分组密码算法
- 支持 SM9 标识密码算法
- OpenSSL API 兼容层
- 国密证书和 TLS 协议支持

### 项目信息
- **源码**: https://github.com/guanzhi/GmSSL
- **许可证**: Apache 2.0
- **语言**: C/C++

## 编译指导

### 依赖要求
- CMake 3.0+
- C 编译器（支持 C11）
- Perl（部分构建步骤）

### 编译命令
```bash
cmake -DCMAKE_TOOLCHAIN_FILE=<harmony-toolchain.cmake> \
      -DCMAKE_INSTALL_PREFIX=/data/data/com.openharmony.compiler/files/usr/local \
      -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install
```

### 注意事项
- 必须使用 CMake 工具链文件指定 HarmonyOS 平台
- 设置 `CMAKE_SYSTEM_NAME=Linux` 实现平台兼容
- 手动指定编译器和工具链路径

## 版本列表

| 版本 | 状态 | 编译日期 | 补丁数 | 备注 |
|------|------|----------|--------|------|
| 3.1.1 | ⚠️ partial | 2026-04-24 | 0 | 测试因 ELF 签名限制无法运行 |

## 已知限制

### HarmonyOS 特定限制
1. **ELF 签名要求**: 所有可执行文件和共享库必须签名
   - 编译产物需要通过 `ohc-run.py sign-elf` 工具签名
   - 测试套件因签名限制无法运行
   - 预编译包制作阶段会自动处理签名

2. **平台识别**: CMake 无法直接识别 HarmonyOS
   - 需要创建工具链文件
   - 设置 `CMAKE_SYSTEM_NAME=Linux` 进行兼容

### 功能验证限制
- 测试套件 `make test` 无法直接运行（需要签名）
- 功能验证需要通过签名后的预编译包进行

## 功能验证

### 基本功能测试
```bash
# 安装预编译包后
gmssl version
gmssl sm2 -help
gmssl sm3 -help
gmssl sm4 -help
```

### 国密算法测试
```bash
# SM3 杂凑算法
echo "test" | gmssl sm3

# SM4 对称加密
gmssl sm4 -e -K 0123456789abcdeffedcba9876543210 -in plaintext.txt -out ciphertext.bin

# SM2 签名验证
gmssl sm2 -sign -in data.txt -key sm2.key
```

## 更多信息

详细编译记录见各版本目录下的 `README.md`、`PROGRESS.md` 和 `reports/`。
