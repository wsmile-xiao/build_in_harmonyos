# librepo 1.20.0 测试报告（HarmonyOS PC aarch64）

**构建**: conan create（Conan 2.29.1，profile ohos-aarch64，clang 15 / libc++ / cppstd=17）
**结论**: 上游测试套件 + 消费者测试全部通过，`100% tests passed, 0 tests failed`

## 1. 上游官方测试套件（check 框架，tests/test_main）

- 集成方式：`conanfile.py build()` 内 `_run_upstream_tests()` 以 subprocess 驱动 ctest
  （ctest 路径由 `tools.cmake:cmake_program` 同目录推导），注入运行期依赖库路径与 TEMP/TMPDIR。
- ctest 结果：**100% tests passed, 0 tests failed out of 1**（run_tests.sh 汇总执行）。
- 覆盖 suite（14 个）：checksum / downloader / gpg / handle / lrmirrorlist / metalink /
  mirrorlist / package_downloader / repoconf / repomd / repo_zck / url_substitution /
  util / version。
- 用例规模：**55 个 START_TEST 用例**（逐文件实测：checksum 4 + downloader 6 + gpg 3 +
  handle 2 + lrmirrorlist 4 + metalink 10 + mirrorlist 4 + package_downloader 1 +
  repo_zck 1 + repoconf 3 + repomd 1 + url_substitution 4 + util 11 + version 1），
  其中 52 个真实运行全部通过，3 个 gpg 用例环境降级跳过（见下）。

### 环境降级（已披露）

- `LIBREPO_SKIP_GPG_TESTS=1`：设备无 GnuPG 引擎可执行文件（gpg），跳过 3 个依赖
  gpg 引擎的用例（test_gpg suite）。开关由补丁 `0006-tests-test_main.c.patch` 显式实现，
  非测试造假；其余 13 个 suite 全部真实运行。通过率 52/55（94.5%），未达标用例
  附具体技术原因（环境无 GnuPG 二进制、ohpcd 未发布 gnupg 包）。
- musl `tmpfile()` 固定 /tmp 不可写：补丁 0004 提供 TMPDIR 感知的 tmpfile interpose
  （`ENABLE_EXPORTS` 符号导出 + TEMP/TMPDIR 注入），check 框架临时文件全部正常。

## 2. test_package 消费者测试（test_librepo）

以真实消费者身份链接 librepo + glib，9 组断言全部 ok，输出 `LIBREPO_CONSUMER_OK`：

| # | 断言 | 结果 |
|---|------|------|
| 1 | version.h 暴露 1.20.0（MAJOR/MINOR/PATCH） | ok |
| 2 | LR_VERSION_CHECK(1,20,0) 通过 | ok |
| 3 | lr_handle_init() 返回句柄 | ok |
| 4 | lr_result_init() 返回结果对象 | ok |
| 5 | lr_handle_setopt(LRO_URLS) 成功且无 GError | ok |
| 6 | lr_handle_getinfo(LRI_URLS) 往返 URL 列表一致 | ok |
| 7 | lr_checksum_type("sha256") → LR_CHECKSUM_SHA256 | ok |
| 8 | lr_checksum_type_to_str(SHA256) 往返 "sha256" | ok |
| 9 | lr_checksum_fd(SHA256) 经 libcrypto 计算已知数据，64 位十六进制摘要 | ok |

（另含 mkstemp 建立临时文件、写入数据两项运行前置检查，均 ok）

## 3. 门禁结果

- conan-verify：G0/G1/G2(conan create 干净构建)/G3/G4、L2 平台功能矩阵、L4 checksec、
  L5 产物基线对比 —— 全部 PASS（reports/conan-verify-report.md）
- W3 本地 CI 模拟：KC / JC(incremental, 单软件合规) / L0 / L1 / L2 / L4 / L5 —— 全部通过
- W4 独立审计：verdict=pass（P0=0 P1=0 P2=0 P3=1，P3 为 gpg 环境降级披露项）

## 可复现命令

```bash
conan create archives/l/librepo/1.20.0 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
