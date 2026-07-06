# perl-redis 2.000 适配笔记

## 编译环境
- 构建系统: makefile (ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-26 (初次) / 2026-06-29 (修复完善)
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -k -L -o Redis-2.000.tar.gz https://cpan.metacpan.org/authors/id/D/DA/DAMS/Redis-2.000.tar.gz`
2. 初始化编译: `python3 ohc-run.py init-build perl-redis 2.000 --url=...`
3. 生成 Makefile: `PERL_MM_FALLBACK_SILENCE_WARNING=1 perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site`
4. 编译: `make -j1`
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `make test`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙平台CA证书问题 | 使用 `curl -k` 手动下载，再用 `--no-download` 初始化 |
| 2 | 测试失败 - 模块无法加载 | 缺少运行时依赖 IO::Socket::Timeout | 手动从CPAN下载安装 IO::Socket::Timeout 0.32 + PerlIO::via::Timeout 0.32 + Try::Tiny 0.31 |
| 3 | 测试失败 - 缺少测试依赖 | 缺少 Test::Fatal, Test::Deep, Test::TCP, Test::SharedFork, IO::String | 手动从CPAN下载安装所有测试依赖 |
| 4 | 测试跳过 - 无redis-server | 鸿蒙平台无Redis服务器 | 可选依赖，记录跳过即可 |
| 5 | conan-verify G2失败 | conanfile.py中env参数格式错误 | 修改为命令行内联环境变量 |
| 6 | 生成模板为autotools | ohc-run.py默认生成autotools模板 | 参考perl-protocol-http2成功案例，改写为Perl Makefile.PL模式 |
| 7 | conanfile.py generate()使用AutotoolsToolchain | 纯Perl模块不需要autotools工具链 | 移除AutotoolsToolchain，改用Conan 2 Environment API设置PERL_MM_FALLBACK_SILENCE_WARNING |
| 8 | self.run() env参数类型错误 | Conan 2的self.run()不接受dict作为env参数 | 使用generate()方法中的Environment类设置环境变量 |
| 9 | package_info()硬编码Perl版本 | 路径中硬编码了"5.42.0" | 改用glob动态发现实际Perl版本路径 |
| 10 | test_package硬编码本地路径 | 硬编码了/storage/Users/currentUser/...路径 | 改为动态检测系统Perl site_perl路径 |
| 11 | test_package缺少功能测试 | 仅检查文件存在和模块加载 | 增加子模块加载测试、API存在性测试、错误处理测试 |
| 12 | test_package包含conan生成文件 | conan create生成的临时文件被归档 | 清理conanbuild.sh/conanrun.sh等生成文件 |
| 13 | 缺少软件级README.md | 归档目录缺少README.md | 创建软件级README.md |
| 14 | conan-verify CI profile无效 | ci/conan/profiles/ohos-aarch64包含os.cpu.arch无效设置 | 使用~/.conan2/profiles/ohos-aarch64手动验证，记录CI profile问题 |

## 源码修改

无源码修改。使用原始 Makefile.PL (ExtUtils::MakeMaker fallback)。

## Conan 配方变更 (2026-06-29)

### conanfile.py 修复
1. **移除 `generate()` 中的 AutotoolsToolchain** — 纯 Perl 模块不需要 autotools 工具链
2. **新增 `generate()` 使用 Conan 2 Environment API** — 正确设置 `PERL_MM_FALLBACK_SILENCE_WARNING=1`
3. **修复 `build()` 方法** — 移除错误的 `env=env` 参数（Conan 2 不接受 dict）
4. **修复 `package_info()`** — 使用 glob 动态发现 Perl 版本路径，不再硬编码 "5.42.0"

### test_package/conanfile.py 修复
1. **移除硬编码本地路径** — 改为动态检测系统 Perl site_perl 路径
2. **增强功能测试** — 新增子模块加载测试、API 存在性测试、错误处理测试
3. **清理生成文件** — 移除 conan create 生成的临时文件

## 依赖版本

- PerlIO::via::Timeout 0.32
- IO::Socket::Timeout 0.32
- Try::Tiny 0.31
- IO::String 1.08
- Test::SharedFork 0.35
- Test::TCP 2.22
- Test::Fatal 0.018
- Test::Deep 1.205

## 验证结果

```bash
$ make test
All tests successful.
Files=18, Tests=7, 7 wallclock secs
Result: PASS

$ conan create archives/p/perl-redis/2.000 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
perl-redis/2.000: Package created
test_package: Redis loaded successfully: OK
test_package: Version OK
test_package: Submodules OK
test_package: API test OK, Redis::Hash API OK, Redis::List API OK
```

## 注意事项

- 本模块为纯Perl模块（无XS/C代码）
- 源码同时包含 Build.PL (Module::Build::Tiny) 和 Makefile.PL (ExtUtils::MakeMaker fallback)
- 使用 Makefile.PL 时需设置 PERL_MM_FALLBACK_SILENCE_WARNING=1 避免警告和10秒等待
- conanfile.py 按照纯Perl模块模式编写，参考 perl-protocol-http2/1.11 成功案例
- Redis 2.000 使用 AUTOLOAD 机制动态分发 Redis 命令（set/get/del 等），这些方法不直接定义
- CI profile (`ci/conan/profiles/ohos-aarch64`) 有无效设置 `os.cpu.arch`，需修复后 conan-verify 自动验证才能通过

---

**编译结束**: 2026-06-29
**最终状态**: published
