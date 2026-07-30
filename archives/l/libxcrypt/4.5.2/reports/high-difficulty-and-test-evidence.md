# libxcrypt 4.5.2 高难适配与完整上游测试证明

## 1. 文档用途与原子边界

本文是 libxcrypt 4.5.2 适配 PR 的详细说明材料，同时可作为测试框架/工具链 Wiki 说明的正文来源。它只覆盖一个软件、一个 Issue 和一个 PR：

- 软件：libxcrypt 4.5.2
- Issue：#1279
- PR：#3018
- PR 类型：DOSBox Staging / NWChem 等主库的前置依赖项
- 软件配方路径：`archives/l/libxcrypt/4.5.2`
- 官方源码：`https://github.com/besser82/libxcrypt/releases/download/v4.5.2/libxcrypt-4.5.2.tar.xz`
- 官方源码 SHA-256：`71513a31c01a428bccd5367a32fd95f115d6dac50fb5b60c779d5c7942aec071`
- 上游 tag commit：`db70b42bd7b2a5b00a8580c8dec0aa66791c950a`

本文不合并其他软件的适配、Issue 或 PR，也不把 CI 状态当作本轮目标端验证证据。

## 2. 申请项总览

| 申请路径或材料 | 适用性 | 本 PR 的实际工作与证据 |
|---|---|---|
| 路径 A：基础适配 | 适用 | Conan 配方、Autotools 交叉构建、七份补丁、static/shared 包、消费者和产物边界验证 |
| 路径 B：新增可复用知识 | 适用 | 随 PR 提交 E232、E233 两组 `draft:true` 的 KV+MD 草稿，不修改正式索引 |
| 路径 C：高难适配 | 适用 | 使两个原本在目标端 SKIP 的上游入口真实执行，并保持生产库代码、ABI、符号和包边界不变 |
| 测试框架/工具链材料 | 适用 | 目标端双配置 runner、逐项 `.trs`/`.log` 收证、SHA-256 清单和独立结构化校验器 |
| 服务搭建 | 不适用 | libxcrypt 是本地 C 库，不启动 Tor、Apache、Tomcat 或其他常驻服务 |
| 远程取得官方资源并解决环境依赖 | 适用 | 固定官方 release URL 和摘要，处理目标端 Autotools、HMDFS、Libtool、签名 ELF 和系统 libc 差异 |

## 3. 基础适配工作

### 3.1 构建与打包

配方使用 Conan 2 的 `AutotoolsToolchain` 和 `AutotoolsDeps`。`shared` 选项分别映射为上游 static/shared 构建，构建后执行上游 `make -j1 check`，通过后才安装到 Conan package 目录。配方不下载非官方替代源码，不修改版本号，不引入额外第三方运行时依赖。

七份补丁各自职责如下：

| 补丁 | 触达范围 | 目的 |
|---|---|---|
| `0001-Makefile.am.patch` | 上游构建源文件 | 通过配置 shell 启动 helper，并给独立测试补齐准确的 fallback 对象 |
| `0002-Makefile.in.patch` | release 包生成文件 | 同步 `Makefile.am` 的必要改动，使 release tarball 不依赖现场 autoreconf |
| `0003-build-aux-m4-autogen-config.guess.patch` | 平台识别 | 识别 HarmonyOS/aarch64 并输出可被上游接受的目标三元组 |
| `0004-build-aux-m4-autogen-config.sub.patch` | 平台规范化 | 将缺失的 OHOS shorthand 规范化为上游已有形式 |
| `0005-configure.patch` | 配置临时目录 | 使 `config.status` 临时目录在目标文件系统上保持可写 |
| `0006-test-explicit-bzero.c.patch` | 仅测试源文件 | 给原上游死栈扫描补充 OHOS pthread 独立栈后端 |
| `0007-test-getrandom-fallbacks.c.patch` | 仅测试源文件 | 在目标 libc 提供高优先级接口时仍执行原上游 fallback 失败链 |

所有补丁均从官方 tarball 的 pristine/work 双轨通过仓库 `refresh-patch` 方法生成，并在 fresh 源码上按声明顺序无模糊应用。新增两份测试补丁的 SHA-256 为：

```text
432d4bc4365374aebd135c9b2b7e40966908f1d4421d8d0032e73665cbe1530c  0006-test-explicit-bzero.c.patch
b7daa9c66a7021f1b97d0426cb55cb583d833bebc407cdc1aa418ae374164d53  0007-test-getrandom-fallbacks.c.patch
```

### 3.2 生产包边界

测试适配不进入生产库源文件。正式目标端验证再次检查以下边界：

