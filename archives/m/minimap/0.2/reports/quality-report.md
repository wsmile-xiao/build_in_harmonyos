# 质量报告 — minimap 0.2

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ 含 source/build/package/package_info/export_sources/apply_conandata_patches |
| `conandata.yml` | ✅ 官方 codeload tag v0.2 URL + sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_minimap.py` | ✅ CLI 4 项检查 |
| `test_package/test_minimap_consumer.c` | ✅ 链接安装后的库并运行 |
| `test_package/MANIFEST.yml` | ✅ 上游无测试声明 + `assertion_count = 5` |
| 软件级 `commands.json` | ✅ 工具类型（R38） |

## 依赖 (R36)

- `self.requires("zlib/1.3.1")`；zlib/1.3.1 已在制品仓发布。

## 产物 (G4)

- `bin/minimap`、`lib/libminimap.a`、`include/{minimap.h,bseq.h,kseq.h}`、
  `share/man/man1/minimap.1`、`licenses/LICENSE.txt`
- CLI 包：`package_type="application"` + `bindirs=["bin"]` → 提供 `commands.json`。

## 测试真实性 (R34 / L1e)

- CLI 测试运行**安装后**的 `bin/minimap`；库测试链接**安装后**的 `libminimap.a`。
- 移除包目录时两者都会失败，反向验证成立。

## 版本策略 (R37)

- 首次适配使用平台版本 `0.2`（上游 tag v0.2）。

## 风险

- 上游无测试；功能测试使用合成数据（已在 notes/test-report 说明）。
