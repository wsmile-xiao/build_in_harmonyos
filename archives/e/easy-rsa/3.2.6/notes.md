# easy-rsa 3.2.6 适配笔记

## 编译环境
- 构建系统: shell（纯 POSIX shell 脚本，无需编译）
- 编译日期: 2026-08-06
- 编译器: 无（shell 脚本）
- 状态: published

## 编译步骤

Easy-RSA 是一个纯 POSIX shell 脚本工具，用于管理 PKI（公钥基础设施）。无需传统编译过程。

1. **下载源码**: 从 GitHub 下载 v3.2.6 tarball
2. **版本占位符替换**: 在 easyrsa 脚本中替换 `~VER~` → `3.2.6`、`~DATE~` → 构建日期、`~GITHEAD~` → unknown
3. **安装文件**: 复制 easyrsa3/ 目录中的文件到目标位置
   - `easyrsa` 脚本 → `$PREFIX/bin/easyrsa`
   - `openssl-easyrsa.cnf` → `$PREFIX/share/easy-rsa/`
   - `vars.example` → `$PREFIX/share/easy-rsa/`
   - `x509-types/` → `$PREFIX/share/easy-rsa/x509-types/`
4. **功能测试**: 运行 `--version`、`init-pki`、`build-ca nopass` 验证完整功能

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法自动检测下载 URL | Easy-RSA 不在 registry 中 | 手动提供 GitHub URL |
| 2 | 版本信息显示占位符 | 源码中含 ~VER~ 等占位符 | 在 conanfile.py build() 中用 replace_in_file 替换 |
| 3 | ~HOST~ 占位符不存在 | easyrsa 脚本中无 ~HOST~ | 去掉对 ~HOST~ 的替换（build-dist.sh 中有但 easyrsa 无） |
| 4 | conan-init 生成 Autotools 模板 | 默认模板假设 C 库 | 手动重写 conanfile.py 为 application 类型 |

## 源码修改

补丁文件: `0001-easyrsa3-easyrsa.patch`（版本占位符替换）
- 替换 `~VER~` → `3.2.6`
- 替换 `~DATE~` → 构建日期
- 替换 `~GITHEAD~` → unknown

## Conan 配方说明

- **package_type**: application（命令行工具，非库）
- **settings**: os, arch（无 compiler/build_type，纯 shell 脚本）
- **依赖**: openssl/1.1.1w（运行时依赖 openssl 命令行工具）
- **build()**: apply_conandata_patches + replace_in_file 替换版本占位符
- **package()**: 安装 easyrsa 脚本、配置文件、x509-types 到 bin/ 和 share/easy-rsa/
- **package_info()**: bindirs=["bin"], resdirs=["share/easy-rsa"]
- **test_package**: 运行 easyrsa --version、init-pki、build-ca nopass

## 依赖版本

- OpenSSL: 1.1.1w（运行时依赖，通过 Conan 管理）

## 验证结果

```bash
$ easyrsa --version
EasyRSA Version Information
Version:     3.2.6
Generated:   Thu Aug  6 08:11:51 CST 2026
SSL Lib:     OpenSSL 3.0.9 30 May 2023

$ easyrsa --batch init-pki
'init-pki' complete; you may now create a CA or requests.

$ easyrsa --batch build-ca nopass
CA creation complete. Your new CA certificate is at:
* ca.crt
```

## Conan 验证结果

| 门禁 | 结果 |
|------|------|
| G1 配方完整性 | PASS |
| G2 conan create | PASS |
| G3 系统同名库隔离 | PASS |
| G4 产物完整性 | PASS |
| L2 平台功能测试 | PASS |
| L4 静态安全扫描 | PASS |
| L5 产物基线对比 | PASS |
| W3 本地 CI 模拟 | PASS |

## 注意事项

1. Easy-RSA 是 shell 脚本，不需要 ELF 签名（但依赖的 openssl 需要）
2. 需要确保 OpenSSL 已安装并在 PATH 中
3. easyrsa 脚本安装后可直接执行
4. 建议用户通过 `source vars.example` 配置环境变量

---

**编译结束**: 2026-08-06 08:17
**最终状态**: published