- static 包只包含 `libcrypt.a`，不包含 `libcrypt.so*`。
- shared 包包含 `libcrypt.so`、`libcrypt.so.2`、`libcrypt.so.2.0.0` 三个普通文件，内容摘要一致，不依赖目标文件系统软链接行为。
- shared 真库 SONAME 为 `libcrypt.so.2`。
- shared 真库 NEEDED 只包含 `libc.so`，没有 RUNPATH/RPATH。
- static 消费者不依赖 `libcrypt.so.2`。
- shared 消费者依赖 `libcrypt.so.2`，并由目标端实际运行通过。
- 消费者和共享库均为 AArch64 ELF，并保留目标签名段。
- 安装头文件、公共 API、导出符号和 Conan 依赖集合没有因两份测试补丁改变。

## 4. 高难工作一：执行 explicit-bzero 死栈语义测试

### 4.1 上游真实判定对象

`test/explicit-bzero.c` 不是普通的返回值单元测试。它在一块调用者可观察的独立栈上依次执行三项子测试：

1. `no clear`：函数返回后应仍能观察到测试模式，用于证明扫描方法本身有效。
2. `ordinary clear`：记录普通 `memset` 是否被编译器消除，只输出信息，不硬编码编译器结论。
3. `explicit clear`：函数返回后必须找不到测试模式，证明显式清零没有被删除。

上游默认用 ucontext 切换到调用者提供的栈。目标头文件虽存在 `ucontext.h`，但未提供该测试需要的完整函数集合，因此上游宏 `USE_SWAPCONTEXT` 未定义，入口直接以 77 结束。77 是 SKIP，不是 PASS。

### 4.2 适配设计

`0006` 只在 `__OHOS__ && !USE_SWAPCONTEXT && !XCRYPT_USE_ASAN` 条件下启用 pthread 栈后端：

- 使用调用者分配的 64 KiB 栈。
- 通过 `pthread_attr_setstack` 让测试线程在该栈上运行。
- 使用两个两方 barrier 分别表达主栈恢复和协程栈暂停方向。
- 主线程只在测试线程停在确定阶段时扫描目标栈。
- 上游的 `subtests`、模式准备、模式使用、计数和三类期望只保留一份。
- 最后一个子测试完成后才释放测试线程并销毁同步对象。
- 任一 pthread 调用失败都会使 Automake 记录非 PASS，不会把异常路径伪装为成功。

### 4.3 为什么不能用更简单的替代

- 只检查 `explicit_bzero` 符号存在，不能证明死存储清零未被优化掉。
- 扫描普通堆缓冲区，不能复现上游对函数返回后死栈内容的观察。
- 只查看汇编文本，不能替代目标优化级别和目标运行时下的行为验证。
- 直接把入口标为 unsupported 或继续返回 77，不能计为通过。
- 修改生产库函数以配合测试会污染被测对象，违反测试边界。

### 4.4 结果

static 和 shared 两个 fresh 配置都实际执行该入口。原始日志包含三项 prepare/test 观测，其中显式清零最终为 0，`.trs` 的唯一 `test-result` 和 `global-test-result` 均为 PASS。

## 5. 高难工作二：执行 getrandom fallback 全失败链

### 5.1 上游真实判定对象

`test/getrandom-fallbacks.c` 用链接包装和故障注入验证上游随机字节实现的 fallback 次序、缓冲区写入和最终失败。目标 libc 提供 `arc4random_buf`，因此 `HAVE_ARC4RANDOM_BUF` 为真；上游测试在预处理阶段直接返回 77，整个 fallback 实现和故障链均未执行。

### 5.2 适配设计

`0007` 只在 OHOS 测试翻译单元中执行以下操作：

1. 取消当前测试单元里的 `HAVE_ARC4RANDOM_BUF` 选择。
2. 将被测内部入口改名为测试专用名称，避免与生产对象重复定义。
3. 直接包含上游同一份 `lib/util-get-random-bytes.c` 实现，不复制或改写算法。
4. 保留原测试已有的系统入口包装、错误注入、子路径切换、缓冲区断言和最终失败断言。
5. 非 OHOS 构建继续走上游原预处理分支。

### 5.3 为什么不能用更简单的替代

- 目标 libc 的高优先级接口存在，不代表 libxcrypt 的 fallback 实现正确。
- 只运行成功路径不能覆盖 `getentropy`、`getrandom`、直接系统调用和 `/dev/urandom` 的失败切换。
- 复制一份简化实现会测试副本而不是上游生产实现。
- 仅修改期望状态或把 77 解释为成功会造成测试统计失真。

### 5.4 结果

static 和 shared 两个 fresh 配置都实际执行该入口。原始日志包含目标端启用的 fallback 子路径和最终失败链，所有已有断言通过；`.trs` 的两个唯一终态均为 PASS。

