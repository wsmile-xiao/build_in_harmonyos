# 测试报告 — libbigwig 0.4.8
<!-- 放置路径: archives/l/libbigwig/0.4.8/reports/test-report.md -->

> **项目**: libbigwig
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS(HongMeng 内核)aarch64 设备,clang 15.0.4,Conan 2.29.1 私有缓存(zlib/1.3.1.1 + curl/8.15.0,ohpcd 制品仓)
> **测试类型**: 官方测试套件(上游 test/,make test 等价物)+ 消费者功能测试(test_package)

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 8 | 100% |
| 通过 (PASS) | 7 | 87.5% |
| 失败 (FAIL) | 1 | 12.5% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **87.5%**(唯一 FAIL 为 https 远端样例的运行环境 CA 限制,本地全部功能通过;详见 2.2)

单位口径:测试程序数。8 = 上游 7 个测试程序(testLocal、testWrite、exampleWrite、testIterator、testRemote、testRemoteManyContigs、testBigBed)+ test_package 消费者测试 1 个(test_libbigwig)。

---

## 二、测试结论

### 2.1 总体评价

✅ **可用**。本地读写、文件创建、迭代遍历、染色体表与区间索引全部功能通过;经 libcurl 的 http 远端读取通过;包消费者(静态链接)头文件、库导出与运行时行为验证通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| testBigBed(ENCODE https 源)打开失败 | 仅 https 远端样例;根因是上游代码未设 `CURLOPT_CAINFO`,制品仓 conan curl/openssl 栈在设备上无编译期默认 CA 路径(TLS rc=60;显式指定 CAINFO 后服务器返回 HTTP 206) | 🟢 环境限制,非适配缺陷 |

### 2.3 可用功能清单

```
✅ 本地 bigWig 读取: testLocal(test.py 断言输出 md5 逐字节命中,程序内 14 处 assert 通过)
✅ 本地 bigWig 重写: testWrite(产物 md5 8e116bd1… 逐字节命中)
✅ 从零创建 bigWig: exampleWrite(产物 md5 ef104f19… 逐字节命中)
✅ 数据块迭代遍历: testIterator(exit 0,输出 5 条迭代块)
✅ http 远端读取: testRemote / testRemoteManyContigs(UCSC,test.py md5 断言命中)
✅ 消费者静态链接与回环: test_package/test_roundtrip.c(写入→重开→逐条核对 13 处检查点)
⚠️ https 远端读取: 需运行环境提供 CA 证书路径(上游未设 CURLOPT_CAINFO)
```

### 2.4 已知限制

1. https 远端访问依赖运行环境 CA 配置(见 2.2);http 不受影响。
2. `with_curl=False` 构建变体不含远端访问(上游 NOCURL 语义),由选项显式选择,默认开启完整功能。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| testLocal(test/test.bw) | 读取并断言头/染色体/区间 | ✅ PASS |
| testWrite(test/test.bw → out) | 重写文件(md5 命中) | ✅ PASS |
| exampleWrite | 从零创建(md5 命中) | ✅ PASS |
| testIterator(test/test.bw 1 100) | 块级迭代 | ✅ PASS |
| testRemote(UCSC http) | 远端读取(md5 命中) | ✅ PASS |
| testRemoteManyContigs(UCSC http) | 非叶染色体树(md5 命中) | ✅ PASS |
| test_libbigwig(test_package) | 消费者回环 13 处检查点 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 功能 | 结果 | 失败原因 |
|--------|------|------|----------|
| testBigBed(ENCODE https) | 远端 bigBed 读取 | ❌ FAIL | TLS 握手 rc=60:上游未设 CURLOPT_CAINFO,conan openssl 无设备默认 CA 路径;最小探针显式 CAINFO=/etc/ssl/certs/cacert.pem 后 rc=0 且 HTTP 206。证据:reports/upstream-tests.md |

---

## 四、上游测试驱动与证据

- 上游驱动: `test/test.py`(6 个测试函数、8 处 assert): 5 过 1 挂,与上表一致。
- 逐字证据: `reports/upstream-tests.md`(原始日志哈希在文中注明)。
- 包构建内验证: conan create + test_package(W3,`.ci-result.json` exit 0,
  conan-verify-report G0–G4/L2/L4/L5 全 passed)。
