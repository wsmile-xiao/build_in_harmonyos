# spirit-po 1.1.2 测试报告

## 验证环境

- 平台：HarmonyOS PC / OHOS aarch64
- 编译：OHOS clang 15.0.4，libc++，C++11-17
- Conan：2.29.1（OHOS 适配版，profile `ci/conan/profiles/ohos-aarch64`）
- 依赖：`boost/1.90.0`

## 上游测试

| 类别 | 口径 | 用例数 | 结果 |
|---|---|---|---|
| 单元测试 `test/main.cpp` | 运行时 assertion（TEST/CHECK_*） | 126 | 126 通过 |
| libintl 对照 `test_libintl/main.cpp` | 每个 `po/*.po` 一个 executable-level case | 206 | 206 跳过（无 libintl.h/链接库） |
| **合计** | | **332** | **126 PASS + 206 SKIP，0 FAIL** |

上游单元测试在 Conan `build()` 内复现执行：`Upstream unit test: 126/126 assertions passed`，覆盖 22 个 PO fixture（12 正常 + 10 失败输入）。

libintl 206 项技术原因：`test_libintl/CMakeLists.txt` 要求 `find_package(Boost/Gettext/Intl REQUIRED)` 并链接 `${INTL_LIBRARIES}`；当前 OHOS worker 仅有 `msgfmt 0.26`，没有 `libintl.h`，也没有 `libintl.so/.a`，不能以 msgfmt 代替运行时对照。已如实列为 SKIP 而非压缩分母或伪 PASS。

## 消费者测试（test_package）

`test_spirit_po.cpp` 通过 `spirit-po::spirit-po` 真实链接，验证 `from_range` 解析 header、`size()`、`gettext/pgettext/ngettext` 复数选择与缺失 key 回退（7 断言/1 可执行用例）。

- conan create 内运行：`RUN: bash -c './test_spirit_po'`（退出 0）
- CI L1e 破坏性反向验证：`[ok] L1e: Negative test confirmed — test genuinely depends on spirit-po`

## 门禁结果

- conan-verify：PASS（G1/G2/G3/G4 + L2/L4/L5，header-only 无 bin/lib 对应跳过）
- W3 build_and_test.sh：Success 1，Failed 0，L0=pass，L1=pass，L2=skip（无 bin/），L4=pass，L5=warn（无产物），Pass rate 100%
- `.ci-result.json` exit_code=0
- 归档状态：`built`（设备验证完成，待合并后 release upload 才转 published）
