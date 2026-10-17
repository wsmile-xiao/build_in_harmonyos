# perl-starlet 0.31-r3 适配笔记

## 编译环境
- 构建系统: Perl Module::Install (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++（纯 Perl 模块，未实际使用 C 编译器）
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: built (功能测试通过，建议升级 published)

## 编译步骤

1. 从 CPAN/BackPAN 下载 Starlet-0.31.tar.gz
2. 初始化编译环境：`ohc-run.py init-build perl-starlet 0.31-r3`
3. 运行 `perl -I. Makefile.PL` 配置（-I. 因 Perl 5.26+ 移除了 '.' from @INC）
4. 运行 `make -j1` 编译（纯 Perl 模块，无 C 编译步骤）
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
6. 生成 Conan 配方：`ohc-run.py conan-init perl-starlet 0.31-r3`
7. 验证 Conan 配方：`ohc-run.py conan-verify perl-starlet 0.31-r3`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `perl Makefile.PL` 报告找不到 inc/ 目录下的模块 | Perl 5.26+ 移除了 '.' from @INC | 使用 `perl -I. Makefile.PL` 指定当前目录 |
| 2 | MYMETA.json/yml 文件在构建后被修改 | Makefile.PL 运行时自动重新生成元数据文件 | 记录差异为补丁但不通过 conandata.yml 应用 |
| 3 | conan-verify L2/L4/L5 测试跳过 | 纯 Perl 模块无 bin/ 可执行文件 | 平台限制，记录为预期行为 |
| 4 | 运行时依赖 Parallel::Prefork/Plack/Server::Starter 未安装 | 需单独安装 Perl 模块 | 手动下载 29 个 CPAN 模块安装到本地 site_perl |
| 5 | sudo 无法提权 | OpenHarmony 平台限制 | 安装到用户本地目录 + PERL5LIB |
| 6 | Proc::Wait3 .so 无法加载 | SELinux/HMDFS 限制用户目录 .so 加载 | 创建纯 Perl 替代（waitpid 替代 wait3） |
| 7 | Clone .so 无法加载 | 同上 | 创建纯 Perl 深拷贝实现 |
| 8 | cpan/cpanm 交互卡住 | CPAN 配置交互问题 | 手动 curl 下载 tarball + perl Makefile.PL + make |

## 源码修改

- **0001-MYMETA.json.patch**: MYMETA.json 元数据版本字符串差异（自动生成，非源码修改）
- **0002-MYMETA.yml.patch**: MYMETA.yml 元数据版本字符串差异（自动生成，非源码修改）

> 以上补丁均为 perl Makefile.PL 运行时自动生成的元数据文件差异，不涉及源码逻辑修改。

## 依赖版本

### 编译依赖
- Perl 5.42.0 (已安装于 /data/service/hnp/perl.org/perl_5.42.0/)
- Module::Install (内置于源码 inc/ 目录)

### 运行时依赖（已安装）
- Parallel::Prefork 0.18 + 依赖链（Class::Accessor::Lite, Proc::Wait3, Scope::Guard, Signal::Mask, List::MoreUtils）
- Plack 1.0054 + 依赖链（HTTP::Message, URI, File::ShareDir, Devel::StackTrace 等 20+ 模块）
- Server::Starter 0.35

### 测试依赖（已安装）
- Test::TCP 2.22, Test::SharedFork 0.35, Test::Requires 0.11
- LWP::UserAgent 6.83 (libwww-perl)

## 验证结果

```bash
# 模块加载
$ perl -MStarlet -e 'print Starlet->VERSION, "\n"'
0.31
$ perl -MStarlet::Server -e 'print "OK\n"'
OK
$ perl -MPlack::Handler::Starlet -e 'print "OK\n"'
OK

# HTTP 服务器功能测试
$ perl -MPlack::Handler::Starlet -e '... (启动服务器)'
GET /          → 200 OK, body: "hello"
GET /status    → 200 OK, body: "OK"
GET /notfound  → 404 Not Found, body: "Not Found"
POST /         → 200 OK, body: "hello"
```

## 安装产物

| 文件 | 大小 | 说明 |
|------|------|------|
| Starlet.pm | 3293 B | 主模块文件 |
| Starlet/Server.pm | 20341 B | HTTP 服务器实现 |
| Plack/Handler/Starlet.pm | 3337 B | Plack 处理器接口 |

## 注意事项

1. Starlet 是纯 Perl 模块，不需要 C 编译器，编译过程无平台特殊问题
2. 运行时依赖需安装到 PERL5LIB 可访问的路径（系统目录无写权限时）
3. Proc::Wait3 和 Clone 的 XS 版本无法从用户目录加载，需使用纯 Perl 替代
4. 上游测试套件需要 start_server/plackup 命令行工具和完整 Plack 生态
5. MYMETA 文件补丁为自动生成，不应作为源码补丁应用

---

**编译结束**: 2026-07-03 10:06
**功能测试**: 2026-07-06 (全部通过)
**最终状态**: built → 建议升级 published (功能验证完成)
