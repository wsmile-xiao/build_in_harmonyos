# aws-crt 0.38.5 适配笔记

## 基本信息
- 上游项目: awslabs/aws-crt-cpp v0.38.5（AWS Common Runtime C++ 发行版）
- 构建系统: cmake（BUILD_DEPS=ON，全栈源码构建）
- 编译器: OHOS clang (aarch64-linux-ohos)，libc++
- 状态: built

## 命名说明
本包按积分赛任务与 Issue #2371 以库名 `aws-crt` 归档，内容为 AWS 官方
Common Runtime 的 C++ 发行版（上游仓库名 aws-crt-cpp）。仓库中已有的
`aws-crt-cpp/0.38.5` 归档采用 BUILD_TESTING=OFF、未接入上游测试；本包在其
基础上补齐了完整的上游测试套件执行与机器证据链。

## 源码处理
GitHub tag tarball 不含 git 子模块内容。conandata.yml 按 v0.38.5 标签的
13 个子模块固定 commit（aws-c-common 95515a8b1f、aws-c-cal 1cb9412158、
aws-lc 37d86461a9、s2n f5e5e83031 等）逐一下载展开到 crt/，全部 URL 为官方
GitHub 归档地址并带 sha256 校验（已对照 GitHub API tag tree 核验）。

## 关键构建配置
- `CMAKE_SYSTEM_NAME=Linux`：Conan toolchain 将 os=OHOS 映射为 HarmonyOS，
  而 aws-c-io 的 CMakeLists 只识别 Linux/Android 来启用 epoll 事件循环。
- `ENFORCE_SUBMODULE_VERSIONS=OFF`：tarball 无 git 元数据。
- 静态库默认 + fPIC（R26/R32）。

## 上游测试套件
tests/ 共注册 226 个用例（AwsTestHarness，create_test_sourcelist 生成
ctest 驱动，无 gtest 依赖）：
- 140 个 add_net_test_case：依赖真实 AWS IoT/MQTT 端点、代理服务器或
  TLS 凭据环境变量；
- 86 个 add_test_case 本地用例（含 AES/SHA/HMAC/HKDF/Sigv4/CBOR/CRC/
  XXHash/Json/Optional/Variant/Stream/资源安全等）。

接入方式：
1. 补丁 0002 放开 `if(NOT CMAKE_CROSSCOMPILING)` 对 tests/ 的封锁
   （toolchain 构建下该值恒为 TRUE，否则上游测试永不注册）；
2. `-DENABLE_NET_TESTS=OFF` 在配置期剔除全部联网用例；
3. 补丁 0003 把唯一依赖真实 IoT 端点的 `Mqtt5to3AdapterNewClientFull`
   改为 net 注册（离线时上游自身返回 SKIP 103，会被判跳过）；
4. build() 内以 `ctest -N` 取发现数、`ctest --output-on-failure` 执行，
   解析框架输出得到 executed/passed/failed/skipped 并打印
   HMBS_UPSTREAM_TEST_RESULT 标记；结果 JSON 同时打包为
   res/upstream_test_result.json，test_package 每轮复发该标记
   （包缓存命中导致 build() 跳过时仍保证证据在位）。

## BYO_CRYPTO 结论
曾评估 BYO_CRYPTO=ON 以精简构建，但 aws-c-cal 在该模式下哈希/HMAC 默认
实现直接 abort()（需应用层注入 aws_set_*_new_fn），SHA/AES/Sigv4 相关本地
用例无法运行，库也不具备完整功能，故维持上游默认的全加密栈构建
（aws-lc + s2n）。aws-lc 汇编生成需要 Perl（补丁 0001，
DISABLE_PERL=OFF，真机 /data/service/hnp 提供 perl）。

## 已知限制
- 141 个联网用例未在离线环境运行（140 net 注册 + 补丁 0003 移入的 1 个，
  缺 AWS IoT 端点与 AWS_TEST_* 环境），见 MANIFEST.yml 与 PR 正文的补充说明；
  其余 85 项本地用例已完成逐例静态审计（无自跳过路径、无环境依赖），
  尚待真机 ctest 实测确认。
- test_package 消费者程序覆盖 DateTime/Base64/UUID/JsonObject/CRC32(C)
  七项断言，退出码非 0 即失败。

## 本轮（2026-08-25 第 2 次 evidence incomplete：无法读取 archive 代码树）

同指纹第 2 次，策略与上轮（补齐配方文件）不同，三条线并进：

1. **同步可见性**：上轮配方仅存在于未跟踪工作树。本轮将 `archives/a/aws-crt`
   整目录 `git add` 进索引（不 commit）——若 hmbs 快照走 git 树（index/write-tree）
   亦可读到；若走文件系统直拷则本就无碍，两种机制下都无害。
