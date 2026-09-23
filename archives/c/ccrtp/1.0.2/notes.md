# ccrtp 1.0.2 — OHOS 适配笔记

## 上游信息
- 名称: GNU ccRTP
- 版本: 1.0.2
- 仓库: https://www.gnu.org/software/ccrtp/
- 源码: https://ftp.gnu.org/gnu/ccrtp/ccrtp-1.0.2.tar.gz（sha256 对应 1.0.2 归档）
- 许可证: GPL-2.0-or-later
- 构建系统: Autotools (configure + make)

## 适配要点
1. **依赖**: 要求 commoncpp2 >=1.0.0，OHOS 已发布 commoncpp2/1.8.1，前向兼容，直接依赖 1.8.1；zlib/openssl 为 commoncpp2 传递依赖。
2. **config.guess/sub**: 2003 年版本不识别 aarch64-unknown-linux-ohos，需为 config/config.guess 插入 `*-linux-ohos*` 分支，config/config.sub 将 `linux-gnu*` 扩展为 `linux-gnu* | linux-ohos*`。
3. **HMDFS getcwd 失效**: conan 缓存父目录对 getcwd() 不可达，autoconf 的 `ac_pwd=`pwd`` 判定失败。build() 入口 `os.chdir(build_folder)` + `os.environ["PWD"]=build_folder`（shell pwd 走逻辑路径），并将 configure 的 `ac_pwd=`pwd` && test -n "$ac_pwd" &&` 改为 `ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"` 兜底（aribb24/nspr/cdecl/asterisk-flite 同款）。
4. **临时目录与 umask**: HMFS 上 /tmp 只读、且 `umask 077 && mktemp -d ./confXXXXXX` 创建的 0700 目录在 setgid 文件系统下不可写。复用 HMBS 注入的 TMPDIR/HMBS_AUTOCONF_MKTEMP_FALLBACK（兜底 build_folder/tmp），patch mktemp 模板为 `${TMPDIR}/confXXXXXX`，并将 `umask 077` 改为 `umask 022`；`ls -t` 与 "newly created file is older" 探测在 fork/getcwd 失败时降级为警告（cdecl 同款）。
5. **SHELL**: HNP bash (/data/service/hnp/bin/bash) 在 HMFS 上启动即 getcwd 失败，改用 HMBS 注入的 SHELL=/bin/sh (CONFIG_SHELL) 执行 configure/make。
6. **C++ 兼容**: 老代码 C++98，需 CXXFLAGS 加 `-std=c++98 -fpermissive -Wno-error -Wno-deprecated-declarations`；鸿蒙缺 `pthread_testcancel`，提供 stub 头并通过 `-include` 注入。
7. **配置**: `CONFIG_SHELL=/bin/sh SHELL=/bin/sh ./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --prefix=/usr --disable-shared --disable-dependency-tracking`，通过 CFLAGS/CXXFLAGS/LDFLAGS 注入依赖头库，PKG_CONFIG_PATH 合并；configure 前对源码树 touch 避免时间戳漂移误判。

## 上游测试
- 上游未提供 `make check` 或 ctest 套件，`demo/` 下 `rtphello/rtpsend/rtplisten` 等为示例程序，其中 `ccrtptest` 在 1.0.2 中被注释掉。经审计源码与构建文件，确认无正式测试框架。
- 因此 `test_package/MANIFEST.yml` 标记 `upstream_tests_exist: false` 并附审计说明，`HMBS_UPSTREAM_TEST_RESULT` 将输出 `status:"no_tests"`。

## 测试验证
- **test_package**: 编译并运行 `test.cpp`，含对 `ccrtp/rtp.h` 的真实 API 调用（`ost::InetHostAddress` 构造、`RTPSession` 创建、`getLocalSSRC()`），验证头文件、库链接与运行时。
- 真机预检将在下一轮由 hmbs 注入，生成 `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 标记。

## 已知限制
- conandata.yml 以多 URL 形式声明源码：主 URL 为 ftp.gnu.org 官方，备选 ftpmirror 与 archive.org。
