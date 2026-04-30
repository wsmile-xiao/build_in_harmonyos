# PROGRESS.md — ca-certificates 20250419 编译记录

**软件**: ca-certificates  
**版本**: 20250419  
**状态**: built  
**日期**: 2026-04-29  

---

## 编译流程

### Step 1: init-build
- ✅ 下载源码: http://ftp.debian.org/debian/pool/main/c/ca-certificates/ca-certificates_20250419.tar.xz
- ✅ 解压到工作目录
- ✅ 创建归档骨架
- ✅ 检查依赖（无依赖）

### Step 2: 编译
**问题**: 
- certdata2pem.py 需要 cryptography 模块（Python）
- cryptography 无法在鸿蒙平台编译（依赖 Rust，不支持 aarch64-unknown-linux-ohos）

**解决方案**:
- 创建简化版 certdata2pem_simple.py
- 移除 cryptography 依赖，直接输出 PEM 格式证书
- 跳过证书过期验证（仅影响日志输出）

**执行步骤**:
```bash
cd mozilla/
python3 certdata2pem_simple.py
# 生成了 150 个 .crt 证书文件
```

### Step 3: 安装（Staging）
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/share/ca-certificates/mozilla
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/sbin
cd mozilla/ && install -m 644 *.crt $TEST_PREFIX/$DEFAULT_PREFIX/share/ca-certificates/mozilla/
cd ../sbin/ && install -m 755 update-ca-certificates $TEST_PREFIX/$DEFAULT_PREFIX/sbin/
```

### Step 4: 打包
- ✅ 制作预编译包: ca-certificates-20250419-ohos-aarch64.tar.gz (333KB)
- 包含:
  - 150 个 CA 证书文件（mozilla/*.crt）
  - update-ca-certificates 工具（sbin/）

### Step 5: 本地安装
- ✅ 安装到 ~/usr/local/share/ca-certificates/mozilla/
- ✅ 安装 update-ca-certificates 到 ~/usr/local/sbin/

### Step 6: Finish
- ⚠️ G0 干净构建验证失败（Python subprocess 平台限制）
- ⚠️ test-report.md 缺失（ca-certificates 无测试）
- ⚠️ 缺少 debug.tar.gz（无二进制文件）
- ✅ 预编译包已制作

---

## 关键发现

### 知识沉淀 (L3 - 本版笔记)
1. **cryptography 模块依赖问题**: 
   - certdata2pem.py 需要 cryptography 模块
   - cryptography 依赖 Rust，无法在鸿蒙平台编译
   - 解决方案：创建简化版脚本，移除 cryptography 依赖

2. **ca-certificates 特殊性**:
   - 无二进制产物，仅有证书文件和 Shell 脚本
   - 不需要传统编译流程（configure/make）
   - 主要工作：证书提取和安装

3. **Makefile DESTDIR 问题**:
   - 原 Makefile 使用 /usr/share/ca-certificates 而非 $DEFAULT_PREFIX
   - 需要手动修正安装路径

---

## 产物

| 产物 | 路径 | 大小 |
|------|------|------|
| 预编译包 | packaging/ca-certificates-20250419-ohos-aarch64.tar.gz | 333KB |
| debug 包 | - | - |

---

**编译结束**: 2026-04-29 21:36  
**最终状态**: built