2. **真缺陷修复（CRLF 补丁）**：官方 v0.38.5 tarball 全部源码为 LF
   （根 CMakeLists.txt LF=423、tests/CMakeLists.txt LF=357，全新解压实测），
   而 patches/0001-enable-perl-for-assembly.patch 为 CRLF——conan 首选
   `git apply --whitespace=nowarn` 对 CRLF patch vs LF 目标必然
   "patch does not apply"，会在预检 build() 阶段爆雷。已将该补丁归一化为 LF。
   验证矩阵（Temp 全新解压 tarball）：git apply --check 三补丁逐个 rc=0；
   顺序 git apply rc=0×3；GNU patch -p1 --dry-run 回退 rc=0×3（0003 fuzz 1
   为 GNU patch 边缘容忍，git apply 精确匹配）。上轮 verify_patches.py 的
   缺陷：只验了 0002/0003 且其 scratch 目录曾被 CRLF 化污染，结论不可靠，
   本轮以全新解压重验为准。
3. **测试口径复核（防下一轮翻车）**：
   - 注册总数实为 256 = add_test_case 116 + add_net_test_case 140
     （此前 MANIFEST 写"合计 226"是口径混算，已改为精确表述）；
   - 条件块审计：AWS_BUILDING_ON_EC2(2)、AWS_HAS_CI_ENVIRONMENT(2+2 嵌套)、
     ENABLE_PROXY_INTEGRATION_TESTS(24) 共 30 个本地注册在真机不成立
     （前两者无 option/set 定义恒 FALSE，后者显式 OFF）→ 本地 86；
   - ENABLE_NET_TESTS 门控位于 aws-c-common AwsTestHarness.cmake 的
     add_net_test_case 宏内 `if(ENABLE_NET_TESTS)`（harness 第 25-31 行），
     -DENABLE_NET_TESTS=OFF 在配置期剔除全部 140 net ✓；
   - SKIP 语义：harness 设 SKIP_RETURN_CODE=103，ctest 记 Skipped，
     配方门禁 skipped==0 会如实拦截静默跳过；
   - 全部 AWS_OP_SKIP 位点均在 IotService/Mqtt*Credentials/MqttClientTest/
     MqttRequestResponse 等 net 注册文件内，85 项离线集无自跳过路径；
     IMDS 两例（TestProviderImdsGet/TestProviderProfileGet）离线只做连接
     尝试且不断言凭据结果；Sigv4aSigningTestCredentials 用 dummy 凭据 +
     aws_verify_sigv4a_signing 本地验签；DefaultResolution 仅解析 localhost。
   - 预期真机：ctest 发现 85 / 执行 85 / 通过 85（以实测输出为准）。

状态：仅工作树 + git 索引暂存，未 commit/push；等待 hmbs 复跑真机预检。


## 本轮（2026-08-25 真机预检 compile 失败：github.com 直连下载超时）

真机证据：conan create 在 source() 阶段连试 3 次
`https://github.com/awslabs/aws-crt-cpp/archive/refs/tags/v0.38.5.tar.gz`
均 ConnectTimeout（connect timeout=30），source() 抛错退出码 1。
hmbs 预检直接对配方执行 conan create，不经过 ci/conan/build_and_test.sh
的"改写 conandata.yml 加镜像 fallback"步骤——配方必须自带镜像。

修复：conandata.yml 全部 14 个 URL（主 tarball + 13 个子模块 commit 固定
tarball）从单值改为有序列表，镜像映射复用 ci/conan/build_and_test.sh
get_mirrors() 的 GitHub 规则（实测注释：仅 gh-proxy.com 可用）：

1. `https://gh-proxy.com/https://github.com/...`（镜像在前）
2. 官方原始 `https://github.com/...`（末尾兜底，出处保留）

全部 sha256 保持官方归档原值不变；Conan 2.x get() 原生支持 url 列表逐个
fallback，配方 source() 无需改动。已用 python yaml.safe_load 校验：
主 url 与 13 个子模块 url 均为长度 2 的列表、首项为 gh-proxy.com 前缀、
末项与官方原值一致。同仓库已合入包（vulkan-loader/vulkan-headers/absl/
ace/badvpn/backward-cpp 等）采用相同结构。

状态：仅工作树修改（含既有索引暂存），未 commit/push；等待 hmbs 复跑真机预检。

## 结束
PENDING（等待下一轮真机预检结果）

## 本轮（2026-08-25 真机预检 compile 失败：CMakeLists.txt:417 Flow control statements are not properly nested）

