# notes.md — inspircd 4.7.0 适配记录

申请人：Bingggooo（队伍：来都来了）

## 上游

- 仓库：https://github.com/inspircd/inspircd（分支 insp4），官网 https://www.inspircd.org/
- 版本：v4.7.0（2025-03-29 发布），C++17 模块化 IRCv3 服务器
- 源码包：https://github.com/inspircd/inspircd/archive/refs/tags/v4.7.0.tar.gz
- sha256：`fcad041a46f1d7c635ba2ed41d7bcef1cfa2510a5692ac98b34f90420187c97b`（本地下载实测，非估算）
- License：GPL-2.0-only

## 构建系统（perl Configure + make，非 autotools/cmake）

- `configure` 是 perl 程序（`use v5.26.0`，仅核心模块：Config/Cwd/File::*/FindBin/Getopt/Class::Struct/File::Path），由 HNP 系统 perl（`/data/service/hnp/bin/perl` 5.42.0）直接运行，**不设 `tool_requires("perl/...")`**——conan perl 5.42.2 在真机上不可用：其 PERL5LIB（5.42.2 lib）泄漏到系统 perl 5.42.0 可执行文件上导致 `Perl lib version (5.42.2) doesn't match executable 'perl' version (5.42.0)` 中断（2026-09-27 预检实测；mdocml/avimetaedit/burp2 同款先例）。build() 显式 `unset PERL5LIB; export PERL=<system-perl>` 后调用系统 perl。
- 任一命令行选项即进入非交互模式；配方传 `--prefix=/ --disable-auto-extras --disable-ownership --disable-interactive`。
- 上游 Configure 是纯 in-source 构建：`configure` 首检 `-w $RealDir`，不可写即 `print_error ... exit 1`（无绕过旗标），且 `.configure/cache.cfg`、生成的 makefile、探测二进制、全部目标文件都写进源码树。真机上 conan 源码缓存及 build 文件夹下新鲜副本连续两轮均报 `Checking whether <tree> is writable ... no`（2026-09-27 预检），证明问题不在“是否复制”而在 conan-home 所在 HMDFS 的 `access()` 判定；故本轮改走与前两轮完全不同的路线：build() 经 `_sync_build_tree()` 把源码树复制到 HMBS 任务级 TMPDIR（`$TMPDIR/inspircd-src`，`local_mktemp=1` 已验证可写，与 conan-home 不同区域），复制时不保留只读模式位（`copyfile+u+w`，目录 `u+wx`，容忍 `HMBS_CAP_CHMOD=0`），随后以真实建文件/读/删探针证明可写（`_prove_tree_writable`，失败则如实抛错绝不伪造），最后仅对该副本的 `configure` 把“not writable” fatal 精确降级为 warning（按 marker 定位单个 `print_error`，源码缓存 untouched；探针已过则 `-w` 的 no 属于 access-vs-open 误报）。
- 编译器取 `$ENV{CXX}`（conanbuild 环境的 OHOS clang），找不到则按 c++/g++/clang++/icpx 顺序探测并做 `-fno-rtti` 相容性编译；`get_compiler_info` 编译运行 `make/test/compiler.cpp` 识别 Clang/GCC（只影响警告旗标）。
- socket engine 按 epoll（sys/epoll.h 存在性）→ kqueue → poll → select 自动选择；选择结果回读 `.configure/cache.cfg`（SOCKETENGINE/HAS_*）并打到构建日志。
- `SYSTEM_NAME = lc $^O`，OHOS perl 上报 linux，走 Linux 分支（-pthread -ldl -lrt -rdynamic，DLLEXT=so）；musl 的 `-dumpmachine` 若以 -musl 结尾仅打印警告，不阻塞。
- `main.mk` 末尾 `CORECXXFLAGS += $(CPPFLAGS) $(CXXFLAGS)`、`CORELDFLAGS/PICLDFLAGS += $(LDFLAGS)`，conan 工具链旗标经 `env="conanbuild"` 自动生效，无需硬编码（R33）。
- extra 模块（ssl_openssl/mysql/pgsql/sqlite3/ldap/pcre2/re2/geo_maxmind/argon2/yyjson…）全部经 `--disable-auto-extras` 关闭，核心零外部 `requires`（fmt/http_parser/bcrypt/md5/sha2/utfcpp/lyra 均已 vendor）；该模式下不触发“必须构建 TLS 模块”错误（该检查仅在 auto-extras 开启时执行）。
- `make install` 支持 DESTDIR 但各行均为 `-` 前缀（失败忽略），且真机 HMBS install shim 以 Error 64 忽略关键拷贝（2026-09-27 预检：INSTALL COMPLETE 但包内无 bin/inspircd）；故 package() 先跑 `make DESTDIR=<package> install`，缺二进制时回退为从 `build/<Compiler>-<Ver>/bin/inspircd` 与 `modules/*.so` 手抄（idsgrep/yydecode 先例），之后仍硬校验 `bin/inspircd` 非空 + `modules/core_*.so` 非空，否则拒绝出包。

