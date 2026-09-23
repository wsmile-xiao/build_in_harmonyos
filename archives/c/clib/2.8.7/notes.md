# clib 2.8.7 适配笔记

## 编译环境
- 构建系统: makefile(无 configure 脚本;纯 Makefile + 构建期特性探测)
- 编译日期: 2026-09-07
- 编译器: /data/service/hnp/bin/clang(OHOS aarch64,clang 15.0.4)
- 状态: built
- Conan: 2.29.1(OHOS 适配版)/ profile: ci/conan/profiles/ohos-aarch64

## 编译步骤

1. `conan install --requires=curl/8.15.0 --build=never` 验证依赖 binary 可取得(W0)。
2. conan source:下载官方 tag tarball 并核对 sha256。
3. `apply_conandata_patches`:应用 0001(http-get CA 运行时探测)与 0002(测试构建适配)。
4. 配方 build() 生成 curl-config shim:Makefile 硬编码 `$(shell curl-config --cflags/--libs)`
   探测 libcurl;发行 curl 包内 curl-config 的 prefix 固化打包机路径(实测指向不存在的
   `.conan2/p/b/...`)不可用;shim 输出依赖注入的真实 include/lib 路径并前置 PATH。
5. `make -j1 CC=<profile clang> CFLAGS=-O2` → 9 个产物全部链接成功:
   clib / clib-install / clib-search / clib-init / clib-configure / clib-build /
   clib-update / clib-upgrade / clib-uninstall。
6. package():`conan.tools.files.copy` 逐个复制 9 个产物到 bin/(设备无 coreutils install)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 主构建链接期 `undefined symbol: pthread_cancel` 风险 | musl libc 不实现 POSIX 线程取消 API(知识 E085) | 无需补丁:上游 scripts/feature-test-pthreads 在构建期做特性测试(OHOS 上链接失败)→ Makefile 不定义 HAVE_PTHREADS → 走上游自带串行回退路径(clib-package.c `#ifndef HAVE_PTHREADS` 分支) |
| 2 | prescan 报 secure_getenv 3 处(critical/medium) | musl 无 secure_getenv 符号(实测 `_GNU_SOURCE` 下仍 undefined symbol) | 无需补丁:三处均有 `#ifdef _GNU_SOURCE` 守卫且默认构建(c99)未定义该宏 → 走 getenv 回退;prescan 按源码文本命中属死代码误报 |
| 3 | 包安装/搜索等全部 HTTPS 操作报 `CURLE_SSL_CACERT (60)`(探针实测 `unable to get local issuer certificate`) | OHOS 无 /etc/ssl 默认 CA;Conan libcurl 编译期默认 CAINFO 指向不存在路径;clib 源码不设置 CURLOPT_CAINFO;libcurl 忽略 SSL_CERT_FILE env(工具层 CURL_CA_BUNDLE 语义不适用 libcurl) | 补丁 0001:vendored deps/http-get 运行时探测(CURL_CA_BUNDLE/SSL_CERT_FILE env → 常见 Linux CA 文件 → SSL_CERT_DIR env 与 /system/etc/security/certificates 目录)并显式设置 CURLOPT_CAINFO/CURLOPT_CAPATH;buffer 与 file 两条请求路径都覆盖;无平台条件编译 |
| 4 | 测试构建 `-DHAVE_PTHREADS` 硬编码无法链接 | test/package/Makefile 绕过了上游特性探测 | 补丁 0002:改走同一 `$(shell ../../scripts/feature-test-pthreads && echo ...)` 探测 |
| 5 | 测试 Makefile 编译缺 curl 头文件/库路径 | 上游测试 Makefile 依赖系统 curl 安装路径(无 curl-config 调用) | 补丁 0002:新增 CURL_CFLAGS/CURL_LIBS make 变量(默认空,不设时上游行为不变) |
| 6 | feature-test-pthreads / uninstall.sh 直接执行报 `/bin/bash: bad interpreter` | 设备无 /bin/bash;profile 提供 CONFIG_SHELL=/data/service/hnp/bin/bash | 补丁 0002:shebang 改为 hnp bash |
| 7 | test.sh 用例发现为空,12 个 shell 集成测试未被执行 | 设备 HMDFS 将文件模式规范化为 770(chmod 771 也被剥 o+x),`find -perm -111` 永不匹配 | 补丁 0002:用例发现改为 `find test/*.sh -type f`(上游全部 .sh 本就可执行);属设备文件系统限制的测试基础设施适配 |
| 8 | 设备无 coreutils install 命令 | — | package() 用 conan.tools.files.copy 替代 make install |
| 9 | conandata 源码 tarball 首次下载即遇到一次 HTTP 000(curl exit 35 SSL 连接错误) | 设备出口间歇性连接重置(workflow §11.1 已知) | 重试即成功;上游测试脚本自带重试逻辑(clib_package retries=3) |

