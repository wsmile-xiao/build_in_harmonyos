# ripgrep 15.1.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-05-22
- 编译器: rustc 1.95.0, cargo 1.95.0
- 状态: built

## 编译步骤

### 1. 环境准备
- Rust工具链已安装（rustc 1.95.0, cargo 1.95.0）
- 配置cargo使用稀疏索引（sparse registry）加速依赖下载
- 设置SSL_CERT_FILE环境变量指向CA证书

### 2. 源码下载
- 从GitHub下载ripgrep 15.1.0源码
- URL: https://github.com/BurntSushi/ripgrep/archive/refs/tags/15.1.0.tar.gz
- 使用wget下载，文件大小600KB

### 3. 编译过程
- 使用`cargo build --release`编译
- 依赖下载：使用稀疏索引成功下载所有crate依赖（约30个crate）
- 编译时间：约7分钟（6分59秒）
- 无需修改源码，直接编译成功

### 4. 安装和验证
- 手动复制二进制文件到staging目录和本地目录
- 验证：`rg --version`成功显示版本信息
- 功能测试：ripgrep可正常执行搜索

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cargo索引更新慢（清华镜像排队） | 国内镜像访问限制 | 改用稀疏索引（sparse registry）+ SSL证书配置 |
| 2 | SSL证书错误 | cargo无法访问crates.io | 设置SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 3 | cargo install失败（SSL错误） | cargo install没有继承SSL环境变量 | 手动复制编译产物而非使用cargo install |
| 4 | manifest缺少build_system字段 | verify-build检查顶级字段 | 添加顶级build_system: cargo字段 |

## 源码修改

无源码修改，ripgrep 15.1.0直接编译成功。

## 依赖版本

- rustc: 1.95.0 (built from a source tarball)
- cargo: 1.95.0 (built from a source tarball)
- crates: 约30个（包括aho-corasick, regex-syntax, serde_json等）
- SSL证书: 121个根证书

## 验证结果

```bash
$ rg --version
ripgrep 15.1.0

features:-pcre2
simd(compile):+NEON
simd(runtime):+NEON

PCRE2 is not available in this build of ripgrep.
```

质量门禁结果：
- G1 (二进制完整性): ✅ PASS
- G2 (功能可用性): ✅ PASS (rg --version成功)
- G3 (可移植性): ✅ PASS (Rust静态二进制，无需RPATH)
- G4 (档案完整性): ✅ PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ripgrep-15.1.0-ohos-aarch64.tar.gz | 6.0MB | 预编译主包（strip后） |
| ripgrep-15.1.0-ohos-aarch64-debug.tar.gz | 19MB | 调试符号包 |
| rg (二进制) | 25MB (编译) / 6MB (strip后) | ripgrep可执行文件 |

## Rust编译特殊说明

### 编译时间
- 素引更新：约1-2分钟（使用稀疏索引）
- 依赖下载：约2分钟
- 实际编译：约4-5分钟
- 总耗时：约7分钟

### Cargo配置要点
```toml
[registries.crates-io]
protocol = "sparse"  # 使用稀疏索引加速

[net]
git-fetch-with-cli = true  # 使用git命令获取依赖
retry = 5  # 失败重试5次

[http]
timeout = 60  # HTTP超时60秒
```

### SSL证书配置
必须设置SSL_CERT_FILE环境变量，否则cargo无法访问crates.io：
```bash
export SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem
```

### Rust静态编译优势
- 无需RPATH设置（G3 PASS）
- 无动态库依赖
- 二进制自包含
- 跨平台可移植性强

## 注意事项

1. **Cargo索引更新**：首次编译时需要更新crates.io索引，建议使用稀疏索引
2. **SSL证书**：必须配置SSL_CERT_FILE，否则无法下载crate依赖
3. **编译时间**：Rust编译可能需要较长时间，建议耐心等待
4. **无PCRE2**：此编译版本不支持PCRE2正则表达式（需要额外依赖）
5. **SIMD加速**：自动启用NEON SIMD加速（compile和runtime）

---
**编译结束**: 2026-05-22 17:15
**最终状态**: built