## 上游测试审计（结论：no_tests）

- `make/template/main.mk` 目标扫描：all/clean/configureclean/debug/install/deinstall/distclean/finishmessage/help/mod-header/std-header/target——无 check/test/installcheck 目标。
- `make/test/*.cpp`（compiler/arc4random_buf/clock_gettime/getentropy/kqueue）是 Configure 编译并运行的特性探测，结果进 `.configure/cache.cfg`，无注册、无计数。
- `tools/testssl` 是 TLS 辅助脚本（随包安装为 inspircd-testssl），不是测试运行器。
- 上游唯一质量门是 `.github/workflows/ci-irctest.yml` 调用的外部 irctest pytest 套件：需安装好的 live server + Anope/Atheme 服务 + pytest 生态，无法在 conan 构建内运行。
- 因此 `test_package/MANIFEST.yml` 按 no_tests 申报（`upstream_test_total: 0` + 逐项 audit），build() 输出 `HMBS_UPSTREAM_TEST_RESULT status:no_tests` 并落盘 `res/upstream_test_result.json` 供 test_package 复述（cache-hit 轮次）。

## test_package（R34，5 用例，真机实测）

`test_inspircd.sh`（POSIX sh + `${HMBS_PYTHON3:-python3}` 做 TCP，HMBS 注入）：

1. 二进制存在/可执行/非空；
2. `inspircd --version`（无需配置文件，ParseOptions 先于配置加载）退出 0 且输出含 `InspIRCd-4.7.0`；
3. 最小生成配置（server/admin/bind 127.0.0.1 高端口/pid/log/path moduledir 指向包内 modules）以后台 `--nofork --nolog --nopid --runasroot` 启动，30 秒内 TCP 建连成功（超时则倾倒 server.out + inspircd.log 尾部）；
4. 真实 IRC 握手：NICK/USER 后收到含 ` 001 hmbs01 ` 的 welcome 数值（逐行打印 transcript，非空+精确内容双断言），随后 QUIT；
5. kill 后端口释放（反向对照，残留进程无法冒充通过）。

## 待真机预检确认项（本轮未提交，待 HMBS 后台验证）

- OHOS sysroot 下 `-ldl -lrt` 链接是否成立（musl 桩库预期成立；若缺则在 main.mk Linux 分支上打补丁）。
- 探测到的 socket engine（预期 epoll）与 `HAS_*` 结果（cache.cfg 回读）。
- `install` 命令可用性（若缺则改手抄二进制+模块，idsgrep/yydecode 先例）。
- package() 回退拷贝的 `p/bin` 目录创建：2026-09-27 预检 `os.makedirs(bindir, exist_ok=True)` 报 FileExistsError（exist_ok 仅豁免已存在目录，`make install` 的 `-` 忽略规则+shim Error 64 可在包内留下同名文件/断链），已加 `_ensure_package_dir` 先识别并清理占位文件再建目录。
- 构建日志降载：2026-09-27 预检在模块编译中段出现 `Connection closed by remote host`（无编译错误行，属传输/会话中断），build() 不再强制 `INSPIRCD_VERBOSE=1`，改用上游默认精简输出（`--silent` 的 `BUILD:` 短行，产物一致），避免 ~200 个完整 clang++ 命令行撑大日志。
- 5 用例真实通过率回填 PR 正文（本轮不猜数字）。
