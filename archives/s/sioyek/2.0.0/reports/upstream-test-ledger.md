# 上游测试台账 — sioyek 2.0.0

上游仓库：https://github.com/ahrm/sioyek（tag v2.0.0，sha256 92398b6d...）
构建体系：qmake（pdf_viewer_build_config.pro），无 CMake/autotools 测试基建。

| 清点位置 | 结论 |
|---|---|
| 仓库根 tests/ | 不存在 |
| pdf_viewer/ 内 *_test* 文件 | 无 |
| .github/workflows | 仅 build_and_release.yml（构建发布，无测试 job） |
| .pro QMAKE / TESTS / check target | 无 |
| scripts/*.py | 运行时辅助脚本（TTS/论文下载器），非 pytest 体系 |
| resources/ | 配置与文档资源 |

结论：上游确无测试用例（N=0）。按 R51 自行补齐 test_package 三层冒烟
（ELF 架构断言 / 依赖解析 / --version 实跑），真机实测 3/3 通过 100%，
实测证据见 reports/test-report.md 与 reports/conan-verify-report.md。
