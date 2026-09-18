# 质量报告 — libbiosoup-dev 0.11.0

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ 含 source/build/package/package_info/export_sources/apply_conandata_patches |
| `conandata.yml` | ✅ 官方 codeload tag 0.11.0 URL + sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_biosoup.cpp` | ✅ 14 项断言，真实使用库 API |
| `test_package/MANIFEST.yml` | ✅ 上游测试（gtest）跳过声明 + `assertion_count = 14` |

## 产物 (G4)

- `include/biosoup/{nucleic_acid,overlap,progress_bar,sequence,timer}.hpp`
- `licenses/LICENSE`
- 纯头文件库：无 `bin/`、无 `lib/`，不需要 `commands.json`。

## 系统同名库隔离 (G3)

- 无编译产物，不产生 `.so`。

## 测试真实性 (R34 / L1e)

- test_package 通过 `find_package(biosoup)` + `biosoup::biosoup` 使用安装后的包。
- 移除包目录时测试无法编译，反向验证成立。

## 版本策略 (R37)

- 首次适配使用平台版本 `0.11.0`（上游 tag 0.11.0）。

## 风险

- 上游 GoogleTest 套件未运行；已复用其期望值覆盖核心 API 并在 MANIFEST 说明。