## 源码修改

- `patches/0001-http-get-ca-store-probe.patch`:deps/http-get/http-get.c 增加运行时 CA 库探测
  (http_get_apply_ca_store),两条请求路径(http_get_shared / http_get_file_shared)生效。
- `patches/0002-test-build-ohos-pthreads-curl-flags.patch`:test/package/Makefile、
  test/cache/Makefile、scripts/feature-test-pthreads、test.sh、test/uninstall.sh。
  全部为测试基础设施适配;12 个 shell 测试脚本与 61 个 C 测试用例逻辑零修改。

## 依赖版本

- curl/8.15.0(Conan ohpcd;传递依赖 openssl/3.5.6.1、zlib/1.3.1.1)
- libcurl 以动态库链接;openssl 静态链入 Conan libcurl.so(实测 NEEDED 仅 libc)

## 上游测试验证结果(2026-09-07 设备实测)

- 统计口径:describe it() 用例(C)/ shell 脚本;取数:日志去 ANSI 后
  `grep -c "✓"`、`grep -c "(✓)"`。
- C describe 用例:TOTAL=61 PASS=61 FAIL=0 SKIP=0 NOT_RUN=0
  (test/package 12 个程序 56 用例 + test/cache 1 个程序 5 用例)
- shell 集成测试:TOTAL=12 PASS=12 FAIL=0 SKIP=0 NOT_RUN=0
- 合计:TOTAL=73 PASS=73 FAIL=0 SKIP=0 NOT_RUN=0
- test_package 消费者断言 13 项(分母双环境一致);tp6 clib-search 真实 HTTPS 为条件观测项:设备 PASS(无网环境 SKIP 有据,见 CI 日志)
- 执行方式:沙箱 HOME(避免污染真实 ~/.clib);TMPDIR 指向任务私有目录;
  curl-config shim 与 CURL_CFLAGS/CURL_LIBS 注入;日志见 reports/。
- `make test` 的上游入口 test.sh 逐段执行(与上游 CI 等价);测试构建经由
  补丁 0002 适配(用例逻辑未动,逐项说明见 PR 模板)。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/clib | ~410 KB | 主程序 |
| bin/clib-install | ~414 KB | 安装子命令 |
| bin/clib-search | ~410 KB | 搜索子命令 |
| bin/clib-init | ~410 KB | 项目初始化子命令 |
| bin/clib-configure | ~414 KB | 配置子命令 |
| bin/clib-build | ~418 KB | 构建子命令 |
| bin/clib-update | ~410 KB | 更新子命令 |
| bin/clib-upgrade | ~414 KB | 升级子命令 |
| bin/clib-uninstall | ~410 KB | 卸载子命令 |

## 注意事项

- `clib <command>` 通过 `which("clib-<command>")` 在 PATH 中分发;包内 9 个工具同目录
  安装,消费者 PATH 含包 bindir 即可完整使用。
- clib 运行时缓存在 `$HOME/.clib`;CA 探测顺序:env → 标准 Linux 路径 → 设备证书目录;
  若环境两者皆无,HTTPS 将维持上游默认失败行为(不做静默降级)。
- OHOS 条件编译:本适配零 `__OHOS__` 宏;全部平台差异经构建期特性探测与运行时探测解决。
