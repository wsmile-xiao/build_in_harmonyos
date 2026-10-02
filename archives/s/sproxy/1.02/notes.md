# sproxy 1.02 适配笔记

## 编译环境
- 构建系统: autotools 包装的纯 Perl 脚本包（无 C/C++ 编译；manifest 记 custom）
- 编译日期: 2026-09-29
- 编译器: 无（perl 解释型，`cc: none`）
- 状态: built（W3 由 finish 写入 `.ci-result.json`）

## 语言预检（R47）
- 只读预判 `detect_language`: `{'detected_language': 'c', 'build_system': 'autotools', 'manifest': 'configure.ac/Makefile.am 存在', 'source_stats': '无源文件可统计'}`；
  默认口径 `lang-preflight` 放行（exit 0）。
- 实际内容：`src/sproxy.in`（180 行 Perl，`#!%_PERL%`）+ 自带 `lib/JoeDog-Config-1.2.tar.gz` 等 4 个 Perl 模块 tarball，
  全仓无 `.c/.h`。检测器因 autotools 元数据判 c，实际是 Perl 脚本包；已如实记录，判定未导致 `env_unsupported`，无需覆盖。

## 上游测试清点（R51）
- 上游 1.02 无任何测试：无 `tests/` 目录，`Makefile.am` 无 `check`/`TESTS`，无 ctest/pytest 注册；
  `find -name 'test*'` 仅得 `utils/modtest`（configure 的 perl 模块探测脚本，非测试）。上游 N=0，N′=0。
- 由 `test_package/test_sproxy.py` 补真实消费者功能测试（10 断言）。

## 编译（打包）步骤
上游 `configure && make && make install` 只做三件事：`sed` 替换 `%_DATE%/%_VERSION%/%_PROGRAM%/%_AUTHOR%/%_PERL%`（src/sproxy、
doc/sproxy.conf、doc/sproxy.1）、拷贝到 `$prefix/{bin,etc,man}`、当 `$PERL utils/modtest <Module>` 判定缺模块时解包 `lib/*.tar.gz`
并 `perl Makefile.PL LIB=$prefix/lib/sproxy`。配方在 `build()` 用 Python 做等价处理（见下），`package()` 布局：

```
bin/sproxy                      # shebang = perl 依赖包绝对路径
etc/sproxy.conf                 # 脚本读取 $Bin/../etc/sproxy.conf
lib/sproxy/JoeDog/Config.pm     # 脚本 use lib $Bin/../lib/sproxy
share/man/man1/sproxy.1  share/doc/sproxy/{README,AUTHORS,ChangeLog}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务书依赖写 Autoconf/Automake/Libtool | sproxy 无 C 代码，configure 已随包预生成，上游 autotools 仅做 sed/拷贝 | 不依赖 autotools，配方 `build()` 等价实现；构建机无需 autoconf/automake/libtool |
| 2 | 不能走上游 configure | `configure.in` 用 `$PERL utils/modtest` 探测模块，需在构建机执行目标 perl（aarch64 musl ELF，x86 构建机不可执行，E544）；输出为空会让自带 JoeDog::Config 被静默跳过 | 直接用 `tarfile` 从 `lib/JoeDog-Config-1.2.tar.gz` 取出 `Config.pm` 装到 `lib/sproxy/JoeDog/` |
| 3 | 上游 `Makefile.am` 有笔误 `havesmime` | install-exec-hook 里变量名写错（应为 havemime）；且 `MIME::Base64` 为 perl 核心模块 | 不复用上游 Makefile，未受影响 |
| 4 | shebang | OHOS 无 `/usr/bin/perl` 且禁 `#!/usr/bin/env perl`（同 ldap-git-backup 先例） | `#!%_PERL%` 重写为 `perl/5.42.2.3` 依赖包绝对路径 |
| 5 | test_package 第 1 次失败 `no perl with LWP::UserAgent/HTTP::Daemon` | 依赖 perl 是 aarch64 ELF，x86 runner 无法执行；候选被 `which("perl")` 命中的仍是它 | 候选加入 `/usr/bin/perl` 等主机 perl 并去重 |
| 6 | 第 2 次失败 `Can't load '…/aarch64-linux-thread-multi/auto/…so'` | `conanrun` 导出依赖 perl 的 `PERL5LIB`，主机 perl 继承后加载 XS 失败 | 仅对 shebang 所指依赖 perl 继承 `PERL5LIB`，其余候选用干净 `PERL5LIB`（沉淀为知识草稿 E14721） |
| 7 | CI 红（首轮 `Can't locate HTTP/Daemon.pm`，二轮 `Can't locate HTTP/Request.pm`） | CI 上依赖 perl 与设备系统 perl 都不带 libwww-perl 栈（本地主机 perl 自带，掩盖了缺口；首轮我误判为只缺 Daemon）；已核对本地缓存的同一份 conan perl 包：无 LWP/HTTP/URI | 配方自包含：从上游自带 `lib/libwww-perl-5.76.tar.gz` 装整套 LWP/HTTP::*/Net::HTTP（纯 Perl），另取官方 CPAN `URI-5.35` 纯 Perl，全部装到 `lib/sproxy`；test 断言这些模块均解析自包内 |
| 8 | LWP 5.76 默认 `parse_head=1`，text/html 响应会 `require HTML::HeadParser`（XS，依赖 perl 不带） | sproxy 只转发内容，不需要 head 解析 | `build()` 在 `$ua->env_proxy;` 后插入 `$ua->parse_head(0);`（锚点计数校验）；test 在 HTML::* 不可加载下转发 text/html 响应 |

