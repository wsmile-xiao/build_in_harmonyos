# 质量报告 — units-cpp 2.3.4

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ 含 `source`/`generate`/`build`/`package`/`package_info`/`export_sources`/`apply_conandata_patches` |
| `conandata.yml` | ✅ 官方 codeload tag v2.3.4 URL（https）+ sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_units.cpp` | ✅ 20 项断言，真实使用库 API |
| `test_package/MANIFEST.yml` | ✅ 上游 188 用例清点、2 项排除原因、`assertion_count = 20` |

## 产物 (G4)

- `include/units.h`
- `licenses/LICENSE`
- 纯头文件库：无 `bin/`、无 `lib/`，不需要 `commands.json`。

## 系统同名库隔离 (G3)

- 无编译产物，不产生 `.so`，不存在 `/lib` 污染。

## 测试真实性 (R34 / L1e)

- test_package 通过 `find_package(units)` + `units::units` 使用安装后的包。
- 移除包目录时测试无法编译，反向验证成立。
- build() 内真实编译并运行上游 GoogleTest 套件（186/188），非伪造。

## 版本策略 (R37)

- 首次适配使用平台版本 `2.3.4` = 上游 tag `v2.3.4`。
- 与仓库内既有 `archives/u/units`（GNU units 2.22，application）为不同软件，不冲突。

## 风险

- 上游 2 项用例（locale、`CaptureStdout`/`/tmp`）因 OHOS 平台环境差异未运行，已逐条说明并在 MANIFEST 声明。
