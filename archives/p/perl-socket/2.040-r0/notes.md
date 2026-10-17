# perl-socket 2.040-r0 适配笔记

## 编译环境
- 构建系统: makefile (Perl XS / ExtUtils::MakeMaker)
- 编译日期: 2026-07-01 (初版 2026-06-29)
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `perl Makefile.PL` — 生成 Makefile，自动探测平台特性
2. `make` — 编译 Socket.xs → Socket.c → Socket.so，同时复制 Socket.pm 到 blib/
3. `package()` — 从 blib/ 复制 Socket.so 和 Socket.pm 到 Conan 包目录

### 关键命令
```bash
perl Makefile.PL
make
# package() copies:
#   blib/arch/auto/Socket/Socket.so → lib/auto/Socket/Socket.so
#   blib/lib/Socket.pm              → lib/Socket.pm
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `test-0.c:17:30: error: no member named 'sa_len' in 'struct sockaddr'` | BSD 特有字段 `sa_len`，Linux/鸿蒙 `struct sockaddr` 无此字段。这是 `perl Makefile.PL` 的特性探测，**非阻塞**，探测失败后正确禁用该特性 | 无需修复，这是正常的特性探测行为 |
| 2 | `Socket.so not found in package` (初始 G2 FAIL) | 早期 test_package 使用 C 测试代码有平台兼容问题；package() 路径需确认 | 重写 test_package 为 Perl 模块加载测试（文件验证 + Perl `use Socket`），package() 正确从 `blib/arch/auto/Socket/` 复制 |
| 3 | `AttributeError: 'ConanOutput' object has no attribute 'warn'` | Conan 2.x 的 `ConanOutput` 没有 `warn()` 方法 | 改用 `self.output.warning()` |
| 4 | `env argument to ConanFile.run() should be a list` | Conan 2.x 的 `ConanFile.run()` 方法 `env` 参数必须为 list 类型，原代码传入了 dict | 改为 `env=["conanrun"]`，使用 Conan 标准环境文件 |
| 5 | `test_package/MANIFEST.yml` 缺失 (G1 FAIL) | CI L0e 门禁要求此文件存在 | 参照 perl-set-object 创建 MANIFEST.yml，声明上游测试 (t/Socket.t) 和 test_package 测试 |
| 6 | SELinux HMDFS 限制 .so 加载 | 鸿蒙 SELinux 策略阻止从 HMDFS 标签路径 (`/storage/Users/...`) 加载共享库，需安装到 `/data/service/hnp/` (hnp_file 标签) | test_package 添加 ELF 验证 + 依赖检查作为 fallback，实际安装到系统目录后可正常加载 |

## 参考 perl-dbd-pg 编译经验

| 经验 | 适用情况 |
|------|---------|
| 鸿蒙缺少 CRT 文件，需 `-nostartfiles -nodefaultlibs -lc` | Socket 模块未遇到此问题（链接较简单，perl Makefile.PL 正确处理） |
| SELinux HMDFS 限制 .so 加载，需安装到系统目录 | **同样遇到**，test_package 通过 ELF 验证 fallback 处理 |
| Makefile.PL 中 `dynamic_lib` 参数添加链接选项 | Socket 模块无需此修改 |

## 源码修改

无补丁。源码无需修改，`perl Makefile.PL` 自动探测平台特性并正确处理 `sa_len` 缺失。

## 依赖版本

- Perl 5.42.0 (系统自带, `/data/service/hnp/bin/perl`)
- clang 15 (鸿蒙 SDK 工具链)

## 产物分析

### Socket.so ELF 信息
- 类型: ELF shared object, 64-bit LSB arm64, not stripped
- 动态依赖: 仅 libc.so
- 导出符号: 34 个全局 FUNC 符号 (与系统 2.038 版本完全一致)
- 关键符号: boot_Socket, getaddrinfo, getnameinfo, htonl, htons, freeaddrinfo

### SELinux 标签
- 系统目录 (`/data/service/hnp/...`): `u:object_r:hnp_file:s0` — 可加载
- 用户目录 (`/storage/Users/...`): `u:object_r:hmdfs:s0` — 不可加载

## 验证结果

```
conan-verify: ALL PASS (G0, G1, G2, G3, G4, L2, L4, L5)
产物: lib/Socket.pm, lib/auto/Socket/Socket.so

功能测试: 29 pass, 3 skip (echo 服务未运行), 0 fail
  - Socket 常量: 9/9
  - IPv4/IPv6 地址函数: 5/5
  - sockaddr pack/unpack: 5/5
  - sockaddr_family: 2/2
  - Unix Domain Socket: 2/2
  - getaddrinfo: 2/2
  - 多播: 1/1
  - 上游 t/Socket.t: 3 pass, 3 skip
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (build: perl Makefile.PL + make, package: copy from blib/) |
| conandata.yml | 源码 URL + sha256 |
| test_package/conanfile.py | Perl 模块加载测试 + ELF 验证 + 依赖检查 (R28) |
| test_package/MANIFEST.yml | 上游测试声明 (CI L0e 门禁) |
| reports/test-report.md | 完整功能测试报告 |
| reports/conan-verify-report.md | Conan 配方验证报告 |
| reports/baseline.json | 产物基线 |

## 注意事项

- `sa_len` 是 BSD 特有字段，Linux/鸿蒙的 `struct sockaddr` 没有此字段。`perl Makefile.PL` 的特性探测会正确检测并禁用。
- Socket 是 Perl 核心模块的 CPAN 版本 (2.040)，系统自带版本为 2.038。两者导出符号完全一致，功能等价。
- test_package 使用 Perl 测试而非 C/CMake 测试（R28）。
- 鸿蒙 SELinux HMDFS 限制阻止从用户目录加载 .so，test_package 包含 ELF 验证 + 依赖检查作为 fallback。
- Conan 2.x `ConanFile.run()` 的 `env` 参数必须为 list 类型（如 `["conanrun"]`），不能传 dict。
- `test_package/MANIFEST.yml` 是 CI L0e 门禁必需文件。

---

**编译结束**: 2026-07-01
**最终状态**: published (conan-verify 全门禁通过 + 功能测试通过)
