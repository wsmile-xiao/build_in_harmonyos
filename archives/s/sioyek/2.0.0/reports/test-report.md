# 测试报告 — sioyek 2.0.0 (HarmonyOS PC, aarch64)

- 适配版本：sioyek/2.0.0（qmake + Qt5 + mupdf 桌面 PDF 阅读器）
- 适配平台：aarch64-linux-ohos（鸿蒙 PC，真机 runner003）
- 验证时间：2026-09-19（conan create 第 14 轮全绿）

## 上游测试三步法（R51）申报

### 1. 清点（适配前）
| 清点项 | 结果 |
|---|---|
| tests/ 目录 | 不存在 |
| ctest 注册数 | 0（无 CMake 工程） |
| pytest 注册数 | 0（scripts/ 下 .py 为运行时辅助脚本，非测试） |
| make check / test target | 不存在（qmake .pro 无 check target） |
| CI workflow 测试 job | 无（build_and_release.yml 仅构建发布） |
| 证据 | git tag v2.0.0 树逐项核查；notes.md「R51 测试申报」节 |

### 2. 运行（真机实测）
上游确无自带测试用例（N=0），无法运行；test_package 自行补齐冒烟测试并在真机 100% 执行：

| 测试 | 内容 | 结果 |
|---|---|---|
| test_package ELF 断言 | bin/sioyek 为 aarch64 musl ELF | PASS |
| test_package 依赖解析 | conanrun 环境 ldd NEEDED 全解析（libz/Qt5Core/Gui/Widgets/Network/OpenGL/GLESv2/libc++_shared/mupdf 静态内链） | PASS |
| test_package 实际运行 | conanrun.sh 环境 `sioyek --version` → `sioyek 2.0.0`（main.cpp:662 QApplication 构造前处理，无显示环境可真实运行） | PASS |
| staging 复核 | conan 缓存包 bin/sioyek `--version` rc=0（本机 FUSE 环境直接执行） | PASS |

### 3. 回填（R51 结论）
- 上游测试：清点 0 个（确无测试，证据见上表与 notes.md）
- test_package 冒烟：N = 3，通过 N′ = 3，通过率 **100%**
- 无「待 CI 测试」占位；平台 CI 若复跑 test_package 结果应一致

## conan 验证（同机同轮）
- G1 配方完整性 / G2 conan create / G3 同名库隔离 / G4 产物完整性：全部 PASS
- L2 smoke / L4 checksec / L5 基线对比：PASS（reports/conan-verify-report.md）
- W2 归档结构（L0a-L0e）/ W3 本地 CI 模拟：PASS（reports/w3-local-ci.log）
