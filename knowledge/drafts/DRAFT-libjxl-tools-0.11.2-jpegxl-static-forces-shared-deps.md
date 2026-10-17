# DRAFT: JPEGXL_STATIC=ON 强制 -static 与共享依赖冲突

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan|cmake|static-link|shared-dependency` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-libjxl-tools-0.11.2-jpegxl-static-forces-shared-deps.kv`

---

**匹配关键词**：JPEGXL_STATIC, -static, EXE_LINKER_FLAGS, brotli, BUILD_SHARED_LIBS, lld, static link of dynamic object, libjxl, RPATH, $ORIGIN/../lib

## 错误签名（error_signature）

```text
JPEGXL_STATIC.*-static|ld\.lld: error: attempted static link of dynamic object|unable to find library -lbrotli|attempted static link of dynamic object
```

## 错误摘录（error_text_excerpt）

```text
ld.lld: error: attempted static link of dynamic object '.../libbrotlienc.so'
```

## 根因（root_cause）

libjxl 的 `JPEGXL_STATIC=ON` 会向 `EXE_LINKER_FLAGS` 追加 `-static`，强制整个可执行文件
（含所有传递依赖）静态链接；当某个 Conan 依赖（如 `brotli/1.2.0`）配方仅产出共享库 `.so` 时，
lld 拒绝把动态对象静态链接而报错。该选项语义为「产出全静态可执行」，与「外部依赖以共享
形式提供」的制品仓现实直接冲突。

## 影响范围（affected_scope）

任何提供 EXE 全静态开关、但依赖链中存在共享库（.so-only）配方的 CMake 项目；
libjxl-tools/0.11.2（依赖共享 `brotli/1.2.0`）实测受影响。

## 推荐方案（rec_approach: `keep-in-tree-static-but-shared-deps-dynamic`）

1. `BUILD_SHARED_LIBS=OFF` 保留内建 libjxl 静态，**但 `JPEGXL_STATIC=OFF`**，让外部依赖保持共享。
2. `package()` 把共享依赖的 `.so`（及其间接需要的运行时库）复制进包内 `lib/`。
3. 烘焙 `CMAKE_INSTALL_RPATH` / `CMAKE_BUILD_RPATH = $ORIGIN/../lib`，使工具自包含可运行。
4. 随包 `.so` 与二进制一并进行 OHOS 签名。

**验证**：`conan create` 链接阶段无 `attempted static link of dynamic object`；
`readelf -d <pkg>/bin/<tool> | grep NEEDED` 的共享依赖均能在包内 `lib/` 解析；
`env -i <pkg>/bin/<tool> --version` 可运行。

**替代方案**：若确实需要全静态可执行，必须让所有传递依赖都以静态库形式提供（需制品仓提供
`.a` 变体或改为上游内置构建），代价是依赖体积、许可与升级维护成本上升。

**禁则**：不得以篡改生成文件/链接标志（`sed ...EXE_LINKER_FLAGS`、手动 strip `-static`）
的方式绕过错误 —— 不可复现，且违反 R6 / R15。

---

*本文件由同名 `.kv` 字段派生生成（kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
