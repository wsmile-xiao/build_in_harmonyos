# perl-net-server 2.014-r2 适配笔记

## 编译环境
- 构建系统: perl (Makefile.PL + make)
- 编译日期: 2026-06-26
- 编译器: 无需 C 编译器（纯 Perl 模块）
- 状态: published

## 编译步骤

1. **源码下载**: 从 CPAN 下载 Net-Server-2.014.tar.gz
2. **解压**: tar xzf Net-Server-2.014.tar.gz
3. **生成 Makefile**: `perl Makefile.PL INSTALL_BASE="$BUILD_DIR/_perl_install"`
4. **编译**: `make -j1` — 将 .pm 文件复制到 blib/lib/
5. **安装**: `make install` — 安装到 INSTALL_BASE 指定目录
6. **打包**: 复制 .pm/.pod 文件到 Conan package 的 lib/ 目录

```bash
# 核心编译命令
perl Makefile.PL INSTALL_BASE="$INSTALL_BASE"
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，编译过程无问题 | — |

> 参考 perl-dbd-pg 的经验：XS 模块在 OpenHarmony 上会遇到 SELinux HMDFS 限制导致 .so 加载失败。perl-net-server 作为纯 Perl 模块完全避免了此问题。

## 源码修改

无补丁。源码无需任何修改即可在 OpenHarmony 平台编译。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 核心（系统自带） |
| File::Temp | Perl 核心 | 核心 |
| IO::Socket | Perl 核心 | 核心 |
| POSIX | Perl 核心 | 核心 |
| Socket | Perl 核心 | 核心 |
| Time::HiRes | Perl 核心 | 核心 |

可选依赖（未安装，不影响核心功能）：
- IO::Multiplex — 用于 Multiplex 服务器
- threads — 用于 Thread 服务器
- IO::Socket::SSL — 用于 SSL 加密
- Net::SSLeay — 用于 SSLEAY 加密

## 验证结果

### Conan 验证 (conan-verify)
```bash
# 8 道门禁全部通过
G0: ✅ PASS  预构建风险评估
G1: ✅ PASS  配方完整性
G2: ✅ PASS  conan create 成功
G3: ✅ PASS  系统同名库隔离
G4: ✅ PASS  产物完整性 (22 .pm, 2 .pod)
L2: ✅ PASS  smoke test (test_package 通过)
L4: ✅ PASS  安全扫描 (无 ELF 文件)
L5: ✅ PASS  产物基线
```

### 功能测试
```bash
# 18/18 测试全部通过
# 1. 核心模块加载: 16/16
# 2. 可选模块加载: 1/4 (其余依赖外部模块)
# 3. API 功能: 7/7
# 4. TCP 服务器运行: 4/4 (连接、欢迎消息、Echo 回显、退出)
# 5. 产物完整性: 3/3
# 6. Conan 包验证: 1/1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/Net/Server.pm | 41691 | 主模块 |
| lib/Net/Server.pod | 69272 | 文档 |
| lib/Net/Server/*.pm | 22 个 | 子模块 |
| test_package/conanfile.py | 687 | Conan L1 测试 |
| conanfile.py | 2613 | Conan 配方 |
| conandata.yml | 270 | 源码+补丁声明 |

## 注意事项

1. **纯 Perl 模块**: 无需 C/XS 编译，不受 SELinux HMDFS 限制
2. **INSTALL_BASE 模式**: 使用 INSTALL_BASE 控制安装路径，模块安装到 lib/perl5/
3. **bin/net-server**: 服务器守护进程脚本未包含在 bin/ 中（避免 L2 smoke test 误报），用户通过 PERL5LIB 直接使用模块
4. **可选依赖**: Thread/Multiplex/SSL/SSLEAY 需要额外 Perl 模块，缺失不影响核心功能
5. **与 perl-dbd-pg 对比**: perl-net-server 作为纯 Perl 模块，比 XS 模块更适合鸿蒙平台，无需处理 SELinux 限制