## 6. 上游测试集合与计数原则

### 6.1 唯一入口

上游在本目标配置下共有 54 个唯一 Automake 入口：

```text
alg-des
alg-gost3411-2012-hmac
alg-gost3411-2012
alg-hmac-sha1
alg-md4
alg-md5
alg-pbkdf-hmac-sha256
alg-sha1
alg-sha256
alg-sha512
alg-sm3-hmac
alg-sm3
alg-yescrypt
badsalt
badsetting
byteorder
checksalt
compile-strong-alias
crypt-badargs
crypt-gost-yescrypt
crypt-nested-call
crypt-sm3-yescrypt
crypt-too-long-phrase
explicit-bzero
gensalt-bcrypt_x
gensalt-extradata
gensalt-nested-call
gensalt-nthash
gensalt
getrandom-fallbacks
getrandom-interface
ka-bcrypt-a
ka-bcrypt-x
ka-bcrypt-y
ka-bcrypt
ka-bigcrypt
ka-bsdicrypt
ka-descrypt
ka-gost-yescrypt
ka-md5crypt
ka-nt
ka-scrypt
ka-sha1crypt
ka-sha256crypt
ka-sha512crypt
ka-sm3-yescrypt
ka-sm3crypt
ka-sunmd5
ka-yescrypt
preferred-method
short-outbuf
special-char-salt
symbols-renames
symbols-static
```

`symbols-renames` 和 `symbols-static` 是上游声明的 static-only 入口，因此：

- static 选择 54 个入口。
- shared 选择其余 52 个入口。
- 唯一上游入口总数仍是 54，不能把 54 和 52 相加成 106。
- 同一入口内的断言、循环输入、shared/static 重复执行和消费者重复配置都不拆成新测试入口。

### 6.2 接受条件

每个入口只有同时满足以下条件才计为通过：

- 有且只有一个同名 `.trs`。
- `.trs` 中有且只有一个 `test-result`，值为 PASS。
- `.trs` 中有且只有一个 `global-test-result`，值为 PASS。
- 有同名原始 `.log`。
- `test-suite.log` 的 TOTAL/PASS 与选择集合完全一致。
- SKIP、XFAIL、FAIL、XPASS、ERROR 全部为 0。
- 没有缺失、重复、额外或未知终态。

## 7. 测试框架/工具链说明材料

### 7.1 目标端 runner

正式 runner 为 static/shared 建立隔离的 Conan home、源码目录、构建目录、临时目录和证据目录。每个配置执行一次 fresh `conan create --build='libxcrypt/*'`，且每次有独立 1800 秒外层超时。runner 不复用旧构建树，不从静态预测生成结果分桶。

runner 在构建后自动完成：

1. 收集唯一 `test-suite.log`。
2. 按集合逐项复制 `.trs` 与同名 `.log`。
3. 校验每项两个唯一终态。
4. 校验七个汇总状态。
5. 校验新增两个入口的关键原始日志。
6. 运行 Conan 消费者入口。
7. 校验 AArch64、签名段、static/shared 包边界和动态依赖。
8. 生成逐文件 SHA-256 和二级汇总 SHA-256。
9. 只有全部步骤完成才原子写入 `COMPLETE`。

### 7.2 独立校验器

`validate_full_upstream.py` 不信任 runner 的汇总文本，而是重新读取回传文件：

- 从 `test_package/MANIFEST.yml` 读取 54 个唯一入口。
- 用 static-only 列表推导 shared 的 52 个入口，不硬编码静态预测结果分桶。
- 检查集合差、重复名、缺日志、重复终态和未知终态。
- 重新解析两个 `test-suite.log` 的全部七个计数。
- 为每个 `.trs`、`.log` 和 suite 日志计算 SHA-256。
- 输出结构化 JSON，供 W4 和 PR 描述复核。

### 7.3 测试工具材料结论

这套材料不是把断言拆分计分，而是建立可复用的完整入口验证方法：目标端 fresh 执行、原始终态收集、集合一致性验证、产物边界验证、双层摘要和独立解析。本文可直接作为 Wiki 说明的基础材料；实际计分由赛事规则和审核结果决定。

## 8. 正式目标端结果

目标：HarmonyOS 6.0 / aarch64，Clang 15，Conan 2.29.1 OHOS 适配版。

| 配置 | 上游选择 | PASS | SKIP | XFAIL | FAIL | XPASS | ERROR | 消费者 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `shared=False` | 54 | 54 | 0 | 0 | 0 | 0 | 0 | 同一消费者入口通过 |
| `shared=True` | 52 | 52 | 0 | 0 | 0 | 0 | 0 | 同一消费者入口通过 |