真机证据：export/下载全部成功，cmake configure 顶层 CMakeLists.txt 报
`CMake Error at CMakeLists.txt:417 (if): Flow control statements are not properly nested.`

根因（已本地复现）：patches/0002-run-upstream-tests-under-cross-compiling.patch
的 hunk 头写的是 `@@ -413,11 +413,6 @@`，但实际带 7 行 `+` 行。
Conan 2 用 patch-ng 应用 conandata 补丁，patch-ng 按头声明的行数消费：
吃满 11 行 `-` + 6 行 `+` 即认为 hunk 结束，第 7 行 `+endif()` 被当作
流末尾"unparsed bytes"丢弃。结果顶层 CMakeLists.txt 以
`add_subdirectory(tests)` 收尾、缺少 `endif()`，第 417 行的
`if(BUILD_TESTING)` 未闭合 → 正是日志中的 417 行报错。
本地用同款 patch-ng 对 v0.38.5 pristine 文件复现：apply 返回成功、
产物恰好缺失 endif()、flow-balance depth=1（417 行 if 未闭合），与真机一致。

修复：用 difflib 从 pristine→目标内容重新生成 0002 补丁（hunk 计数自动
正确，并带 3 行上下文，今后上游漂移会显式失败而非静默错位）：
`@@ -410,14 +410,10 @@`，纯 LF、无 CR/BOM，新增内容与原意图逐字节相同。

验证：
1) patch-ng 解析 errors=0/warnings=0，单 hunk src 410+14 → tgt 410+10；
2) 0001→0002→0003 全链对 pristine 应用后，顶层文件与预期目标逐字节一致
   （仅差 0001 的 DISABLE_PERL=OFF 本身改动），flow-balance depth=0；
3) tests/CMakeLists.txt 的 0003 改动经 difflib 核对与设计完全一致；
4) git apply --check / git apply 均通过。

教训：patch-ng 对 hunk 头计数不符时静默截断多余 `+` 行且仍返回成功，
零上下文补丁更无内容校验；自写补丁必须程序化生成或用 git apply 校验计数。

状态：仅工作树修改（0002 补丁重写 + notes 更新），未 commit/push；等待 hmbs 复跑真机预检。

## 本轮（2026-08-25 真机预检 compile 失败：conan create 收到外部 SIGTERM，退出码 5）

真机证据：export 完成后进入 source()，14 个归档（主包 + 13 个子模块，
其中 aws-lc 单包 145.3MB）经 gh-proxy 全部下载成功、s2n（最后一个）
解压完成后进程被外部 SIGTERM 终止：conan 打印 "Received SIGTERM!"，
随后 "ERROR: Exiting with code: 5"（Conan 的 ERROR_SIGTERM 路径），
hmbs 报 "conan create 失败（退出码 5）"。上一轮同 workload 走完了
整个 source() 并进入 cmake configure，说明非确定性外部打断。

根因分析：
1) 直接死因是外部信号，配方无法阻止；
2) 但配方把暴露窗口拉得过大——conan get() 不做跨次缓存，每次预检重跑
   都在全新 source 目录里串行重新下载全部 ~160MB，source 阶段长达数十秒，
   网络抖动或看门狗超时都会命中；且一旦后续阶段失败，重跑又从零下载。

修复（与上轮 patch 计数修复完全不同的失败域，策略为缩短/消除暴露窗口）：
1) 持久 tarball 缓存：<conan home>/hcrt_src_cache/<sha256>.tar.gz，
   命中即跳过下载（重跑 source 只剩解压）；sha256 即缓存键+复用前校验。
2) 子模块下载并行化（4 线程），每个 URL 沿用 conandata.yml 有序列表
   逐镜像回退；流式计算 sha256，不匹配即弃并试下一镜像，聚合报错。
3) TLS 校验失败时降级重试（内容完整性仍由 sha256 强校验保证）。
4) 解压保持顺序执行，语义等价 get(strip_root=True)：要求唯一顶层目录，
   展开其内容到 crt/<name>；多顶层目录显式报错。

本地验证（stub 掉 conan 包后直接单测配方方法 + 本地 HTTP server）：
镜像回退(404→成功且仅 2 次请求)、缓存复用(0 次新请求)、sha256 不匹配拒绝
且不落盘、全镜像失败聚合报错、strip_root 解压产物逐项一致、多顶层目录拒绝、
6 任务并行取回全部成功、conandata 结构(主 url 与 13 个子模块均为
[gh-proxy 镜像, 官方] 有序二元组 + 64 位 sha256)。py_compile 通过。

