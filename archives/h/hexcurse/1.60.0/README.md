# hexcurse 1.60.0 — OpenHarmony (aarch64) 编译归档

## 软件信息

- **名称**: hexcurse
- **版本**: 1.60.0
- **描述**: 基于 curses 的十六进制编辑器
- **许可证**: GPL-2.0
- **主页**: https://github.com/LonnyGomes/hexcurse
- **构建系统**: autotools (configure + make)

## 编译信息

- **目标平台**: OpenHarmony aarch64 (aarch64-unknown-linux-ohos)
- **编译器**: clang 15
- **链接方式**: 完全静态链接 (R26)
- **Conan 引用**: hexcurse/1.60.0@ohpcd/stable
- **编译状态**: published

## 依赖

- ncurses: 系统预装静态库 (libncurses.a)，无 Conan 依赖

## 文件清单

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (AutotoolsToolchain + Autotools) |
| conandata.yml | 源码 URL 和 SHA256 |
| test_package/ | Conan 测试包 (R28) |
| patches/ | 18 个补丁文件 |
| reports/test-report.md | 测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |
| reports/conan-create.log | Conan 构建日志 |
| manifest.yaml | 归档清单 |
| notes.md | 适配笔记 |

## 验证结果

conan-verify 8 道门禁全部通过:
- G0: 预构建风险评估 ✅
- G1: 配方完整性检查 ✅
- G2: conan create (干净构建) ✅
- G3: 静态链接验证 (R26) ✅
- G4: 产物完整性检查 ✅
- L2: 平台功能矩阵 (smoke test) ✅
- L4: 静态安全扫描 (checksec) ✅
- L5: 产物基线对比 ✅