唯一上游入口结论：`54/54 PASS`。shared 的重复执行不增加唯一入口数。

目标端最终摘要：

```text
LIBXCRYPT_STATIC_EXIT=0
LIBXCRYPT_SHARED_EXIT=0
LIBXCRYPT_UNIQUE_UPSTREAM=54/54
LIBXCRYPT_STATIC_UPSTREAM=54/54
LIBXCRYPT_SHARED_UPSTREAM=52/52
LIBXCRYPT_CONSUMER_CONFIGURATIONS=2/2
LIBXCRYPT_W3_RESULT=PASS
```

回传后的独立校验结论：

```text
RAW_HASH_LINES=238
RAW_HASH_FAILURES=0
SUMMARY_HASH_LINES=10
SUMMARY_HASH_FAILURES=0
VALIDATION_PASS: unique=54/54 static=54/54 shared=52/52 unexpected=0
```

关键摘要：

```text
14580505eee37637d503537be1820c41d6c33707986a3091ccf5c09e041954dc  evidence-return-r4.tar.gz
a683f6bf0e88af4fc30cff27c3dd774a4a8ae4624a3894e2406bb66f8e06e069  validation-result.json
```

正式 r1-r3 都没有形成 static/shared 完整闭环，因此不计入通过结果。r4 修复的只是证据脚本变量名冲突；配方、源码补丁、官方测试集合和构建输入与已验证候选保持一致。

## 9. 官方资源取得与环境依赖

### 9.1 官方资源

- 只使用官方 release URL。
- 下载后必须匹配固定 SHA-256。
- 补丁 replay 再次从该官方归档解压，按 `conandata.yml` 顺序应用七份补丁。
- replay 后两个测试源文件摘要由 runner 固定校验，防止传输或补丁顺序漂移。

### 9.2 解决的环境依赖

- 使用目标端已有 Clang、LLVM readelf/ar、Python 和 Conan。
- 处理 Autotools 对目标平台三元组的识别。
- 处理目标文件系统上的 configure 临时目录与 Libtool wrapper 启动。
- 处理目标 libc 缺少 `explicit_bzero` 导出时独立测试的准确 fallback 对象链接。
- 处理目标端 ucontext 函数不可用与 `arc4random_buf` 已存在导致的两个测试 SKIP。
- 对生成的目标 ELF 只做正常构建与既有签名流程，不修改系统文件或登录账户。

普通下载本身不单独夸大为高难工作；可申请材料是固定官方来源、环境依赖闭环和目标端完整验证的组合。最终得分以赛事审核为准。

## 10. 服务搭建项说明

libxcrypt 提供本地密码哈希 API，不提供网络守护进程或 Web 服务。本 PR 未搭建 Tor、Apache、Tomcat 或其他服务，也不创建监听端口。因此服务搭建项明确标记为不适用，不申请虚构分值。

## 11. 可复用知识草稿

本 PR 只在 `knowledge/drafts/` 提交配套 KV+MD，且都标记 `draft:true`：

- E232：在目标文件系统上启动 Libtool 测试包装器时，只对存在匹配 `.libs` ELF 的 wrapper 走 shell，真实 ELF 仍直接执行。
- E233：目标 libc 缺少 API 时，库内 hidden fallback 不会自动满足独立测试目标；应给准确测试目标链接准确 fallback 对象，不能跳过测试。

本 PR 不写正式 graph、doc、index 或 SUMMARY；草稿是否提升由主编审核决定。

## 12. 复核清单

- [x] 官方 URL 与 SHA-256 固定。
- [x] 七份补丁从 pristine/work 生成并完成 fresh replay。
- [x] 两份新增补丁只改测试源文件。
- [x] static fresh 54/54 PASS，零 SKIP，零意外终态。
- [x] shared fresh 52/52 PASS，零 SKIP，零意外终态。
- [x] 唯一上游入口为 54，不重复累计配置。
- [x] `explicit-bzero` 三类原上游观察真实执行。
- [x] `getrandom-fallbacks` 原上游 fallback 失败链真实执行。
- [x] static/shared 消费者入口均运行通过。
- [x] 生产包、SONAME、NEEDED、RPATH 和 AArch64/签名边界复核通过。
- [x] 238 个原始证据文件摘要复核通过。
- [x] 10 个汇总文件摘要复核通过。
- [x] 独立校验器得到 `unexpected=0`。
- [x] PR 正文测试类型细分、零值原因和总数一致性检查通过。

独立 W4 不在本实现文档中自我认证；它由未参与实现的任务对冻结候选执行，要求 P0/P1=0，结果作为提交和更新 PR 的外部门禁保存。