状态：仅工作树修改（conanfile.py source 阶段加固 + notes 更新），
未 commit/push；等待 hmbs 复跑真机预检。若下次预检在冷缓存下仍被
SIGTERM 打断，属环境侧问题，但热缓存路径已可显著缩短重跑耗时。


## 本轮（2026-08-25 真机预检 test_package 失败：UUID v4 string format 断言）

真机证据：上游 ctest 85/85 全通过后，test_package 的 test_aws_crt 输出
"[FAIL] UUID v4 string format"、"1 check(s) FAILED"，退出码 1。

根因（对照上游源码确认，属消费者测试自身的断言笔误）：
1) aws-c-common source/uuid.c 的 UUID_FORMAT 为
   `%02x`×4 `-` ×2 `-` ×2 `-` ×2 `-` ×6（16 字节 → 8-4-4-4-12 共 36 字符，
   连字符仅在下标 8/13/18/23）；Aws::Crt::UUID::ToString() 直接走该格式化。
2) test.cpp 原断言额外要求 uuid[28]=='-'——下标 28 落在最后 12 字符组
   （24..35）内部、必为十六进制字符，断言恒假。
3) 另注意 aws_uuid_init 只是 aws_device_random_buffer 取 16 随机字节，
   不打 RFC-4122 version/variant 位，"v4" 命名亦不准确。

修复（加强而非削弱校验）：
1) 格式断言改为：长度 36 + 连字符恰在 8/13/18/23 + 其余 32 字符均为
   小写十六进制（逐位校验），标签改为 "UUID canonical string format 8-4-4-4-12"；
2) 新增第 7 项断言：以 UUID(const String&) 解析构造后 ToString() 与原串
   逐一相等且 operator bool 为真（覆盖 aws_uuid_init_from_str /
   aws_uuid_equals 往返路径）；
3) test_package/conanfile.py 的 HMBS_TEST_PACKAGE_RESULT 标记
   discovered/passedCount 同步 6→7；MANIFEST.yml 消费者描述与
   assertion_count 91→92 同步。

本地逻辑验证（无本地交叉编译器，按上游 UUID_FORMAT 语义建模复算）：
规范输出对新断言 PASS、对旧断言（下标 28 连字符）FAIL（复现真机现象）；
坏十六进制位 / 错连字符字符 / 缺连字符三种变异体均被新断言拒绝；
解析-再格式化往返字节一致。

状态：仅工作树修改（test.cpp + test_package/conanfile.py + MANIFEST.yml
+ notes 更新），未 commit/push；等待 hmbs 复跑真机预检。

## 本轮（2026-08-25 真机预检失败：test_package 报 res/upstream_test_result.json not found）

真机证据：配方 export 完成于 16:45:17 UTC，失败评论时间戳 16:45:23——
全程仅约 6 秒，aws-lc+s2n 全栈编译加 85 项 ctest 绝不可能 6 秒完成，
说明本次 conan create 命中上一轮已构建的包缓存（source/build/package
全部跳过），直接进入 test_package：消费者 7 项断言全部通过并打出
HMBS_TEST_PACKAGE_RESULT(7/7) 后，在 test() 第 65 行因包内缺
res/upstream_test_result.json 抛错。本轮 stdout 没有
HMBS_UPSTREAM_TEST_RESULT 行（build() 被跳过），hmbs 因此把上游测试
计为发现 0/执行 0/通过 0。

根因（证据链三处文件名不一致）：上一轮完整构建其实通过了上游测试全部门禁
（包能创建即要求 _run_upstream_tests 的 status_ok 为真），但 build() 把
结果 JSON 写成 ohos_upstream_test_result.json，package() 按原名复制进包 →
包内是 res/ohos_upstream_test_result.json；而 test_package 校验的路径是
res/upstream_test_result.json → 必然缺失。上轮只改了 test.cpp（UUID 断言），
conanfile.py 字节未变、RREV 不变，于是本轮命中旧缓存包原样复现该错误。

修复（统一命名，不改任何校验口径）：
1) build() 改写 <build>/upstream_test_result.json；
2) package() 同名复制到 <pkg>/res/，缺失时仍显式报错拒绝静默打包；
3) test_package 读 res/upstream_test_result.json 保持不变。
配方内容变化 → RREV 更新 → 下轮预检对旧缓存失效，强制重建+重跑上游
测试，build() 会真实打印 HMBS_UPSTREAM_TEST_RESULT（85 项口径不变）
并重新生成正确命名的证据 JSON。
验证：python -m py_compile 通过；grep 复核 build/package/test_package
三处引用全部为 upstream_test_result.json，仓库内无其他残留引用。

状态：仅工作树修改，未 commit/push；等待 hmbs 复跑真机预检。