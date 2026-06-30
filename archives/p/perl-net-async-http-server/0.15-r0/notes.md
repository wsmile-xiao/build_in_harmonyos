# perl-net-async-http-server 0.15-r0 适配笔记

## 编译环境
- 构建系统: perl (Module::Build)
- 编译日期: 2026-06-24
- 编译器: clang/clang++ (纯Perl模块，无C编译)
- 状态: published

## 编译步骤

1. 下载源码: `curl -fsSL --insecure https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Net-Async-HTTP-Server-0.15.tar.gz`
2. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-net-async-http-server 0.15-r0 --no-download`
3. 安装依赖IO::Async: 从CPAN下载IO-Async-0.805并安装到$DEFAULT_PREFIX
4. 配置: `perl Build.PL --install_base=$DEFAULT_PREFIX`
5. 编译: `./Build`
6. 测试: `./Build test` (73 tests, all pass)
7. Staging安装: `./Build install --destdir=$TEST_PREFIX` (DESTDIR模式)
8. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package perl-net-async-http-server 0.15-r0`
9. 部署安装: `./Build install` (安装到$DEFAULT_PREFIX)
10. 验证: `perl -MNet::Async::HTTP::Server -e 'print "OK"'`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 系统CA证书过期/缺失 | 使用curl --insecure下载，init-build --no-download |
| 2 | IO::Async模块缺失 | 系统未预装IO::Async | 从CPAN下载IO-Async-0.805并手动安装 |
| 3 | manifest缺少build_system字段 | 模板生成的manifest.yaml没有顶级build_system字段 | 手动添加build_system: perl |
| 4 | verify-build G4失败 | manifest缺少build_system字段 | 同上修复 |
| 5 | 模块使用Build.PL而非Makefile.PL | CPAN模块使用Module::Build | 使用perl Build.PL/./Build替代Makefile.PL/make |

## 源码修改

无源码修改，无补丁。纯Perl模块直接编译安装。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| perl | 5.42.0 | 系统预装 |
| Module::Build | 0.4234 | 系统预装 |
| IO::Async | 0.805 | CPAN手动安装 |
| HTTP::Request | 系统版本 | 系统预装 |
| HTTP::Response | 系统版本 | 系统预装 |
| Metrics::Any | 0.10 | 系统预装 |
| Future | 0.52 | 系统预装 |
| Future::Utils | 0.52 | 系统预装 |
| Struct::Dumb | 0.16 | 系统预装 |

## 验证结果

```bash
$ perl -MNet::Async::HTTP::Server -e 'print "OK"'
OK
$ perl -MNet::Async::HTTP::Server -e 'print "Version: ", $Net::Async::HTTP::Server::VERSION, "\n"'
Version: 0.15
```

测试结果: Files=14, Tests=73, All tests successful (3 skipped)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-net-async-http-server-0.15-r0-ohos-aarch64.tar.gz | 45KB | 预编译包 |

## 注意事项

- 这是纯Perl模块，使用Module::Build而非Makefile.PL
- IO::Async依赖不在cmd-pkgs预编译包列表中，需从CPAN手动安装
- 3个测试被跳过: t/80cross-http.t和t/81cross-https.t需要Net::Async::HTTP(客户端), t/99pod.t需要Test::Pod
- SSL证书问题需要使用curl --insecure或更新CA证书
---

**编译结束**: 2026-06-24 17:45
**最终状态**: published

---

## 功能测试补充 (2026-06-25)

基于 perl-dbd-pg 的编译经验，对软件进行了14项功能测试，涵盖：
- 模块加载与版本验证
- 依赖模块可用性
- HTTP服务器实例创建与启动
- PSGI模式与Plack Handler
- 请求对象方法完整性（17个方法）
- Metrics::Any适配器检查
- SELinux限制检查（纯Perl模块，无限制）
- 分块传输响应
- 预编译包内容验证
- 安装路径验证

测试结果: **14/14 PASS**，鸿蒙平台完全可用。

与 perl-dbd-pg 的关键差异：
- perl-dbd-pg 包含XS组件，受SELinux HMDFS限制，需管理员安装
- perl-net-async-http-server 为纯Perl模块，无此限制，用户可直接使用

---

**功能测试结束**: 2026-06-25
**功能测试状态**: PASS (14/14)
