# notes — lib1305 0-20250415 OHOS aarch64 适配

本文记录适配过程的关键决策与证据，供后续审计与复用。

## 1. 上游核验（官方事实，非第三方）

| 项 | 值 |
|---|---|
| 官方主页 | https://lib1305.cr.yp.to |
| 版本 | 20250415（tarball 内 `version` 文件硬编码） |
| tarball URL | https://lib1305.cr.yp.to/lib1305-20250415.tar.gz |
| SHA256 | ac20c0a49898db23e237ac208f876cab83dcfc952d690ec96d8038bb22204c5e（从官网下载实测） |
| License | Public domain；官网 SPDX：`LicenseRef-PD-hp OR CC0-1.0 OR 0BSD OR MIT-0 OR MIT`，配方取 `CC0-1.0` |
| 构建系统 | `./configure`（python3 脚本）+ `scripts-build/` + `Makefile`，与 libcpucycles 同源的 djb 构建体系 |
| 公开 API（官网 api.html） | `#include <lib1305.h>`，`poly1305(a,m,mlen,k)` / `poly1305_verify(a,m,mlen,k)`，链接 `-l1305` |
| 生成头实际符号 | `lib1305_onetimeauth[_poly1305]` / `lib1305_onetimeauth_verify` / `lib1305_onetimeauth_BYTES(16)` / `lib1305_onetimeauth_KEYBYTES(32)`（由 configure 按 `api` 文件生成，test.c 用短别名并与规范名交叉核对） |

配方版本号 `0-20250415` 采用任务指定的版本串；对应上游发布即 20250415。

## 2. 上游测试调查

| 搜索位置 | 结果 |
|---|---|
| test/ tests/ 目录 | 不存在 |
| `make check` / `ctest` / `meson test` 目标 | 不存在 |
| 官方测试入口（test.html） | `lib1305-test`（常规测试）+ `lib1305-fulltest`（编排脚本） |
| `lib1305-test` | SUPERCOP 风格：verify_16 与 onetimeauth_poly1305 在全部选中实现 x 输入偏移下运行已知答案 + 校验和 + canary 防越界检查；成功打印 `all tests succeeded`，退出 0，失败退出 100 |
| `lib1305-fulltest` | 对每个（操作/原语/实现/偏移）并行调用 lib1305-test；偶数偏移任务追加 `valgrind` 数据流（TIMECOP）运行 |
| CI 配置 | 不存在 |

结论：常规测试由配方 `build()` 真实运行 `build/arm64/package/bin/lib1305-test` 覆盖；
`fulltest` 的数据流一半硬依赖 `valgrind`（见 §5），在 OHOS 上按缺失工具链处理。

## 3. 依赖分析（W0）

| 依赖 | 状态 | 处理 |
|---|---|---|
| `libcpucycles`（仅 `lib1305-speed` 基准工具 `#include <cpucycles.h>`） | 已合入 `archives/l/libcpucycles/20260625`（manifest 状态 published） | `tool_requires("libcpucycles/20260625")`：纯构建期，产出的 lib/include 不引用、不打包、不传递给消费者 |
| `librandombytes`（共享库链接行 `-lrandombytes` + `lib1305-test`/`lib1305-speed` 链接） | 仓库无收录 | 配方自带 `vendor-randombytes/` 构建期 shim（见 §4）；库本体零引用，消费者无新增依赖 |

`tool_requires` 与 shim 的头文件/库路径均经 `compilers/default` 首行 `-I/-L`
注入（configure 不读环境变量，见 §6），无需任何上游 patch。

## 4. randombytes shim 说明（/vendor-randombytes）

- 内容：`randombytes.h`（`void randombytes(void *,long long)`，与上游
  `randombytes_internal_void_voidstar_longlong` 一致）+ `randombytes.c`
 （`/dev/urandom` 惰性常驻 fd，EINTR 内循环，硬失败直接 abort，绝不返回弱随机数）。
- 性质：新文件，非 patch；CC0-1.0，与上游 librandombytes 同为公共领域。
- 迁移路径：librandombytes 一旦合入并发布，删除本目录并改用
  `self.requires("librandombytes/<ver>")`，去掉 `-I/-L` 注入。
- 审计证据：库本体零引用可用 `nm -D package/lib/lib1305.so.1 | grep randombytes`
  为空验证；共享库仅静态嵌入 shim 符号，无新增 DT_NEEDED。

## 5. lib1305-fulltest / valgrind 处理

`scripts-build/fulltest-convert` 对每个偶数偏移任务追加 `(True,)` 数据流任务，
`fulltest-top` 将其翻译为 `env valgrind_multiplier=1 valgrind -q
--error-exitcode=99 lib1305-test ...`。OHOS 无 valgrind 时该子进程以 127
失败，fulltest 整体判负——这是缺失工具链，不是库缺陷。

- 低成本补齐评估：valgrind 在 OHOS musl aarch64 上无可用移植，补齐成本
  远超基准库适配本身，放弃。
