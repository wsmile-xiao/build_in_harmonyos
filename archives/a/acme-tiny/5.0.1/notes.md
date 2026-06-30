# acme-tiny 5.0.1 适配笔记

## 编译环境
- 构建系统: setuptools（Python 包）
- 编译日期: 2026-05-22
- 编译器: 无（纯 Python）
- 状态: built

## 编译步骤

### 1. 初始化构建环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build acme-tiny 5.0.1 \
  --url=file:///storage/Users/currentUser/acme-tiny-5.0.1.tar.gz --force
```

### 2. 解决版本检测问题
acme-tiny 使用 setuptools_scm 从 git 仓库检测版本。解压的 tarball 没有 .git 目录，导致版本检测失败。

解决方案：设置环境变量 `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ACME_TINY=5.0.1`

### 3. 安装到测试目录（staging）
```bash
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ACME_TINY=5.0.1
cd $BUILD_SRC_DIR
python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX
```

安装结果：
- bin/acme-tiny（可执行脚本）
- lib/python3.12/site-packages/acme_tiny.py（Python 模块）

### 4. 安装到本地并验证
```bash
python3 setup.py install --prefix=$DEFAULT_PREFIX
```

验证结果：
```bash
$DEFAULT_PREFIX/bin/acme-tiny --help
# 输出：usage: acme-tiny [-h] --account-key ACCOUNT_KEY --csr CSR --acme-dir ACME_DIR ...
# 功能正常

python3 -c "import acme_tiny; print('模块导入成功')"
# 输出：模块导入成功
```

### 5. 打包预编译包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build acme-tiny 5.0.1
python3 $SKILL_ROOT/scripts/ohc-run.py package acme-tiny 5.0.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | setuptools_scm 版本检测失败 | tarball 无 .git 目录 | 设置 SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ACME_TINY=5.0.1 |
| 2 | manifest.yaml 缺少 build_system | init-build 检测为 autotools | 手动修改为 system: setuptools, build_system: setuptools |

## 源码修改

无补丁，纯 Python 脚本无需修改源码。

## 依赖版本

- Python: 3.12.8
- OpenSSL: 3.5.6（命令行工具，运行时依赖）
- setuptools: 已安装
- setuptools_scm: 已安装

## 验证结果

### 质量门禁（G0-G4）

- G0（干净构建验证）：跳过（无补丁）
- G1（二进制完整性）：PASS（无二进制文件）
- G2（功能可用性）：PASS（1 warning：无二进制文件）
- G3（可移植性）：PASS（纯 Python）
- G4（档案完整性）：PASS

### 功能测试

```bash
acme-tiny --help
# 显示完整帮助信息，功能正常
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| acme-tiny-5.0.1-ohos-aarch64.tar.gz | 50KB | 预编译包 |
| manifest.yaml | 2KB | 版本级元数据 |
| notes.md | 4KB | 编译笔记 |

## 注意事项

1. **setuptools_scm 版本问题**：解压的 tarball 无法自动检测版本，必须设置环境变量
2. **运行时依赖**：需要 openssl 命令行工具支持（用于证书操作）
3. **安装方式**：用户通过预编译包安装后，acme-tiny 命令直接可用
4. **无 ELF 文件**：纯 Python 脚本，不需要 strip/签名等处理
**预编译包**: archives/a/acme-tiny/5.0.1/packaging/acme-tiny-5.0.1-ohos-aarch64.tar.gz
---

**编译结束**: 2026-05-22 15:16
**最终状态**: built
