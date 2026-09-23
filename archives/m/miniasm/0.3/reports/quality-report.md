# 质量报告 — miniasm 0.3

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ 含 source/build/package/package_info/export_sources/apply_conandata_patches |
| `conandata.yml` | ✅ 官方 codeload tag v0.3 URL + sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_miniasm.py` | ✅ 6 项检查，运行安装后的二进制 |
| `test_package/MANIFEST.yml` | ✅ 声明上游无测试 + `assertion_count = 6` |
| 软件级 `commands.json` | ✅ 工具类型（R38） |

## 依赖 (R36)

- `self.requires("zlib/1.3.1")`；zlib/1.3.1 已在制品仓发布。

## 产物 (G4)

- `bin/miniasm`（0755）、`share/man/man1/miniasm.1`、`licenses/LICENSE.txt`
- CLI 包：`package_type="application"` + `bindirs=["bin"]` → 提供 `commands.json`。

## 测试真实性 (R34 / L1e)

- `test_miniasm.py` 运行**安装后**的 `bin/miniasm`，构造真实 PAF 并检查 GFA/PAF/BED 输出。
- 移除包目录时测试无法找到二进制而失败，反向验证成立。

## 版本策略 (R37)

- 首次适配使用平台版本 `0.3`（上游 tag v0.3）。

## 风险

- 上游无测试；功能测试使用合成数据（已在 notes/test-report 说明）。
