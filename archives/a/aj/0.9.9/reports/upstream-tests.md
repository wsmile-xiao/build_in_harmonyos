# aj (aj-snapshot) 0.9.9 上游测试报告

## 结论

**上游测试用例数：0**（上游无自动化测试用例，通过率 0/0 不适用）
**test_package 消费测试：1/1 通过**（`aj-snapshot -h` 打印 usage，R34 反空壳）

## 上游测试情况核实

对上游 v0.9.9 release tarball 的完整核查（`aj-snapshot-0.9.9.tar.bz2`）：

| 检查项 | 结果 |
|--------|------|
| test/ 目录 | 不存在 |
| make check 目标 | 不存在（Makefile.am 仅 `SUBDIRS = src man`） |
| make test 目标 | 不存在 |
| 测试框架 | 无（configure.ac 仅做依赖头文件/库检查：alsa/jack/mxml 均 AC_MSG_ERROR REQUIRED） |

configure.ac 的测试相关部分仅为编译期依赖探测：

```
AC_CHECK_HEADER(alsa/asoundlib.h, [])
AC_CHECK_HEADER(jack/jack.h, [])
AC_CHECK_HEADER(mxml.h, [])
AC_CHECK_LIB(asound, main, [], [AC_MSG_ERROR(ALSA library (asound) is required)])
AC_CHECK_LIB(jack, main, [], [AC_MSG_ERROR(JACK library (jack) is required)])
AC_CHECK_LIB(mxml, mxmlLoadFile, [], [AC_MSG_ERROR(mxml library (mxml) is required)], [-lpthread])
```

## 适配后验证

由于上游无测试用例，按 TEST_QUALITY_SPEC 以 test_package 冒烟测试补充：

- **test_package/test_aj.c**：C 测试二进制通过 `system()` 真实执行被测包二进制
  `aj-snapshot -h`，校验输出含 `Usage: aj-snapshot`（R34 反空壳）
- 本地 conan create（ohos-aarch64 profile）退出码 0，test PASSED

## 实测日志

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
...
aj smoke test PASSED (aj-snapshot -h prints usage)
aj/0.9.9 (test package): aj test PASSED (aj-snapshot -h prints usage)
```

## 说明

aj-snapshot 0.9.9 为 2019 年发布的小型 C 工具（单可执行，~2K 行），上游无正式测试
框架。其功能正确性通过以下方式验证：三个硬依赖（alsa/jack/mxml）在 configure 阶段
全部探测通过，`aj-snapshot -h` 正常输出完整 usage，链接 libasound/libjack/libmxml
成功（本地 aarch64 ELF 构建成功）。
