# BearSSL — OpenHarmony 编译档案

## 软件简介

BearSSL 是一个优化的 SSL/TLS 库，专注于安全性和小代码体积。它实现了 SSL/TLS 协议栈，适用于嵌入式系统和资源受限环境。

**主要特性**：
- 纯 C 实现，无外部依赖
- 小代码体积，适合嵌入式设备
- 支持 TLS 1.0/1.1/1.2
- 完整的加密算法套件
- X.509 证书验证
- 静态链接为主，避免动态库依赖

## 可用版本

| 版本 | 状态 | 构建系统 | 补丁数 | 说明 |
|------|------|----------|--------|------|
| 0.6 | ⚠️ partial | custom Makefile | 0 | 无标准 configure/make install |

> 状态说明：✅ success = 完全通过 | ⚠️ partial = 部分通过可用 | ❌ failed = 编译失败

## 编译指导

### 构建系统特点

BearSSL 使用**自定义 Makefile 系统**，无标准的 `configure` 脚本和 `make install` 目标：
- 配置文件位于 `conf/` 目录
- 使用 `make CONF=<config>` 选择配置
- 需要手动安装头文件和静态库

### 编译命令（以 0.6 为例）

```bash
# 解压源码
tar xzf bearssl-0.6.tar.gz
cd bearssl-0.6

# 使用 OpenHarmony 配置编译
make CONF=Ohos

# 手动安装（静态库模式）
mkdir -p $HOME/usr/local/lib $HOME/usr/local/include/bearssl
cp build/Ohos/libbearssl.a $HOME/usr/local/lib/
cp inc/*.h $HOME/usr/local/include/bearssl/
```

### 测试验证

```bash
# 运行加密算法测试
./build/Ohos/testcrypto all

# 运行 X.509 证书验证测试
./build/Ohos/testx509

# 查看平台特性
./build/Ohos/brssl impl
```

## 补丁清单

当前版本无需补丁，源码原生支持 OpenHarmony 平台。

## 已知限制

1. **无标准安装流程**：BearSSL 无 `make install`，需手动复制文件
2. **DLL API 不稳定**：官方不推荐动态库模式，编译时禁用
3. **平台特定优化缺失**：AES_x86ni、AES_pwr4 等优化不可用（预期行为）
4. **静态链接为主**：适合嵌入式场景，动态链接需自行处理

## 功能验证

| 组件 | 状态 | 说明 |
|------|------|------|
| libbearssl.a | ✅ 可用 | 静态库编译成功 |
| brssl 工具 | ✅ 可用 | 命令行 SSL 工具 |
| testcrypto | ✅ 通过 | 所有加密算法测试通过 |
| testx509 | ✅ 通过 | 57 个证书验证测试通过 |

## 依赖关系

- **编译时依赖**：无外部依赖（纯 C 实现）
- **运行时依赖**：无（静态链接模式）

## 相关资源

- [BearSSL 官网](https://www.bearssl.org/)
- [BearSSL GitHub](https://github.com/ctz/bearssl)
- [BearSSL 文档](https://www.bearssl.org/api.html)