## 源码修改
无 `.patch` 文件（`patches: []`）。适配全部在配方 `build()` 内：sed 等价替换、shebang 重写、自带模块取出，以及对 `src/sproxy.in` 的一处插入 `$ua->parse_head(0);`（见问题 8，锚点计数校验防上游漂移；不含平台宏）。

## 依赖版本
- perl/5.42.2.3（制品仓 `conan download perl/5.42.2.3 -r=ohpcd --only-recipe` 可得，已发布）
- 运行期 perl 模块：依赖 perl 与设备系统 perl 都不带 libwww-perl 栈（制品仓另有的 `perl-libwww/6.83` 缺 HTTP-Message/HTTP-Daemon/URI 等，W0 核查无对应 conan 包，不捎带适配）。
  因此包自包含：`lib/sproxy/` 装上游自带 libwww-perl 5.76 整套纯 Perl（LWP、HTTP::*、Net::HTTP、File::Listing、WWW::RobotRules）、`JoeDog::Config`，
  以及官方 CPAN `URI-5.35`（sha256 与 `perl-uri/5.35` 配方同源，`conandata.yml` 第二个 source）。脚本 `use lib $Bin/../lib/sproxy` 使其优先于系统同名模块。
  仍用到的 perl 核心模块（MIME::Base64、Digest::MD5、IO::Socket、Compress::Zlib 等）在依赖 perl 中存在。

## 验证结果

```bash
conan create archives/s/sproxy/1.02 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# test_package/test_sproxy.py 输出（本地 x86 实跑，perl=/usr/bin/perl，退出码 0）：
#   OK: modules resolve from package lib/sproxy
#   OK: -V banner substituted: 'SPROXY v1.02-September-29-2026'
#   OK: -h prints usage with substituted version
#   OK: shebang rewritten from %_PERL%: #!/…/perl/…/bin/perl
#   OK: sproxy listening on 127.0.0.1:<port>
#   OK: GET forwarded: 200 'origin-GET:/hello?x=1'
#   OK: POST forwarded: 200 'origin-POST:a=1\nb=2'
#   OK: text/html forwarded with HTML::* unloadable
#   OK: origin received both proxied requests
#   OK: output file has siege-style lines: ['<url>/form POST a=1&b=2', '<url>/hello?x=1']
```

**如实说明**：包产物（`bin/sproxy`）是与架构无关的 Perl 脚本，本地由**主机 x86 perl** 执行（依赖包的 aarch64 perl 在 x86 runner 上不可执行，
E544，`qemu-aarch64` 亦无 musl loader），执行的是**已安装包内的同一份脚本与 Config.pm**；shebang 所指 aarch64 perl 未在本地实跑。
在 OHOS 设备/CI 上，测试优先用 shebang 指向的依赖 perl；包自带 libwww-perl/URI，perl 只需提供核心模块。

**修订（CI 两轮红后）**：加入自包含 libwww-perl/URI 与 `parse_head(0)` 后重跑，测试 10/10 通过；本地主机 perl 只作解释器，所有 LWP/HTTP/URI 模块均解析自包内（test 已断言）。

## 鸿蒙特有测试（rule12）
- 用例：`test_package/test_sproxy.py`（由 `test_package/conanfile.py` 的 `test()` 经 `self.run` 调起，在 `conan create` 必跑路径上）。N = 1（10 个断言）。
- 流程：被测包参与构建（conan 消费）→ 启动包内 `bin/sproxy`（默认 `etc/sproxy.conf` + 包内 `lib/sproxy/JoeDog/Config.pm`）→ 经代理向本地 origin
  发 GET/POST → 校验转发响应、origin 收到请求、输出文件 siege 格式 URL 行。覆盖本次适配改动点（shebang 重写、模块自带安装、sed 替换）。

## 注意事项
- `%_DATE%` 取构建当天（等价上游 `utils/mkstamp`），`-V` 输出含构建日期。
- 上游 `sproxy.conf` 文档写 `output =`，脚本实际读 `file =` 键（上游既有不一致，未改动）；输出文件请用 `-o`。
---

**编译结束**: 2026-09-29 07:30
**最终状态**: built