- 常规测试部分与 fulltest 的常规一半完全等价（同一批
  `lib1305-test <o> <p> . <n> <offset>` 调用），已在 `build()` 全量运行，
  无用例丢失；数据流一半在 PR 补充说明中如实声明未运行。
- 构建开关：上游 `configure` 默认 `valgrind = True`（`configure:21`），会把
  `include-build-valgrind/crypto_declassify.h`（`#include <valgrind/memcheck.h>`）
  装入构建树，在 OHOS 上直接导致 `lib1305-test` 编译失败
  （`fatal error: 'valgrind/memcheck.h' file not found`）。配方显式传递
  `--no-valgrind`，选用 `include-build/`（`crypto_declassify` 为空操作，
  `crypto_declassify_uses_valgrind 0`）；常规测试不受影响，仅 TIMECOP
  数据流测试按上游文档预期报 `declassify 0`（false positives 预期内）。

## 6. 构建期关键机制（与 libcpucycles 互证）

1. **工具链注入点唯一**：configure 源码无任何 `getenv`，`CC/CFLAGS/AR/RANLIB`
   环境变量全部无效；编译器唯一来源是源码树 `compilers/default`（逐行
   `--version` 探测，首个成功者的整行写入各构建脚本）。配方把 profile 的
   OHOS clang 按同格式前置，原候选行保留作 fallback。
2. **arch 自动探测**：`platform.machine()` 得 `aarch64` → 归一化 `arm64`，
   构建树为 `build/arm64`；amd64-only 实现（含 BMI2 变体）按其
   `architectures` 文件自动跳过，arm64 上选中 portable `ref` 实现。
3. **测试运行方式（本轮改用静态重链）**：上游测试二进制链接相对
   DT_NEEDED `lib/lib1305.so`（SONAME `lib1305.so.1`）。LD_PRELOAD 路线已证伪：
   `--no-tryifunc` 后预加载文件自身加载干净（重定位错误消失），但二进制仍报
   裸 `Error loading shared library lib1305.so.1`——预加载对象不满足 SONAME
   查找，且 OHOS 忽略 `LD_LIBRARY_PATH`，搜索路径层面无解。本轮改用不同路线：
   取同一批上游测试对象（`command/lib1305-test*.o`）对本次构建的
   `package/lib/lib1305.a`（与共享库同源 ofiles，见 `scripts-build/staticlib`）
   做构建树内静态重链（`lib1305-test-static`，写构建树可写区、避开只读 /tmp），
   运行之。零测试源码/断言改动；共享产物动态覆盖由 test_package 消费者测试承担。
4. **禁用 IFUNC（本轮新增）**：`scripts-build/dispatch` 在 `tryifunc=1` 且编译器
   能产出 `STT_GNU_IFUNC` 符号时，把三个公开 API 做成
   `__attribute__((ifunc(...)))`（见 `dispatch/ifunc-test.c` 仅用 readelf 查
   `IFUNC.*xyzzy_wrapper` 即判支持，不验证 loader 能否解析）。OHOS
   loader 无法解析该重定位，故缺符号集合恰为该三符号、且连自身预加载
   也报找不到。配方显式传递 `--no-tryifunc`，选用可移植的
   constructor-pointer 回退（`dispatch/ifunc` 置 0），符号变为普通定义。
5. **跳过上游 install**：`scripts-build/install` 在目标 `lib/`（setgid）内
   建 umask 077 临时目录，OHOS hmfs 下复现 libcpucycles 同款
   PermissionError；改从 `build/arm64/package/` 直接收集（install 无编译
   动作，纯 copy+rename，语义等价）。

## 7. 产物与验证（待真机预检回填实测数字）

- 产物：`include/lib1305.h` + `lib/lib1305.a`（默认）或
  `lib/lib1305.so.1` + `lib/lib1305.so`（`shared=True`）；`bin/` 工具不打包。
- `build()` 内运行上游 `lib1305-test`，期望尾行 `all tests succeeded` 且退出 0。
- `test_package` 消费者测试 8 断言：version / arch / 实现非空 /
  RFC 8439 2.5.2 KAT / 别名一致 / 正确验证 / 篡改否决 / roundtrip。
- 真机 `conan create` 日志即 PR 正文「上游测试用例通过率」的唯一依据；
  本轮仅完成工作树，具体数字待预检 evidence 轮摘录。

## 9. 本轮诊断（2026-09-15：test_package 6/8）

- 现象：上游 `lib1305-test-static` 全过（2/2），消费者测试 6/8；
  失败为 RFC 外部向量相关的 `rfc8439-kat` 与 `verify-ok`（`roundtrip`
  自洽通过、`verify-tampered` 正确否决，证明库内 auth/verify 自洽、
  分发与链接正常）。
- 上轮仅在 `test_package/test.c` 增加诊断输出（`msg-len`、
  `computed-tag`/`expected-tag` 十六进制、各 `verify` 调用的 `rc`），
  断言逻辑未动。

