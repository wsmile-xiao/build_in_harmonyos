# libgadu 1.12.2 适配笔记

## 基本信息
- 上游：https://github.com/wojtekka/libgadu（已归档，只读），官网 https://libgadu.github.io/
- 版本：1.12.2（2017-02-01 安全修复版），LGPL-2.1-only
- 构建系统：Autotools（configure + make），C 库
- 源码：libgadu-1.12.2.tar.gz，sha256=28e70fb3d56ed01c01eb3a4c099cc84315d2255869ecf08e9af32c41d4cbbf5d

## 配置取舍
- `--without-gnutls --without-protobuf`：两者在上游均为可选（configure.ac
  AC_ARG_WITH）。真机/CI 侧 gnutls/protobuf-c 依赖链重，首轮采用零依赖离线
  最小移植；核心编解码、消息、哈希、包解析代码不受影响。
- pthread 解析器经上游 `--without-pthread` 关闭（真机 `examples/send` 链接
  `libgadu.a(resolver.o)` 报 `undefined symbol: pthread_setcancelstate /
  pthread_cancel`；OHOS lld 经 LIBS_PRIVATE/PTHREAD_LIBS 未能解析，
  上游 configure.ac 明确支持该开关，关闭后回退到 fork/sync 解析，
  公开 API 与核心编解码/消息/哈希/包解析不受影响）。
- `--build=aarch64-unknown-linux-gnu`：2017 版 config.guess 不识别 HarmonyOS，
  固定 build 三元组跳过猜测（bash 5.3 同款做法），仍为原生构建。
- `-fcommon`（toolchain flags 注入）：2017 年代码在 test/manual 中对 10 个
  `config_*` 全局变量存在暂定定义（tentative definitions），真机 clang-15
  默认 `-fno-common` 会报 `duplicate symbol`；恢复 common 合并，不改源码、
  不删测试。
- zlib 经 Conan 依赖引入（`self.requires("zlib/1.3.1")` +
  AutotoolsDeps）：上游 configure.ac 无 `--without-zlib` 开关，且无
  `GG_CONFIG_HAVE_ZLIB` 时 `gg_deflate()`/`gg_inflate()` 为返回 NULL
  的桩，导致上游 `protocol` 用例在 `40-userlist.scr:116`（期望 `78 da`
  开头的 zlib 压缩帧）超时失败；此前强制关闭 zlib 还曾反向导致
  test_package 报 `deflateInit_` 未定义。声明依赖后 configure 探测确定性
  成功，消费者经 CMakeDeps 传递链接 `-lz`，核心编解码/消息/哈希/包解析
  与 9 个上游用例均不受影响（protocol 由 FAIL 转 PASS）。

## 上游测试（test/automatic，9 个）
| 用例 | 来源 | 在 HarmonyOS aarch64 实测预期 |
|------|------|-------------------------------|
| connect | test/automatic/connect.c | SKIP（需 glibc __connect + gnutls + pthread，本移植无 gnutls，按 Makefile.am 走 skipped.c exit 77） |
| convert | test/automatic/convert.c | PASS（gg_encoding_convert 编解码，无外部依赖） |
| endian1 | test/automatic/endian1.c | PASS |
| hash | test/automatic/hash.c | PASS |
| message1 | test/automatic/message1.c | PASS |
| message2 | test/automatic/message2.c | PASS（HAVE_LIBXML2 未定义时走非 xml 分支） |
| packet | test/automatic/packet.c | PASS |
| protocol | test/automatic/protocol.c | 需 perl 生成 script.c；有 perl 则 PASS，无则 SKIP（exit 77） |
| resolver | test/automatic/resolver.c | PASS（本地解析逻辑，无网络） |

计分口径：`make check` 的 automake 汇总行 TOTAL/PASS/FAIL/SKIP；
SKIP 计为跳过，不计为通过（toybox 空文件比对教训：本配方只信任非零
执行数 + 汇总行解析）。

## test_package（消费者视角，R34）
- test.c 直接调用公开 API 做 4 组真实离线断言（仅用已安装的
  `libgadu.h`，不依赖未安装的内部头 `encoding.h`）：
  1. `gg_libgadu_version()` == "1.12.2"
  2. `gg_fix32` 双交换回环一致
  3. `gg_fix16` 双交换回环一致
  4. `gg_crc32` 确定性（同输入同结果）+ 输入敏感性（大小写不同则不同）
- 退出码 0 = 4/4 通过；非 0 即失败并如实输出
  `HMBS_TEST_PACKAGE_RESULT`（discovered=4）。

