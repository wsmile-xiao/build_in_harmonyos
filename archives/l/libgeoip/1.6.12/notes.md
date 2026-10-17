# libgeoip 1.6.12 适配笔记

## 编译环境
- 构建系统: autotools（tarball 无 configure，autoreconf -fiv 引导）
- 编译日期: 2026-09-16
- 编译器: clang 15（/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

1. 上游 v1.6.12 tarball 只带 configure.ac，不带 configure → `sh bootstrap`
   （内部 autoreconf -fiv；automake/1.18 + libtool/2.5.4 走 tool_requires）
2. 生成 configure 后修 E114（`umask 077` 两处替换，HMDFS setgid 目录问题）
3. `./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
   --prefix=<staging>`（triplet 显式传，绕过 config.guess 探测；本机即 OHOS aarch64，
   conftest 可直接运行，全部 AC_CHECK_FUNC 通过：pread/mmap/vasprintf/gethostbyname_r...）
4. `make -j1`（E074 HMDFS jobserver fifo EPERM）→ 全产物编译成功
5. `make check` → 上游注册 TESTS 2/2 PASS
6. `make install DESTDIR=<staging>` → libGeoIP.so/a + geoiplookup(6) + GeoIP.h/GeoIPCity.h + geoip.pc

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 无 configure | 上游 release 只带 configure.ac | build() 内 `sh bootstrap`（autoreconf -fiv），automake/libtool tool_requires（同 codecrypt 1.8 方案） |
| 2 | bootstrap 脚本无执行权限 | tarball 解出 -rwxrwx---，CI 用户缺组位（E126） | os.chmod(bootstrap, 0o755) |
| 3 | config.status 临时目录不可写 | E114: HMDFS setgid 把 `umask 077 && mktemp -d` 建的 0700 目录变成 drwx--S--- | 生成后 replace_in_file 两处 umask 077（同 abiword/aaphoto/codecrypt 方案） |
| 4 | config.guess 不识别 HarmonyOS | stock config.guess 不认 HarmonyOS uname | triplet 显式 `--build/--host=aarch64-unknown-linux-ohos`，configure 不跑 config.guess 探测 |
| 5 | parallel make 卡死 | E074: HMDFS jobserver fifo EPERM | make -j1 |
| 6 | 源码级适配 | 无需——所有 configure 探测在 musl/OHOS 全通过，源码零改动 | 零源码补丁 |
| 7 | CI checkout-pr 报 `binary patch does not apply to test_package/GeoIP.dat` | GitCode PR diff 通道对真二进制文件（含 NUL）不携带 binary patch data，git apply 必失败 | 样例库改 base64 文本形态（GeoIP.dat.b64，5.3KB）随 PR 提交，test() 内解码到 build 目录 + sha256 校验后使用 |

## 源码修改

无源码补丁（patches: {}）——全部适配在构建系统层完成（bootstrap + configure 内修）。

## 依赖版本

- 无运行时依赖（核心库不用 zlib，.dat 读取走裸 stdio+mmap）
- automake/1.18 + libtool/2.5.4（tool_requires，制品仓）

## 验证结果

```bash
# 探索阶段实测（设备原生，make check 全输出）
PASS: test-geoip                  # 61 IP 向量集 × (code/code3 × addr/name) 全对
PASS: test-geoip-invalid-file     # 无效文件容错
============================================================================
Testsuite summary for GeoIP 1.6.12
# TOTAL: 2 / # PASS: 2 / # FAIL: 0
============================================================================

# 工具 smoke test（样例 GeoIP.dat，tarball 自带）
$ ./apps/geoiplookup -d ./data 12.87.118.0
GeoIP Country Edition: US, United States
$ ./apps/geoiplookup -d ./data 63.147.126.103
GeoIP Country Edition: FR, France
$ ./apps/geoiplookup6 -v    # usage 正常输出
```

## 上游测试情况（rule4 / N 核验）

上游 test/Makefile.am：
- `TESTS = test-geoip test-geoip-invalid-file`（注册测试 N = 2，实测 `make check` TOTAL: 2）
- 另有 8 个 noinst_PROGRAMS（benchmark + test-geoip-region/city/org/domain/asnum/isp/netspeed）：
  **编译链接全通过但不在 TESTS 注册**，且运行需要 MaxMind 商业数据库
  （GeoIPRegion.dat/GeoIPCity.dat/GeoIPOrg.dat/GeoIPDomain.dat/GeoIPASNum.dat/
  GeoIPISP.dat/GeoIPNetSpeed.dat）——tarball 只带 GeoIP.dat（国家库样例），
  商业库需付费购买无法获取。实测报错样例：
  `Error Opening file ../data/GeoIPRegion.dat / Error opening database`。
  按上游注册口径申报 N=2，ninst 8 个不折叠不虚报。
- 上游 CI（.travis.yml）也是跑 `make check`（同 2 个）。

→ 上游测试 N = 2，本地实跑 2/2 PASS（100%）。

## 注意事项

- 产物 = libGeoIP 库 + geoiplookup/geoiplookup6 工具 → package_type=library +
  bindirs，commands.json 在软件级声明（R38，type=tool）
- 数据文件（GeoIP.dat 等）不打包——运行时用户自备（上游同口径）；
  test_package 携带 tarball 内自带的样例 GeoIP.dat（base64 文本形态 GeoIP.dat.b64，
  因 GitCode PR diff 通道无法携带二进制文件；test() 解码+sha256 校验）+ country_test.txt 向量集做真实验证
- 系统无同名 libGeoIP（R26 核查通过：/lib /lib64 /system/lib* 均无）→ 默认动态
- GeoIP2（libmaxminddb）是新一代替代品，不同软件，本件为 Legacy 线最终版 1.6.12
---

**编译结束**: 2026-09-16 01:22
**最终状态**: built
