# yadifa 3.0.9 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake 工程；测试经 CTest 驱动，BUILD_TESTING=On）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15（OHOS aarch64，Conan profile ci/conan/profiles/ohos-aarch64）
- 依赖: openssl/3.5.8.1（W0 实测 ohpcd 远端返回 Downloading recipe 取回，非本地缓存假成功）
- 状态: built

## 症状与根因

| # | 症状（一手读数） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | configure 期 crypto : not found（EURidToolbox.cmake:660 kvfatal） | 上游自带 cmake/FindOpenSSL.cmake 只探测硬编码系统路径（/usr/local/openssl、/usr/local、/usr），Conan 依赖对它不可见 | patches/0001 把无条件 set(OPENSSL_ADDITIONAL_PATH) 改成 if(NOT DEFINED) 以接受 -D 注入；配方 generate() 传 openssl 的 package_folder（conan2 组件对象没有 cpp_info.rootpath，用过会 AttributeError） |
| 2 | sockaddr_storage 重复定义、find_library 找不到独立 libpthread、affinity 符号缺失 | 上游按 glibc 头布局与 glibc 线程扩展编写 | patches/0002 pthread 回退 + build() 期 -D__MUSL__ 激活上游自带守卫；patches/0003 守卫 pthread_setaffinity_np |
| 3 | 上游测试大面积 EROFS（旧一轮整份日志 145 处 Read-only file system） | OHOS 的 /tmp 是只读文件系统，而 yadifa 测试把临时路径硬编码为 /tmp（源码 56 处），TMPDIR 对硬编码路径无效 | yatest_tmpredir.c 测试期 LD_PRELOAD 路径重写 shim（11 个具名路径 API）；本轮整份日志 EROFS 命中 0 处 |
| 4 | config_logger 组残留 2 项 EROFS（旧一轮） | 这些用例写 //tmp/... 双斜杠前缀，绕过 shim 最初的 /tmp/ 字面量前缀匹配 | shim rewrite() 先折叠前导斜杠串（strspn）再匹配 tmp 分量；本轮该组已从失败名单消失 |
| 5 | 消费者测试在 conan create 的 test() 阶段 rc=127；手工执行包目录产物 rc=126，sh 报 Operation not permitted | CMake 安装期改写已安装 ELF 的 RPATH，使链接期嵌入的 .codesign 段与产物不同源，内核拒绝对该文件 execve 与 dlopen；同一字节流的构建树孪生件可正常执行，失败件拷到 ~/tmp/uc2 并 chmod 755 仍 126 ⇒ 与权限位、所在路径、库搜索路径无关；cmp 显示两文件自第 15749 字节起分叉 | package() 安装后对 bin/ 与 lib/ 的 ELF 实体无条件执行 objcopy --remove-section .codesign + binary-sign-tool -selfSign 1 + chmod 0755（先例 archives/a/acme-client/0.1.15-portable/conanfile.py:179-192）；本轮重签取证见下文 |
| 6 | yadifa -V 与 yadifa --version 都打印版本但退出码为 1 | 上游客户端对版本旗标走非成功返回路径（-h 才返回 0），构建树孪生件与包目录产物读数一致 ⇒ 消费者测试原先断言 rc==0 是对上游行为的错设预期 | 消费者测试改为版本用例只断言版本串出现在输出中（实质断言不降），另加一条 -h 成功路径断言要求 rc==0 且有输出；断言数 3 到 4，用例分母未动 |
| 7 | 历史：verify 中途 ohc-run 抛 UnicodeDecodeError | ctest 失败输出含非 UTF-8 字节 | 驱动侧 PYTHONIOENCODING=utf-8:replace；本轮失败量下降后未再触发 |

## 最小复现
1. 取上游官方 tag 归档 v3.0.9（sha256 dbdf4b07bdac616b01a07a5f511ba4083720607071c4ef5f8b49327de0fcc2e7），按本配方 conan create 即可复现问题 1 与问题 5。
2. 问题 5 不依赖配方的复现：对包目录产物直接执行，再与构建树孪生件对照。
   - cmp <build>/bin/yadifa/yadifa <pkg>/bin/yadifa 报分叉；<pkg>/bin/yadifa -V 得 rc=126；<build>/bin/yadifa/yadifa -V 正常打印版本。
   - 只对 <pkg>/bin/yadifa 重签后 EPERM 消失，转为 Error loading shared library libdnslg.so.10.0.0；再对 lib/ 下三枚 .so.10.0.0 重签后 yadifa -V 打印 yadifa 3.0.9 (2026-03-24) ⇒ 可执行文件与私有库都要安装后重签。
