# 质量报告 — lib1541img 1.1

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ 含 source/build/package/package_info/export_sources/apply_conandata_patches |
| `conandata.yml` | ✅ 官方 codeload tag v1.1 URL + sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_1541img.c` | ✅ 25 项断言，端到端使用库 API |
| `test_package/MANIFEST.yml` | ✅ 上游无测试声明 + `assertion_count = 25` |

## 产物 (G4)

- `lib/lib1541img.a`（23 个模块编译）
- `include/1541img/*.h`（24 个公共头）
- `licenses/LICENSE.txt`
- 纯库类型（无 `bin/`），不需要 `commands.json`。

## 系统同名库隔离 (G3)

- 仅产出静态库；`1541img` 非系统同名库。

## 测试真实性 (R34 / L1e)

- test_package 通过 `find_package(1541img)` + `1541img::1541img` 链接安装后的库并运行。
- 移除包目录时无法编译/链接，反向验证成立。

## 版本策略 (R37)

- 首次适配使用任务版本 `1.1`（上游 tag v1.1）。

## 风险

- 上游用 zimk 子模块构建；本仓库直接编译源文件，未使用上游 Makefile。
