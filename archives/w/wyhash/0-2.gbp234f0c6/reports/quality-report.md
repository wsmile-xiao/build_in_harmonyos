# 质量报告 — wyhash 0-2.gbp234f0c6

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ header-library，settings 四项齐全，`no_copy_source` |
| `conandata.yml` | ✅ 官方 GitHub commit 归档 URL + sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()` |
| `test_package/test_wyhash.cpp` | ✅ 22 项断言，真实调用被测 API |
| `test_package/MANIFEST.yml` | ✅ `assertion_count = 22` |
| `test_package/CMakeLists.txt` | ✅ 通过安装后的 CMake target 链接 |

## 产物 (G4)

- `include/wyhash.h`、`include/wyhash32.h`、`include/o1hash.h`
- `licenses/LICENSE`
- 纯头文件库：无 `bin/`、无 `lib/`，因此不需要 `commands.json`（R38）。

## 系统同名库隔离 (G3)

- 无编译产物，不产生 `.so`，不存在 `/lib`、`/lib64` 污染风险。

## 测试真实性 (R34 / L1e)

- `test_package` 通过 `find_package(wyhash)` + `wyhash::wyhash` 使用安装后的包。
- 移除/破坏包目录时测试无法编译或断言失败，反向验证成立。
- 上游 `test_vector.cpp` 单独编译运行，输出与基线严格比对。

## 版本策略 (R37)

- 首次适配使用上游快照版本 `0-2.gbp234f0c6`，与任务版本一致。
- conanfile 中 `version` 与版本目录名一致（L0m/PF8）。

## 风险

- 仅绑定提交 `234f0c6`；与上游 master（final-4）输出不兼容，已在 notes.md 说明。
