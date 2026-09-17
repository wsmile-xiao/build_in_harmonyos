# 质量报告 — tinyxxd 1.3.16

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ 含 source/build/package/package_info/export_sources/apply_conandata_patches |
| `conandata.yml` | ✅ 官方 tag v1.3.16 URL + sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_tinyxxd.py` | ✅ 18 项检查，运行安装后的二进制 |
| `test_package/MANIFEST.yml` | ✅ `assertion_count = 18`，上游 16 |
| 软件级 `commands.json` | ✅ 工具类型（R38） |

## 产物 (G4)

- `bin/tinyxxd`（0755）
- `share/man/man1/tinyxxd.1`
- `licenses/LICENSE`
- CLI 包：`package_type="application"` + `bindirs=["bin"]` → 必须有 `commands.json`（已提供）。

## 系统同名库隔离 (G3)

- 单一可执行文件，不产出 `.so`，无 `/lib`、`/lib64` 污染。

## 测试真实性 (R34 / L1e)

- `test_tinyxxd.py` 运行**安装后**的 `bin/tinyxxd`，做实打实的输入/输出比对。
- 移除包目录时测试无法找到二进制而失败，反向验证成立。

## 版本策略 (R37)

- 首次适配使用平台版本 `1.3.16`（上游 tag v1.3.16），conanfile version 与版本目录一致。

## 风险

- 未纳入依赖 ViM `xxd` 作对照的用例；已在 notes/test-report 说明原因。
