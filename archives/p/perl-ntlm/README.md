# perl-ntlm (Authen::NTLM)

Perl 模块，实现 NTLM (NT LAN Manager) 认证协议，用于 Windows 网络认证场景。

## 功能概述

- **NTLM 认证协议**：支持 NTLMv1 和 NTLMv2 协议
- **密码哈希计算**：LM hash、NTLM hash 计算
- **挑战-响应机制**：完整的 NTLM challenge-response 流程
- **Base64 编解码**：NTLM 消息的 Base64 编码/解码
- **DES/MD4 加密**：内置 DES 和 MD4 实现（纯 Perl）

## OHOS 适配

### 适配要点

- **纯 Perl 模块**：无需 C 编译，不产生 .so 文件，不受 SELinux HMDFS 限制
- **构建系统**：使用 ExtUtils::MakeMaker（`perl Makefile.PL` + `make`）
- **Conan 打包**：使用 `blib/lib` 目录直接 copy，避免 `os.path.join` 绝对路径覆盖问题
- **test_package**：使用 `VirtualRunEnv` 生成器，非 CMake；Perl `-e` 命令需用单引号防止 shell 变量展开

### 已知问题

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| `/tmp` 只读 | 鸿蒙平台限制 | 使用 `$TMPDIR` 或 `$HOME/tmp` |
| curl SSL 证书验证失败 | 鸿蒙平台证书链不完整 | 更新 CA 证书或使用 Conan `get()` 内置下载（自动校验 sha256） |
| Conan 2 `deps_cpp_info` 废弃 | Conan API 变更 | 使用 `self.dependencies[name].package_folder` |

### 与 Linux 的差异

- 无 C 编译环节，平台差异不影响编译
- 模块加载路径需通过 `perl -I<path>` 显式指定
- 无 SELinux 限制（纯 Perl 模块无 .so 文件）

## 依赖关系

### 编译依赖
- Perl 5.x（系统自带）

### 运行依赖
- MIME::Base64（Perl 核心模块）
- Digest::HMAC_MD5（Perl 核心模块）

## 参考资料

- [MetaCPAN - NTLM](https://metacpan.org/dist/NTLM)
- [CPAN - Authen::NTLM](https://cpan.metacpan.org/authors/id/N/NB/NBEBOUT/NTLM-1.09.tar.gz)