3. 问题 4 的复现：旧一轮日志里 //tmp/ 命中非零且 /tmp/ 命中非零；本轮同一读数均为 0。

## 已试过的失败方案
- 再给 Conan 依赖加搜索路径（CMAKE_PREFIX_PATH、OPENSSL_ROOT_DIR）：上游自带 finder 不查这些变量，仍 crypto not found。
- 只在 test_package 里设 LD_LIBRARY_PATH 或改 PATH：包目录产物仍 rc=126，拒绝发生在 execve 之前（签名校验），与库搜索路径无关。
- 只重签可执行文件：报 Error loading shared library，私有 .so 同为被拒对象（见最小复现 2）。
- 用 --disable-*、缩小 ctest 正则、排除失败测试目标来凑绿：未采用；858 条注册用例保持全量真实执行。
- 逐个补丁改上游测试里的 /tmp 字面量（56 处）：放弃，改由测试期 shim 承担，不污染上游 diff。

## 最终方案
CMake 配方 + 3 个 portability 补丁 + 测试期 LD_PRELOAD /tmp 路径重写 shim + 安装后无条件重签包内 ELF + 消费者测试（回环 DNS 双向断言、版本串断言、-h 成功路径断言）。

## 适用边界
- shim 只作用于动态链接的测试进程，且只在 ctest 阶段注入；打包产物与生产运行路径不含 LD_PRELOAD。
- shim 只重写绝对 /tmp 前缀（含折叠后的多斜杠形态），其它路径透传；YADIFA_TEST_TMPDIR 未设置时整体禁用。
- 重签只处理包目录 bin/ 与 lib/ 下的 ELF 实体文件（跳过符号链接）；宿主缺少 /data/service/hnp/bin/ 下 binary-sign-tool 与 llvm-objcopy 时打印提示并跳过，此时问题 5 会复现（必须在具备签名工具的机器上构建）。
- glibchooks 依赖面（下表 SEGFAULT 组）在 musl/OHOS 上根本不可用，不属本包修复范围。

## 源码修改
- patches/0001-findopenssl-additional-path-injectable.patch（portability）
- patches/0002-dnscore-pthread-musl-fallback.patch（portability）
- patches/0003-thread-affinity-musl-guard.patch（portability）
- yatest_tmpredir.c（exports，非补丁，仅测试阶段注入）
- 不改任何上游 C 源文件（补丁只作用于构建脚本层）

