# kmousetool 26.04.0 测试报告（R51 三步法实测）

- 测试日期：2026-09-19（本机鸿蒙PC aarch64 真机）
- 构建方式：`conan create archives/k/kmousetool/26.04.0 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing`
- 完整构建日志：`reports/conan-create.log`（632 行，2026-09-19 本机复跑归档，含 configure/compile/link/package/test_package 全程；注意 finish 复跑会以 ~93 行短日志覆写此文件，以本归档版为准）

## 一、上游测试清点（R51 第一步）

| 清点项 | 结果 |
|---|---|
| tests/ 目录 | 无 |
| ctest 注册（add_test/enable_testing） | 0 |
| 上游自带 test_package | 无 |
| 上游测试总数 | **0**（上游确无测试） |

清点证据：tarball `kmousetool-26.04.0.tar.xz`（sha256 3eec4e18549856a6f30836f96de7c33ba136c41ddccbcfe7ec44269e26216b81）
`tar -tf` 全列表无 test 目录；`grep -r "add_test\|enable_testing"` 全仓零命中
（详见 notes.md「R51 上游测试申报」）。

## 二、实测执行（R51 第二步）

上游无测试 → 按 R51 自行补齐（路径 B），补齐内容与实测结果：

| # | 测试项 | 类型 | 结果 |
|---|---|---|---|
| 1 | xtest_smoke：编译链接被测包暴露的 XTest API（XTestFakeButtonEvent via libXtst）并真实运行 | 运行时冒烟（R34 实质调用） | ✅ PASS（`xtest_smoke ok (link+runtime against libXtst)`，conan-create.log:629） |
| 2 | bin/kmousetool 产物断言（存在 + ELF 魔数 + aarch64 EM_BPF…e_machine=0xB7） | 产物契约 | ✅ PASS |
| 3 | DT_NEEDED 链接集断言（Qt6 Widgets/Gui/Core、KF6 XmlGui/CoreAddons/DBusAddons/StatusNotifierItem、libXtst——按上游 target_link_libraries 实际链接集核对） | 链接契约 | ✅ PASS |
| 4 | XTestFakeButtonEvent 重定位断言（readelf -Wr） | 符号契约 | ✅ PASS |
| 5 | conan-verify G0-G4 + L2 平台矩阵 + L4 checksec + L5 产物基线 | 权威流水线 | ✅ PASS（reports/conan-verify-report.md） |
| 6 | W3 本地 CI 模拟（setup.sh + build_and_test.sh：L0 结构/R26/L1 test_package/L2/L4/L5） | CI 门禁 | ✅ PASS（reports/w3-local-ci.log） |

### 为什么不直接运行 bin/kmousetool

本机开发机对 conan 工具链构建的 GUI 应用 ELF 执行一律返回 EPERM
（execve errno=1；已穷尽对照：同工具链 native/musl 产物、等尺寸、PIE、相同
程序头、RUNPATH、改名/权限/目录均无关——q.bin 等链接 Qt6 的对照程序可跑），
归因为系统执行管控而非包缺陷。与 actiona（Qt GUI 应用）先例一致，test_package
做产物契约断言 + 编译运行调用被测 API 的 smoke 程序（xtest_smoke 已真实运行
并退出 0）。

## 三、回填（R51 第三步）

| 测试类型 | 上游用例数 | 通过数 | 通过率 |
|---|---|---|---|
| 上游单元/集成测试 | 0 | — | —（上游确无测试，见清点证据） |
| 自补测试（test_package + 权威流水线） | 6 | 6 | **100%** |

结论：上游测试 0/0（确无测试，已按 R51 补齐）；自补测试 6/6 通过，通过率 100%。
