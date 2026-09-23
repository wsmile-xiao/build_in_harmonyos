# libbigwig/0.4.8 上游测试实跑报告(R51)

- 执行时间: 2026-09-18;执行位置: OHOS 设备(armv8,clang 15.0.4 原生)
- 构建方式: 上游源码(sha256 `10e904ea…` 与 conandata.yml 同源)+ 本任务配方经
  `conan install --build=missing` 生成的 CMakeToolchain/CMakeDeps(私有 CONAN_HOME,
  zlib/1.3.1.1 + curl/8.15.0 取自 ohpcd),`ENABLE_TESTING=ON` 构建全部 7 个上游测试程序。
  该构建与包配方同一依赖栈,即"适配后真实配置"。
- 原始日志(任务目录 evidence/uptest-20260918/):
  - `full-evidence.log`(sha256 `7b4a8538e463814ae93477e4f45bf38eca433b196b9a1f8ef84e3316d1b2f45e`,28 行,1658 字节)
  - `md5-evidence.log`(sha256 `ea69370024ece530754bc01baa4d65824afd47b69fd3a2f97df064c7041ad4bc`,10 行,261 字节)
- 上游驱动: test/test.py(6 个测试函数、共 8 处 assert,顺序执行,通过不打印、失败抛异常;末尾打印 success)

## 结果总表

| # | 上游断言(test.py) | 程序 | 期望 | 实测 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 1 | local_test 输出 md5 `1c520652…` | testLocal | 1c52065211fdc44eea45751a9cbfffe0 | 同(程序内另含 14 处 assert,exit 0) | **PASS** |
| 2 | remote_http_test 输出 md5 `9ccecd6c…` | testRemote(UCSC http) | 9ccecd6c32ff31042714c1da3c0d0eba | 断言通过(test.py 顺序流未失败) | **PASS** |
| 3 | test_recreating_file 产物 md5 `8e116bd1…` | testWrite | 8e116bd114ffd2eb625011d451329c03 | 同(md5-evidence.log 逐字) | **PASS** |
| 4 | test_creation_from_scratch 产物 md5 `ef104f19…` | exampleWrite | ef104f198c6ce8310acc149d0377fc16 | 同(md5-evidence.log 逐字) | **PASS** |
| 5 | remote_test2 输出 md5 `a15a3120…` | testRemoteManyContigs(UCSC http) | a15a3120c03ba44a81b025ebd411966c | 断言通过(test.py 顺序流未失败) | **PASS** |
| 6 | test_bigbed 输出 md5 `33ef9957…` | testBigBed(ENCODE https) | 33ef99571bdaa8c9130149e99332b17b | 程序 exit 1: `[bwHdrRead] There was an error while reading in the header!` | **FAIL(环境根因,见下)** |

test.py 整体 rc=1(第 6 项失败)。testIterator 不属于 test.py 断言,另做手动运行:
`./testIterator test/test.bw 1 100` exit 0,输出 5 条迭代块(逐字见 full-evidence.log)= **PASS**。

**汇总: 6 个测试函数(8 处 assert)全部实跑,PASS 5,FAIL 1;另 testIterator 手动 PASS。**

## testBigBed 失败根因(完整证据链)

1. 失败现象: 打开 `https://www.encodeproject.org/files/ENCFF001JBR/@@download/ENCFF001JBR.bigBed`
   时 bwHdrRead 失败(full-evidence.log 第 4-17 行)。
2. 同期两个 **http** 远端用例(UCSC)均 PASS → 远端读取功能本身正常。
3. 最小 TLS 探针(链接同一 conan libcurl/openssl):
   - 默认 CA 路径: `rc=60 (SSL peer certificate or SSH remote key was not OK)`
   - `CURLOPT_CAINFO=/etc/ssl/certs/cacert.pem`: `rc=0`
   - 设置 `SSL_CERT_FILE` 环境变量**不能**恢复(该 conan openssl 不走此默认路径)
4. 带 CAINFO 后两种 UA(libcurl/8.15.0 与 Python-urllib)均获 **HTTP 206 Partial Content**
   (full-evidence.log 第 26-28 行)→ 服务器完全正常。
5. 结论: 上游 libBigWig 未设 `CURLOPT_CAINFO`,而制品仓 conan curl/openssl 栈在 OHOS
   设备上无编译期默认 CA bundle 路径 → https 远端握手失败。属**环境 CA 路径限制**,
   非 libbigwig 代码或配方缺陷;http 用例与全部本地用例不受影响。
   设备可用 CA 事实与本设备 ssl 实测一致(本地技术索引 §1)。

## 字节级复现说明

设备系统 libz 的 deflate 输出与上游期望不一致(初步手工 -DNOCURL 构建时
testWrite/exampleWrite 产物 md5 不匹配,调查证据 evidence/uptest-20260918/ 过程记录),
但**包依赖栈(conan zlib/1.3.1.1)下三个本地 md5 全部逐字节命中**,即随包发布的
真实依赖组合在 OHOS 上可完整复现上游字节期望;此前差异不构成交付限制。

## 口径

- 上游测试程序清单 N=7(单元/本地 4: testLocal、testWrite、exampleWrite、testIterator;
  集成/远端 3: testRemote、testRemoteManyContigs、testBigBed)
- 实跑 N′=7(全部执行),PASS=6(test.py 5 项 + testIterator 手动),FAIL=1(testBigBed,环境根因)
- 断言口径: test.py 8 处 assert 对应 6 个测试函数,PASS 5 / FAIL 1