## 上游测试五维账本（逐值取自本地留档的同构轮 conan create 全量输出；按 §19 `*.log` 不随 PR、磁盘留档；2026-09-28 01:26 CI 同构轮，**绑 HEAD `8dd95cfcf7`（不是当前 HEAD `e27fa004`，跨轮读数须标轮次）**）
- N_static = 860：lib/*/tests/*/CMakeLists.txt 里 add_test( 的静态声明计数；上游 autotools 入口无 check 目标（grep TESTS/check_PROGRAMS 为空）
- N_registered = 858：ctest 实际注册（与静态差 2 项系上游 ${NAME} 模板条件展开差异，非本适配引入）
- N_executed = 858：注册用例全部真实执行，Total Test time (real) = 612.73 sec（log:19901）
- N_passed = 758 / N_failed = 100（log:19899，逐条清单自 log:19904 起）
- N_skipped = 0（未使用任何排除或跳过开关，分母未动）
- 失败逐组计数（12 组）：
  - fdtools 51 项
  - rest_server 19 项
  - dns_message 8 项
  - xfr_input_stream 7 项
  - mutex 5 项
  - file_input_stream 3 项
  - chroot 2 项
  - crypto 1 项
  - error_state 1 项
  - parser 1 项
  - pushback_input_stream 1 项
  - rewind_input_stream 1 项
- 状态面计数：SEGFAULT 70、Failed 23、Timeout 4、SIGSYS 2、SIGPIPE 1
- EROFS 读数：整份日志 Read-only file system 命中 0 处、//tmp/ 命中 0 处（旧一轮为 145 与 大于 0）
- N_consumer = 1 个 test_package 程序 / 4 条断言（回环查询双向 2 条、版本串 1 条、-h 成功路径 1 条）

## 失败项逐组归因（不笼统合并）
- fdtools 与 rest_server 两组共 70 项 SEGFAULT：这些测试二进制 include glibchooks/glibchooks_controller.h（glibc 内部符号 interposition 框架），musl 无对应内部布局，启动即崩；带与不带 shim 的 A/B 同样崩 ⇒ 与本轮 /tmp 方案无关，按平台边界逐用例申报，不硬修（硬修等于重写上游测试框架）。
- chroot 组 SIGSYS：OHOS seccomp 策略按 syscall 号拦截 chroot()，内核级边界。
- error_state 与 mutex 等 3 项 Timeout(120s)：上游线程/告警时序敏感用例在本机并发下超时，输出停在 YATEST: ... begin 之后无进展。
- 其余断言级失败（dns_message、xfr_input_stream、mutex、file_input_stream、parser、crypto、rewind_input_stream、pushback_input_stream、error_state）逐条首错留在 --output-on-failure 输出中，形如 file_input_stream: unexpected error or EOF reading sample: 0 instead of 4837、pushback_test: failed to read 552, got 553、80021005 = PARSEINT_ERROR、failed to call every alarm event: 5/10，均为 glibc/musl 与内核行为差异导致的断言失败，不含 EROFS。


## 附：100 项未通过逐条清单（取自本地留档同构轮 `conan create` 全量输出，按 §19 `*.log` 不随 PR）

汇总行：`88% tests passed, 100 tests failed out of 858`（`Total Test time (real) = 612.73 sec`）。

| # | 用例 | 失败形态 |
|---|---|---|
| 1 | `fdtools-test-success_test` | SEGFAULT |
| 2 | `fdtools-test-readfully_test` | SEGFAULT |
| 3 | `fdtools-test-readfully_error_short_read_test` | SEGFAULT |
| 4 | `fdtools-test-readfully_error_zero_read_test` | SEGFAULT |
| 5 | `fdtools-test-readfully_limited_test` | SEGFAULT |
| 6 | `fdtools-test-readfully_limited_slow_test` | SEGFAULT |
| 7 | `fdtools-test-readfully_limited_error_short_read_test` | SEGFAULT |
| 8 | `fdtools-test-readfully_limited_error_zero_read_test` | SEGFAULT |
| 9 | `fdtools-test-readfully_limited_ex_test` | SEGFAULT |
| 10 | `fdtools-test-readfully_limited_ex_slow_test` | SEGFAULT |
| 11 | `fdtools-test-readfully_limited_ex_error_short_read_test` | SEGFAULT |
| 12 | `fdtools-test-readfully_limited_ex_error_zero_read_test` | SEGFAULT |
| 13 | `fdtools-test-writefully_test` | SEGFAULT |
| 14 | `fdtools-test-writefully_limited_test` | SEGFAULT |
| 15 | `fdtools-test-writefully_limited_slow_test` | SEGFAULT |
| 16 | `fdtools-test-sendfully_limited_test` | SEGFAULT |
| 17 | `fdtools-test-sendfully_limited_slow_test` | SEGFAULT |
| 18 | `fdtools-test-recvfully_limited_ex_test` | SEGFAULT |
| 19 | `fdtools-test-recvfully_limited_ex_slow_test` | SEGFAULT |
| 20 | `fdtools-test-readtextline_test` | SEGFAULT |
| 21 | `fdtools-test-unlink_ex_test` | SEGFAULT |
| 22 | `fdtools-test-file_get_absolute_path_test` | SEGFAULT |
| 23 | `fdtools-test-file_get_absolute_parent_directory_test` | SEGFAULT |
| 24 | `fdtools-test-open_ex_test` | SEGFAULT |
| 25 | `fdtools-test-open_create_ex_test` | SEGFAULT |
| 26 | `fdtools-test-open_create_ex_nolog_test` | SEGFAULT |
| 27 | `fdtools-test-close_ex_test` | SEGFAULT |
| 28 | `fdtools-test-socketclose_ex_test` | SEGFAULT |
| 29 | `fdtools-test-close_ex_nolog_test` | SEGFAULT |
| 30 | `fdtools-test-fsync_ex_test` | SEGFAULT |
| 31 | `fdtools-test-fdatasync_ex_test` | SEGFAULT |
| 32 | `fdtools-test-dup_ex_test` | SEGFAULT |
| 33 | `fdtools-test-dup2_ex_test` | SEGFAULT |
| 34 | `fdtools-test-truncate_ex_test` | SEGFAULT |
| 35 | `fdtools-test-ftruncate_ex_test` | SEGFAULT |
| 36 | `fdtools-test-fd_getsockettype_test` | SEGFAULT |
| 37 | `fdtools-test-filesize_test` | SEGFAULT |
| 38 | `fdtools-test-file_exists_test` | SEGFAULT |
| 39 | `fdtools-test-file_is_link_test` | SEGFAULT |
| 40 | `fdtools-test-file_is_directory_test` | SEGFAULT |
| 41 | `fdtools-test-file_mtime_test` | SEGFAULT |
| 42 | `fdtools-test-fd_mtime_test` | SEGFAULT |
| 43 | `fdtools-test-mkdir_ex_test` | SEGFAULT |
| 44 | `fdtools-test-fd_setcloseonexec_test` | SEGFAULT |
| 45 | `fdtools-test-fd_setnonblocking_test` | SEGFAULT |
| 46 | `fdtools-test-fd_setblocking_test` | SEGFAULT |
| 47 | `fdtools-test-dirent_get_file_type_test` | SEGFAULT |
| 48 | `fdtools-test-readdir_forall_test` | SEGFAULT |
| 49 | `fdtools-test-access_check_test` | SEGFAULT |
| 50 | `fdtools-test-mkstemp_test` | SEGFAULT |
| 51 | `fdtools-test-rmdir_ex_test` | SEGFAULT |
| 52 | `file_input_stream-test-read_consistency4096_test` | Failed |
| 53 | `file_input_stream-test-read_consistency4096ex_test` | Failed |
| 54 | `file_input_stream-test-read_consistency4096fd_test` | Failed |
| 55 | `rewind_input_stream-test-rewind_test` | Failed |
| 56 | `pushback_input_stream-test-pushback_test` | Failed |
| 57 | `xfr_input_stream-test-axfr_delayed4_tcplen0_test` | Failed |
| 58 | `xfr_input_stream-test-axfr_delayed0_dnserror_test` | Failed |
| 59 | `xfr_input_stream-test-axfr_delayed0_notauthoritative_test` | Failed |
| 60 | `xfr_input_stream-test-ixfr_simple_test` | Failed |
| 61 | `xfr_input_stream-test-axfr_badsoaformat_test` | Failed |
| 62 | `xfr_input_stream-test-axfr_unsupportedtype_test` | Failed |
| 63 | `xfr_input_stream-test-axfr_truncatedsoa_test` | Failed |
| 64 | `chroot-test-simple_test` | SIGSYS |
| 65 | `chroot-test-trailing_test` | SIGSYS |
| 66 | `crypto-test-simple_test` | SIGPIPE |
| 67 | `dns_message-test-header_test` | Failed |
| 68 | `dns_message-test-network_dns_message_query_but_truncated_test` | Failed |
| 69 | `dns_message-test-dns_message_map_test` | Failed |
| 70 | `dns_message-test-dns_message_process_over_query_test` | Failed |
| 71 | `dns_message-test-dns_message_process_over_notify_test` | Failed |
| 72 | `dns_message-test-dns_message_process_over_update_test` | Failed |
| 73 | `dns_message-test-dns_message_process_over_ctrl_test` | Failed |
| 74 | `dns_message-test-dns_message_process_query_over_query_test` | Failed |
| 75 | `error_state-test-error_state_test` | Timeout |
| 76 | `mutex-test-exclusion_group8_test` | Timeout |
| 77 | `mutex-test-exclusion_shared_mutex8_test` | Timeout |
| 78 | `mutex-test-exclusion_shared_mutex_recursive8_test` | Timeout |
| 79 | `mutex-test-mutex_semaphore_test` | Failed |
| 80 | `mutex-test-mutex_semaphore_shared_mem_test` | Failed |
| 81 | `parser-test-parser_get_network_service_port_from_next_word_test` | Failed |
| 82 | `rest_server-test-simple_page_test` | SEGFAULT |
| 83 | `rest_server-test-path_variable_bin_page_test` | SEGFAULT |
| 84 | `rest_server-test-simple_bin_page_test` | SEGFAULT |
| 85 | `rest_server-test-signal_test` | SEGFAULT |
| 86 | `rest_server-test-request_overflow_test` | SEGFAULT |
| 87 | `rest_server-test-invalid_request_test` | SEGFAULT |
| 88 | `rest_server-test-notfound_test` | SEGFAULT |
| 89 | `rest_server-test-setup_test` | SEGFAULT |
| 90 | `rest_server-test-pid_locked_test` | SEGFAULT |
| 91 | `rest_server-test-wrong_listen_test` | SEGFAULT |
| 92 | `rest_server-test-socket_error_test` | SEGFAULT |
| 93 | `rest_server-test-ipv6only_error_test` | SEGFAULT |
| 94 | `rest_server-test-reuseaddr_error_test` | SEGFAULT |
| 95 | `rest_server-test-reuseport_error_test` | SEGFAULT |
| 96 | `rest_server-test-bind_error_test` | SEGFAULT |
| 97 | `rest_server-test-listen_error_test` | SEGFAULT |
| 98 | `rest_server-test-uri_test` | SEGFAULT |
| 99 | `rest_server-test-rest_client_success_test` | SEGFAULT |
| 100 | `rest_server-test-rest_client_chunk_test` | SEGFAULT |

## 验证结果

```bash
CONAN_HOME=$HOME/tmp/ch/home-主理-43-yadifa python3 scripts/ohc-run.py conan-verify yadifa 3.0.9
```
- 判决：**Verdict**: PASS（2026-09-28 00:19 conan-verify 轮与 01:26 CI 同构轮一致）
- 门禁面：G0 ✅ PASS；G1 ✅ PASS；G2 ✅ PASS；G3 ✅ PASS；G4 ✅ PASS；L2 ✅ PASS；L4 ✅ PASS；L5 ✅ PASS
- W3 结果件 .ci-result.json：exit_code=0、step=W3_local_ci、integrity_hash=7865aa5c59d6a95f、log_sha256=97a853ed…（finish 2026-09-28 01:27 写入）
- 安装后重签取证：
  - log:20345 yadifa/3.0.9: resigned packaged ELF: /storage/Users/currentUser/tmp/ch/home-主理-43-yadifa/p/b/yadifc67e0507d7a9c/p/bin/yadifad
  - log:20346 yadifa/3.0.9: resigned packaged ELF: /storage/Users/currentUser/tmp/ch/home-主理-43-yadifa/p/b/yadifc67e0507d7a9c/p/bin/yadifa
  - log:20347 yadifa/3.0.9: resigned packaged ELF: /storage/Users/currentUser/tmp/ch/home-主理-43-yadifa/p/b/yadifc67e0507d7a9c/p/bin/yakeyrolld
  - log:20348 yadifa/3.0.9: resigned packaged ELF: /storage/Users/currentUser/tmp/ch/home-主理-43-yadifa/p/b/yadifc67e0507d7a9c/p/lib/libdnscore.so.10
  - log:20349 yadifa/3.0.9: resigned packaged ELF: /storage/Users/currentUser/tmp/ch/home-主理-43-yadifa/p/b/yadifc67e0507d7a9c/p/lib/libdnsdb.so.10
  - log:20350 yadifa/3.0.9: resigned packaged ELF: /storage/Users/currentUser/tmp/ch/home-主理-43-yadifa/p/b/yadifc67e0507d7a9c/p/lib/libdnslg.so.10
- 消费者测试取证：
  - log:20438 PASS: packaged yadig queried 127.0.0.1:41926 and printed 192.0.2.42
  - log:20439 PASS: server verified the encoded qname and qtype of the request
  - log:20440 PASS: packaged yadifa reports its version: yadifa 3.0.9 (2026-03-24)
  - log:20442 PASS: packaged yadifa -h exits 0 (400 bytes)CONSUMER TEST PASSED (4 assertions)

## 可用 / 不可用 / 未测

| 能力面 | 结论 | 证据（现存日志真实行） |
|--------|------|------------------------|
| 打包可执行文件可被 execve 并返回版本串 | 可用 | 重签取证 log:20345 起；验证结果节的消费者取证行 |
| 包内客户端对回环 DNS 服务端发查询并解析应答 | 可用 | log:20442 |
| 上游 CTest 套件（dnscore、config、流、线程等） | 部分可用（758/858 通过，100 项按上文根因分组未通过） | log:19899、log:19904 |
| yadifad 服务进程长期运行与区域加载 | 未测（本包未做常驻服务与区域文件场景） | 无（不得写成可用） |
| yadifa-keygen、yadifa-zonesign、yakeyrolld | 未测（仅随包安装，未单独驱动） | 无 |
| glibchooks 依赖的 fdtools 与 rest_server 测试面 | 不可用（平台边界） | log:19904 起的 SEGFAULT 组 |

## 路径 B 判定素材（只给证据，定案归主理）
- 症状家族在库内既有覆盖（knowledge/graph/index.tsv 行号）：E002 第 228 行（/tmp 只读，处置口径 set-env-var）、E265 第 491 行（用上游可配环境变量覆盖 SHELL/TMPDIR/FS_IMG 绕开只读 /tmp）、E363 第 589 行（只读 /tmp 叠加假绿与正向完成标记）、E461 第 686 行（AF_UNIX + tmpdir + EROFS）。
- 同族草稿（手工 grep knowledge/drafts/；draft-review 不扫该目录，故不能拿它的建议当查重凭据）：DRAFT-ohos-otmpfile-tmpdir-shim（LD_PRELOAD 重定向**无名**临时文件，pycairo 触发）、DRAFT-libopaque-1.0.1-munit-tmpfile-redirect-tmpdir-shim（构建期 -Dtmpfile= 重命名，条目内明确写着不用 LD_PRELOAD）、DRAFT-boost1.84-coroutine-1.84.0-readonly-tmpdir-redirect-guard-page-fallback。本包草稿的通道是**具名 /tmp 前缀在 11 个路径 API 上的整套件重写（含重复斜杠折叠）**，与上述三条的覆盖面差需定案时对齐行号。
- 本包已提交的草稿对：knowledge/drafts/DRAFT-yadifa-3.0.9-ld-preload-tmp-redirect.kv 与 .md；Issue #3201。
- 第二条候选面（本包新撞、上面条目均未写）：CMake 安装期改写 RPATH 使 .codesign 与产物不同源，导致包目录产物 execve 与其私有 .so 加载双双被拒。库内相邻条目只覆盖签名工具缺失与构建树闭包面（E200 false、E489 false、E502 false）。一手读数见问题 5 与最小复现 2。

## 3+2 声明
- **适配路径**：路径 B（Conan 配方 + 知识草稿）
- **使用知识库**：E002（/tmp 只读）、E017（官方源标量与镜像注入回滚）、E092（CMake 不识 HarmonyOS 平台）
- **知识库扩展**：knowledge/drafts/DRAFT-yadifa-3.0.9-ld-preload-tmp-redirect（LD_PRELOAD 具名 /tmp 路径重写复活上游测试套件）
- **关联 Issue**：#3201

## 为什么要做这个包
权威 DNS 服务器套件（EURid 维护），体量中等。本包把两处 OHOS 特有墙（只读 /tmp、安装后签名失效）各落成可复用做法，后一条直接惠及所有交付可执行文件的配方。

---
**编译结束**: 2026-09-25
**最终状态**: built

## 证据件命名说明
- reports/conan-create-full.log 是同配方、同 profile、同 CONAN_HOME 的一次完整 conan create 全量输出（含 858 条 CTest 逐条结果与 test_package 四条断言）。**该 `*.log` 按 §19 不随 PR、仅磁盘留档（下一行轮次说明不变）**。本文件现内容为 2026-09-28 01:26 轮（绑 HEAD 8dd95cfcf7，由 ci/conan/build_and_test.sh 真跑产出，即 CI 同构路径）；本文全部行号引用指向该文件。
- 轮次说明：09-25 20:32 轮（858 执行 / 750 过 / 108 败）留档于 ~/tmp/uc2/qw2-yadifa/conan-create-full.0925.bak.log 且可自 git 历史回溯；09-28 00:19 conan-verify 轮为 755/103；本轮（01:26 CI 同构）为 758/100。ctest 断言级失败计数存在轮间波动（同配方同机），交付数字一律以本文件（最新全量）为准。
- 框架缺陷记录：ohc-run 在解码子进程输出时对 ctest 失败块里的非 UTF-8 字节抛 UnicodeDecodeError（09-25 20:17 实拍 position 1452624；09-28 finish 两轮复现 position 1456029/1454092）。PYTHONIOENCODING 对 subprocess.run(text=True) 无效（python3.14 走 locale+strict）；本轮经 PYTHONPATH 注入 sitecustomize 将 subprocess.run 默认 errors 放宽为 replace 绕行（rc 语义不变，未改共享框架文件）。
---

**编译结束**: 2026-09-28 01:10
**最终状态**: built
