# DRAFT: OHOS 共享库缺 SONAME 的第二症状 —— install(EXPORT) 打出 IMPORTED_NO_SONAME

> Draft: DRAFT-tdlib-1.8.0-harmonyos-soname-export-imported-no-soname
> 来源：tdlib/1.8.0 适配，CI 等价 W3 的 L5 门禁**同时报 L5a 与 L5c**
> 关系：根因与既有 `DRAFT-libharu-2.3.0-missing-dt-soname` / `E383` / `E330` / `E537` /
> `drafts/E631-draft-9C41` 相同（HarmonyOS 无 CMake 平台模块）。**本条只补两点增量**，
> 建议 **merge-into `DRAFT-libharu-2.3.0-missing-dt-soname`（或 E383）**。

## 增量 1：一个缺失的平台模块，同时污染 ELF 与 CMake 包元数据

```
[ok]   L5: lib/ has content (library package)
[fail] L5a: libtdjson.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
[fail] L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE — 下游必须按完整路径链接
       <pkg>/lib/cmake/Td/TdTargets-release.cmake
[fail] L5: SONAME quality gate failed (2 errors)
```

CMake 的 export 生成器在写 `IMPORTED_*` 时，会依据**同一个** SONAME flag 是否为空来决定
`IMPORTED_SONAME` / `IMPORTED_NO_SONAME`。所以「缺 `Platform/HarmonyOS.cmake`」
不仅让 `.so` 没有 `DT_SONAME`，还让随包导出的 `*Targets-release.cmake` 被打上
`IMPORTED_NO_SONAME TRUE` —— 下游 `find_package` 后只能按完整路径链接，
**CI 的 L5c 门禁会直接判 fail**（既有条目只记了 L5a）。

修复前后对照（同一包）：

| | 修复前 | 修复后 |
|---|---|---|
| `llvm-readelf -d libtdjson.so` | 无 SONAME | `SONAME  libtdjson.so.1.8.0` |
| `TdTargets-release.cmake` | `IMPORTED_NO_SONAME TRUE` | `IMPORTED_SONAME_RELEASE "libtdjson.so.1.8.0"` |
| L5 门禁 | `fail` | `pass` |

## 增量 2：该 flag 用 `tc.cache_variables` 注入**是可行的**（时机与 POLICY 变量相反）

链接规则在 `project()` 之后才求值，因此 toolchain 注入来得及；
这与 `CMAKE_POLICY_VERSION_MINIMUM` 必须走命令行（见
`DRAFT-tdlib-1.8.0-cmake-policy-minimum-toolchain-too-late`）恰好相反——两个「toolchain 里的变量」
一个有效一个无效，判定靠时机而非写法。

```python
def _write_ohos_shared_lib_rules(self, tc):
    for lang in ("C", "CXX"):
        rules = os.path.join(self.generators_folder, f"ohos-shared-lib-rules-{lang.lower()}.cmake")
        save(self, rules, 'set(CMAKE_SHARED_LIBRARY_SONAME_%s_FLAG "-Wl,-soname,")\n' % lang)
        tc.cache_variables[f"CMAKE_USER_MAKE_RULES_OVERRIDE_{lang}"] = rules
```

> 需要 RPATH/`$ORIGIN` 一并补齐时，加 `CMAKE_SHARED_LIBRARY_RUNTIME_*`、
> `_FLAG_SEP`、`RPATH_LINK`、`RPATH_ORIGIN_TOKEN` 等（完整形态与 `cmake --install` 改写
> ELF 破坏 OHOS 签名的坑见 `drafts/E631-draft-9C41`）。tdlib 只需 SONAME 一条，
> 因此产物保持「无 RUNPATH」，`DT_NEEDED` 仅 `libc++_shared.so` / `libc.so`。

## 与既有条目的关系（含框架预审判定）

`draft-review` 输出：`signature=✅ root_cause=✅ rec=✅`，
相似正式条目 TOP3 → E360 0.11、E532 0.10、E140 0.09（全部低于 0.12），
📌 预审建议 **create**（"疑似新知——无高相似条目"）。

> 注意：`draft-review` 只在**正式条目**（`knowledge/graph/`）里找相似项，不比对草稿目录。
> 人工交叉比对另发现同根因的兄弟条目：`E383`（OHOS 共享库缺 SONAME，rec 为窄形态 flag 注入）、
> `E330`（禁版本化 soname 符号链接）、`E537`（DT_NEEDED 绝对路径泄漏）、
> `E631`（rules override 全量形态，**仍是草稿**）、以及草稿
> `DRAFT-libharu-2.3.0-missing-dt-soname`（同根因，只报 L5a）。

- **建议处理方式（两条路，交人工裁决）**：
  1. **merge-into `E383` 或 `DRAFT-libharu-2.3.0-missing-dt-soname`** —— 把本条两点增量
     （L5c/`IMPORTED_NO_SONAME` 第二症状；`tc.cache_variables` 注入时机可行且与
     `CMAKE_POLICY_VERSION_MINIMUM` 相反）并入既有条目，不新增；
  2. **独立成条** —— 若认为「产物 ELF 与它的 CMake 包元数据被同一缺失模块同时污染、且被
     L5a+L5c 双门禁捕获」这一组合症状值得单独检索（工具预审判 create），则保留本条。
