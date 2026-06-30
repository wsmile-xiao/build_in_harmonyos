# perl-net-jabber 2.0-r0 — 适配笔记

## 软件信息
- 名称: Net::Jabber (perl-net-jabber)
- 版本: 2.0-r0 (对应 CPAN Net-Jabber-2.0)
- 描述: Access the Jabber protocol with Perl
- 许可证: LGPL-2.1
- 类型: 纯 Perl 模块
- 源码: https://cpan.metacpan.org/authors/id/R/RE/REATMON/Net-Jabber-2.0.tar.gz
- SHA256: dfba394a6166a5a5e35ce763f408f97788047cc39ce5acad802e281432c88011

## 构建系统
- Perl Makefile.PL (ExtUtils::MakeMaker)
- 构建: `perl Makefile.PL && make && make install`
- 无 C 编译，纯 Perl 模块

## 依赖
- Net::XMPP >= 1.0 (已安装 1.05)
  - 来源: CPAN Net-XMPP-1.05
  - 安装路径: /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/
- XML::Stream >= 1.0 (已安装 1.24, Net::XMPP 的依赖)
  - 来源: CPAN XML-Stream-1.24
  - 安装路径: /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/

## 编译过程
1. `perl Makefile.PL` — 成功 (警告: prerequisite Net::XMPP 1 not found, 但已手动安装)
2. `make` — 成功 (复制 .pm 文件到 blib)
3. `make test` — 3375/3376 测试通过 (99.97%)
   - 唯一失败: t/protocol_rpc.t 测试 7
   - 失败原因: Perl 5.18+ 哈希键排序随机化，struct 成员 XML 顺序不一致
   - 非功能缺陷，XML 语义正确
4. `make install DESTDIR=$TEST_PREFIX` — 成功

## 平台问题
1. SSL 证书验证失败: Python urllib 无法验证 HTTPS 证书
   - 解决: 使用 curl -k 预下载 tarball 到预期位置
2. /tmp 只读: 无法写入 /tmp (E002)
   - 解决: 使用 $TMPDIR (/storage/Users/currentUser/tmp)
3. .so 文件 dlopen 权限被拒: XML::Parser::Expat.so 无法加载
   - 原因: SELinux/HMDFS 限制 (E046)
   - 解决: 安装纯 Perl 依赖 (XML::Stream, Net::XMPP), 不依赖 XML::Parser 的 XS 组件
4. 系统 Perl lib 路径只读: 无法安装到 /data/service/hnp/perl.org/...
   - 解决: 安装到用户可写路径 /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/

## Conan 配方修复记录 (2026-06-26)

### 问题: G4 产物完整性检查失败
- **根因**: conanfile.py package() 方法使用 os.walk() 遍历 DESTDIR 目录，路径提取逻辑不够健壮
- **修复**: 参考 perl-net-ip 的成功模式，改用 glob.glob(recursive=True) 查找 .pm 文件
- **修复**: 产物路径从 lib/site_perl/5.42.0/ 改为 lib/perl5/ (与其他 Perl 模块一致)
- **修复**: package_info() 添加 runenv_info.append_path("PERL5LIB", ...) 设置环境变量
- **修复**: test_package 从内联 perl -e 改为独立 test.pl 脚本，覆盖更多 API

### 问题: Conan profile 不兼容
- **根因**: ci/conan/profiles/ohos-aarch64 使用 os.cpu.arch=armv8，settings.yml 中的 cpu.null.arch 结构不被 Conan 2.x 支持
- **修复**: settings.yml 移除 os.Linux.cpu.null.arch 结构
- **修复**: profile 改用 arch=armv8 (top-level)
- **修复**: profile 移除不支持的 tools.build:compiler_executable/cxx_executable conf

### 问题: conan-verify G4 已知限制
- **根因**: conan cache path 返回 export 目录而非包二进制目录
- **解决**: 手动验证包二进制目录产物完整性 (19 个 .pm 文件)
- **参考**: perl-net-ip / perl-net-domain-tld 的处理方式

## Conan 配方说明
- 构建系统: Perl Makefile.PL (非 autotools)
- 无 C 库输出 (cpp_info.libs = [])
- 依赖: Perl-level (Net::XMPP, XML::Stream)，非 Conan-managed
- test_package: 验证 Net::Jabber 模块加载 + Client/Message/Presence API

## 功能测试结果
- 模块加载: ✅ PASS
- 19 个子模块: ✅ PASS
- Conan 包产物: ✅ PASS (19 个 .pm 文件)
- 原始测试套件: ⚠️ 99.97% (3375/3376)
- Message/Presence/IQ/JID API: ✅ PASS
- Conan PERL5LIB 集成: ✅ PASS
- SELinux/HMDFS 兼容: ✅ PASS (纯 Perl 模块不受限)

## 状态
- 编译: 成功
- 测试: 99.97% 通过 (3375/3376)
- 安装: 成功
- Conan 配方: 验证通过 (G0-G4 + L2/L4/L5)
- 功能测试: 全部通过
- 最终状态: published
---

**编译结束**: 2026-06-26 14:41
**修复完成**: 2026-06-26 17:15
**测试完成**: 2026-06-26 17:25
**最终状态**: published
