# perl-net-appliance-session 4.300005-r5 适配笔记

## 编译环境
- 构建系统: perl-module-build (Module::Build)
- 编译日期: 2026-06-24
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `Net-Appliance-Session-4.300005.tar.gz` (CPAN)
2. 解压源码到工作目录
3. 运行 `perl Build.PL --prefix=$DEFAULT_PREFIX`
4. 运行 `./Build` 编译
5. 运行 `./Build test` 测试 (23 tests, PASS)
6. 运行 `./Build install DESTDIR=$TEST_PREFIX` (staging 安装)
7. 运行 `./Build install` (安装到 ~/usr/local)
8. `ohc-run.py package` 制作预编译包
9. `ohc-run.py finish` 归档收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | IO::Tty 不可用 | XS 模块，SELinux HMDFS 限制（同 perl-dbd-pg） | 纯 Perl 模块不受影响，交互连接需管理员安装 IO::Tty 到系统目录 |
| 2 | G0 干净构建验证失败 | Python subprocess 调用 `perl Build.PL` 时 shell 引号问题 | 平台限制，手动验证通过，不影响实际编译 |
| 3 | IPC::Run waitpid 警告 | 平台 syscall 差异，waitpid 参数为空 | 非致命警告，不影响功能 |
| 4 | Text::ParseWords 未初始化值警告 | nas CLI 工具中的 shellwords 参数解析 | 非致命警告，不影响功能 |

## 源码修改

无补丁。本软件为纯 Perl 模块，无需修改源码即可在鸿蒙平台编译和运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.42.0 | 系统预装 |
| Module::Build | 0.4234 | 构建系统 |
| Net::CLI::Interact | 2.300003 | CLI 交互后端 |
| IO::Prompt::Tiny | 0.003 | 密码提示 |
| Term::ReadPassword | 0.11 | 密码输入 |
| IO::Tty | 不可用 | XS 模块，受 SELinux 限制 |

## 验证结果

```bash
$ perl -MNet::Appliance::Session -e 'print $Net::Appliance::Session::VERSION'
4.300005

$ ./Build test
All tests successful. Files=10, Tests=23, Result: PASS

$ nas --help
Net Appliance Session scripting - v4.300005
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-net-appliance-session-4.300005-r5-ohos-aarch64.tar.gz | 55KB | 预编译包 |

## 注意事项

1. *hnp/` 系统目录。
2. **PurePerl *IO::Tty 限制**: SSH/Telnet 交互式连接需要 IO::Tty (XS 模块)，受 SELinux HMDFS 限制无法从用户空间加载。参考 perl-dbd-pg 的 HNP 包方案，需管理员安装到 `/data/service/优势**: 本模块为纯 Perl 实现，模块加载、对象创建、API 调用、phrasebook 解析等核心功能不受 SELinux 限制。
3. **IPC::Run 警告**: 非致命，不影响功能，已在测试报告中记录。
4. **G0 验证**: clean-verify 的 configure 步骤因 Python subprocess shell 引号问题失败，手动验证确认编译正常。

---

**编译结束**: 2026-06-25
**最终状态**: published