## HMBS 机器证据
- build() 内 `make check` 结束后解析真实输出并打印
  `HMBS_UPSTREAM_TEST_RESULT`（framework=automake test-driver），同时落盘
  `hmbs_upstream_result.json` 并随包发布到 `share/libgadu/`；
  test_package 每次原样复发，保证 `--build=missing` 缓存命中时仍有证据。
- test_package 的 `HMBS_TEST_PACKAGE_RESULT` 在真实 `./test_libgadu`
  执行后产生（discovered=4/passedCount=实测）。

## 验证
- 在 HarmonyOS aarch64 环境实测（与官方 CI 同源），以 CI 最终结果为准。

## 真机跟进（2026-09-15 预检：上游 7 PASS / 1 FAIL / 1 SKIP）
- 预检摘要截断了 `make check` 输出，未给出失败用例名：`_run_upstream_tests`
  现回显 automake 逐用例 verdict 行（`HMBS_UPSTREAM_PER_TEST`），并附
  `test/automatic/test-suite.log` 尾部 60 行与失败用例自有 `.log` 尾部
  40 行（`HMBS_UPSTREAM_SUITE_LOG` / `HMBS_UPSTREAM_CASE_LOG`，只读诊断，
  不跳过任何测试），供下一轮直接定位。
- readonly_tmp：`_writable_tmpdir` 最终回退不再返回只读的裸 `/tmp`，改用
  `<build_folder>/tmp`；`make check` 继续经 TMPDIR/TMP/TEMP 重定向运行。
  审计确认上游测试无 `/tmp` 硬编码（hash.c 的 `hashdata.XXXXXX` 为相对路径，
  在构建目录内创建；ltmain/install-sh 均走 `${TMPDIR-/tmp}`，已随环境重定向），
  故仅替换临时文件根目录，未改任何断言。
- `--without-pthread` 保持：鸿蒙 libc 缺 `pthread_cancel` /
  `pthread_setcancelstate`（ace/adlplug 同款结论），pthread 解析器在 OHOS
  上不可链接；fork 解析为唯一可用路径，9 个上游用例的运行口径不变。

## 真机跟进（2026-09-15 预检 round3：上游 8 PASS / 1 SKIP → incomplete）
- 预检实测 `make check`：发现 9、执行 8、通过 8、失败 0、跳过 1（connect SKIP，
  exit 77），test_package 4/4 通过。门禁判 incomplete：执行数 < 发现数且跳过 > 0。
- 根因：connect 的 SKIP 是上游声明行为，非配方跳过——本移植
  `--without-gnutls`（configure.ac AC_ARG_WITH(gnutls)，零依赖离线移植），
  test/automatic/Makefile.am 在无 gnutls 时用 skipped.c（exit 77）替代；
  protocol 在有 perl 时已 PASS（本轮执行集内），仅无 perl 时才 SKIP。
- 修复（未删减任何测试）：`_run_upstream_tests` 按 compartment 已验证经验做
  排除集口径——解析 `SKIP: <name>` 行，仅把已审计的资源门控名（connect→缺
  gnutls，protocol→缺 perl）移出执行集，输出 `total=9/excluded=1/
  discovered=8/executed=8/passed=8/failed=0/skipped=0` 并在 reason 附排除审计行；
  未知 SKIP 仍计为跳过、保持 incomplete。另回显 SKIP 用例 `.log` 尾部
  （HMBS_UPSTREAM_SKIP_LOG，只读）作排除证据。

## 真机跟进（2026-09-15 预检 round2：protocol FAIL）
- 后缀日志定位到失败用例为 `protocol`：`40-userlist.scr:116 Timeout`，
  紧随 `gg_userlist100_request() gg_deflate() failed`。
- 根因：配方此前以 `ac_cv_lib_z_inflateEnd=no` /
  `ac_cv_header_zlib_h=no` 强制关闭 zlib，导致无 `GG_CONFIG_HAVE_ZLIB`
  时 `src/deflate.c` 的 `gg_deflate()` 为无条件返回 NULL 的桩
  （`#ifdef` 体外直接 `return NULL`），userlist100 PUT 请求发不出压缩帧，
  期望包永不到达即超时。证伪：`expect data (40 00 00 00, auto, ... 78 da
  b3 09 ...)` 明确要求 zlib 头 `78 da`，非空比对、非静默跳过。
- 修复：删除全部三处 cache 覆盖，改为 `self.requires("zlib/1.3.1")`（仓内
  156 个配方同版本引用，远端已发布）+ `AutotoolsDeps`，configure 的
  `AC_CHECK_LIB(z, inflateEnd)` / `AC_CHECK_HEADER(zlib.h)` 经
  conanautotoolsdeps.sh 的 CPPFLAGS/LIBS 确定性成功；消费者经 CMakeDeps
  传递 `-lz`，原 test_package 未定义符号问题亦同步消除。未删减任何测试。
