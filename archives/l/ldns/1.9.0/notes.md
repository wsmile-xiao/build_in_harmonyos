# ldns 1.9.0 编译笔记

## 状态: built（Conan 配方验证通过）

### 编译挑战

1. **config.status 临时目录问题**: HarmonyOS上 config.status 使用 `mktemp -d` + `umask 077` 创建临时目录后，
   无法在目录内创建文件（Permission denied）。
   **解决方案**: 将 `mktemp -d "./confXXXXXX"` 替换为 `mkdir -p "$TMPDIR/conf$$"` + `umask 000`。

2. **OpenSSL 依赖**: 原历史记录使用 openssl/3.0，但制品仓中该版本不存在。
   **解决方案**: 更改为 openssl/3.5.6（制品仓中可用版本）。

### 构建配置

- 构建系统: autotools
- 配置参数: --prefix=$DEFAULT_PREFIX --with-examples --with-drill --with-ssl=<openssl_path>
- 编译器: clang 15.0.4
- 依赖: openssl/3.5.6 (静态链接, R26)

### 补丁

1. 0001-harmonyos-platform-support.patch: config.guess + config.sub 添加 HarmonyOS 平台支持

### Conan 配方

- conanfile.py 使用 AutotoolsToolchain
- 依赖 openssl/3.5.6
- 默认静态链接 (R26)
- build() 中修复 configure 脚本的 config.status 临时目录问题
- test_package 调用 ldns API (ldns_rr_list_new, ldns_pkt_new, ldns_version)

### 验证结果

- conan-verify G0-G4 + L2/L4/L5 全部通过
- 可标记 status: published

---
编译结束: 2026-08-10
---

**编译结束**: 2026-08-11 01:49
**最终状态**: published
