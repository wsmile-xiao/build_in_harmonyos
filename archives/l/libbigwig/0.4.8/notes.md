# libbigwig 0.4.8 适配笔记

## 1. 基本信息

- 软件: libbigwig 0.4.8(上游 GitHub tag 0.4.8,bigWig.h 中 LIBBIGWIG_VERSION "0.4.8")
- 上游: https://github.com/dpryan79/libBigWig(MIT,C 语言)
- 构建: CMake ≥3.8;源码为 io.c/bwValues.c/bwRead.c/bwStats.c/bwWrite.c 五个编译单元
- 依赖: zlib(必需)、libcurl(`WITH_CURL`,默认 ON)、libm
- 源码包: https://github.com/dpryan79/libBigWig/archive/refs/tags/0.4.8.tar.gz
  sha256 `10e904ea6eab4c9926dd938050af888bebe6281e8d933237e4a254cb9d3063b1`
  (macOS 本地下载核验;CI 由 conandata.yml 校验同一哈希)

## 2. W0/W0b

- 无历史归档与历史 notes(全新适配),无历史经验可迁移
- W0(2026-09-18,私有 CONAN_HOME,ohpcd): 目标版本未被占用(missing);
  zlib/1.3.1.1 available;curl/8.15.0 available → 依赖齐备,正常适配。
  报告: reports/W0-report.md
- 依赖决策: zlib 取 1.3.1.1 而非 1.3.1,与 curl/8.15.0 配方的传递依赖
  (`self.requires("zlib/1.3.1.1")`)保持同一版本,避免依赖图冲突;
  curl/8.15.0 的 cmake_file_name=CURL、cmake_target_name=CURL::libcurl,
  与上游 `find_package(CURL REQUIRED)` + `CURL::libcurl` 完全匹配,无需补丁。

## 3. 配方要点

- 上游 CMakeLists 无需任何修改: 无 CMake<3.5 兼容问题(≥3.8,满足 CMake 4);
  产物 `libBigWig.a`/`libBigWig.so`,PUBLIC 头 4 个安装到 `include/libbigwig/`
- 选项映射: `shared`→`BUILD_SHARED_LIBS`,`with_curl`→`WITH_CURL`(OFF 时上游定义 `NOCURL`),
  `ENABLE_TESTING=OFF`(包构建内不编译上游测试程序)
- 无 patches/:源码可移植(stdio+zlib+curl,无 mmap/pthread/平台宏),无需适配补丁
- package_info: libs=["BigWig"],system_libs=["m"];cpp_info 属性导出
  cmake_file_name=libbigwig、cmake_target_name=libbigwig::libbigwig
- 库类型包,无可执行产物,不需要 commands.json(R38)

## 4. 上游测试(R51 三步法)

清点(test/ 目录,无 CTest 注册,`make test` 编译后由 test/test.py 驱动 6 个测试函数、共 8 处 assert):

| 测试程序 | 类型 | 数据源 | 断言方式 |
| --- | --- | --- | --- |
| testLocal | 单元/本地 | test/test.bw | 程序内 14 处 assert;test.py 校验输出 md5 |
| exampleWrite | 单元/本地 | 从零创建 | test.py 校验产物 md5 |
| testWrite | 单元/本地 | test/test.bw 重写 | test.py 校验产物 md5 |
| testIterator | 单元/本地 | test/test.bw | 打印迭代块(人工核对退出码) |
| testBigBed | 集成/远端 | encodeproject URL | test.py 校验输出 md5 |
| testRemote | 集成/远端 | UCSC URL | test.py 校验输出 md5 |
| testRemoteManyContigs | 集成/远端 | UCSC URL | test.py 校验输出 md5 |

实跑(OHOS 设备,与本配方同一 conan 依赖栈,ENABLE_TESTING=ON 构建 7 个测试程序):

- test.py 6 个测试(8 处 assert): **PASS 5 / FAIL 1**。
  testLocal 输出 md5 `1c520652…`、testWrite 产物 md5 `8e116bd1…`、exampleWrite 产物
  md5 `ef104f19…`、testRemote(UCSC http)与 testRemoteManyContigs(UCSC http)输出
  md5 断言全部逐字节命中;testBigBed(ENCODE https)FAIL。
- testIterator 手动运行 exit 0,迭代块输出正常。
- testBigBed 根因(证据链完整): 上游代码未设 `CURLOPT_CAINFO`,制品仓 conan
  curl/openssl 栈在 OHOS 设备无编译期默认 CA 路径 → TLS rc=60;最小探针显式
  CAINFO=/etc/ssl/certs/cacert.pem 后 rc=0 且服务器返回 HTTP 206(两种 UA 均可),
  `SSL_CERT_FILE` 环境变量不能恢复。属环境 CA 路径限制,非库/配方缺陷;
  两个 http 远端用例通过佐证远端读取功能正常。
- 证据: reports/upstream-tests.md(原始日志在任务目录 evidence/uptest-20260918/,
  PR 内转写注明原件哈希)。

本地(macOS)预演: test.py 本地 3 项断言通过、remote 3 项跳过——用于校准,不作为
交付证据。

## 5. test_package(消费者测试)

test_roundtrip.c: bwInit → 写文件(bwCreateHdr/bwCreateChromList/bwWriteHdr/
bwAddIntervals 区间块 + bwAddIntervalSpans 跨度块)→ 关闭 → 重开 →
bwGetOverlappingIntervals 查询全区间 → 逐条核对染色体表/条目数/坐标/值
(13 处检查点)。原生预演(macOS)通过后才提交;设备端随 conan create 实跑。

## 6. 已知限制

- `with_curl=False` 构建的包不含远端访问(NOCURL),由选项显式选择,默认保留完整功能
- https 远端访问依赖运行环境 CA 路径: 上游不设 CURLOPT_CAINFO,设备/CI 上若
  conan openssl 无默认 CA bundle,https 源打开会失败(http 不受影响);
  消费者可用 `curl_easy_setopt` 或自设 CA 环境解决(见 reports/upstream-tests.md)

## 7. 验证记录

- W3(finish 内 conan create + test_package): 见 .ci-result.json 与 reports/
- 上游测试实跑: reports/upstream-tests.md(6 断言 5 过 1 挂,环境根因)