## 10. 根因与修复（2026-09-15：向量勘误）

- 根因：`test.c` 写死的所谓“RFC 8439 2.5.2”三元组（key
  `85d6be45…ec55` + `Cryptographic Forum Research Group` + tag
  `a8061dc1…2c01260a`）与权威 RFC 文本不一致。RFC 8439 §2.5.2 实际
  key 为 `85d6be78…41f51b`、tag 为 `a8061dc1…0c0127a9`（与测试值在
  key/tag 尾部均不同）；测试向量系混用来源、无法与正确实现一致。
  这解释了全部现象：库自洽（roundtrip 过）、上游自测过，唯独外部
  KAT 与依赖它的 `verify-ok` 失败。
- 修复：KAT 改用 RFC 8439 附录 A.3 Test Vector #4，按 RFC 十六进制
  dump 逐字节转录——key `1c9240a5…207075c0`（32 字节）、消息为
  `'Twas brillig…outgrabe.`（127 字节，含 3 个 `0x0a` 换行、无尾换
  行，`msg-len` 打印 127 可复核）、tag `4541669a…c5eb62`。断言仍为
  8 个、逻辑不变（`discovered=8` 不变）；篡改检测与 roundtrip 桩检
  测能力不受影响。

## 8. 风险与后续

- 若预检显示 `libcpucycles/20260625` 在制品仓不可用（PF4/W0），备选方案：
  基准工具改用配方内 `clock_gettime` stub 构建（`lib1305-speed` 非测试、
  非交付物），去掉 `tool_requires`。当前首选真实依赖，不预置 stub。
- `lib1305-speed` 需要真实 TSC 才能输出有意义数字，OHOS 上仅保证可构建；
  不作为通过率依据。

## 11. AI Review 189684326 处置（2026-09-15：向量误用指控不成立）

- 指控：`test.c` 把 RFC 8439 附录 A.3 Test Vector #4（AEAD 标签）误作原始
  Poly1305 期望值，断言 #4/#6 必然失败。
- 核验（RFC 原文）：附录 A.3 标题即 "Poly1305 Message Authentication Code"，
  其 Vector #4 字段为 "One-time Poly1305 Key" / "Text to MAC" / "Tag"，
  key `1c9240a5…207075c0`、消息 `'Twas brillig…`（127 字节）、
  tag `4541669a…c5eb62`——与 `test.c` 逐字节一致，确为原始 Poly1305 向量。
  AEAD 向量在 §2.8.2 / 附录 A.5（同 ChaCha 密钥派生出的一次性密钥为
  `bdf04aa9…`，标签为 `eead9d67…`，输入为 AAD + 密文），与本向量无关；
  附录 A.4 #3 亦证实同密钥派生结果为 `965e3bc6…` 而非密钥本身，
  说明 A.3 #4 的密钥是直接输入、无派生——与
  `lib1305_onetimeauth_poly1305(a,m,mlen,k)` 的接口语义一致。
- 证据：RFC 原文转录一致 + HMBS 真机预检 passed（任一断言失败 test 二进制
  即以非零退出，passed 即 8/8 全过，rfc8439-kat 与 verify-ok 均通过）。
- 结论：false_positive，断言逻辑零改动，仅在 `test.c` 头注释补一行
  A.3/A.5 区分说明，防后人重蹈。

## 12. 策略切换（2026-09-15：KAT 由 A.3 #4 改为 §2.5.2，终结重复指控）

- 背景：KAT 选型指控第三次出现（commentId 189684570 重复）。
  前两轮以 false_positive + 注释澄清应对，RFC 原文与两次 passed 预检
  均证实 A.3 #4（key `1c9240a5…` + 127 字节长诗 + tag `4541669a…`）有效，
  但注释策略未能闭环审查。
- 本轮换策略：不再争论 A.3 #4，改用审查方自己背书、歧义最少的
  RFC 8439 §2.5.2 单块向量——key `85d6be78…4149f51b`（32 字节）+
  "Cryptographic Forum Research Group"（34 字节）→
  tag `a8061dc1…0c0127a9`。A.3 #4 的有效性不受影响（仍在 §10/§11 留档），
  切换仅为消除“A.3 #4 密钥字节复用于 A.2/A.4/A.5、易被误读为 AEAD”
  的结构性歧义。
- 取证（三源一致）：RFC 8439 §2.5.2 原文三元组 +
  IETF draft-rfc7539bis §2.5.2 摘录（key material 逐字节一致）+
  独立 Rust 实现按 RFC 逐步复算（含中间 Acc 值）得到同一 tag。
- 改动面：`test.c` 的 key/msg/expected 三数组 + 头注释 + 两处文案；
  断言仍 8 个、名称不变（`discovered=8` 不变），`conanfile.py` 零改动；
  `msg-len` 打印改为 34，篡改检测与 roundtrip 逻辑不受影响。
