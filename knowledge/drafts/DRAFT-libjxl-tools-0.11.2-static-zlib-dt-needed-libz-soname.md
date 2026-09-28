# DRAFT: 已发布共享库 DT_NEEDED 为无 SONAME 的 libz.so，而依赖仓只提供静态 libz.a

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan|dependency|soname|self-contained` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-libjxl-tools-0.11.2-static-zlib-dt-needed-libz-soname.kv`

---

**匹配关键词**：libz.so, libz.so.1, DT_NEEDED, SONAME, libpng16.so.16, libz.a, static-only, --whole-archive, env -i, zlib

## 错误签名（error_signature）

```text
Error loading shared library libz\.so|needed by .*libpng16\.so\.16|no loader default path provides libz\.so
```

## 错误摘录（error_excerpt）

```text
$ readelf -d <pkg>/lib/libpng16.so.16 | grep NEEDED
  (NEEDED)  Shared library: [libz.so]        # 注意：无版本号，即无 SONAME

$ ls /usr/lib/libz*
/usr/lib/libz.so.1  /usr/lib/libz.so.1.2.13  # 系统不提供名为 libz.so 的文件
```

## 根因（root_cause）

制品仓的 `zlib/1.3.1.1` 仅产出**静态** `lib/libz.a`；而已发布的 `libpng/1.6.58` 的共享库
`libpng16.so.16` 其 `DT_NEEDED` 记录为不带版本号的 `libz.so`（上游 libpng 链接宿主 libz 时未写入
SONAME）。OHOS 系统运行时只提供 `/usr/lib/libz.so.1`，不存在名为 `libz.so` 的文件 → 干净环境下
`libpng16.so.16` 载入失败，`cjxl`/`djxl` 报 `Error loading shared library libz.so`。

## 推荐方案（rec_approach: `synthesize-shared-lib-from-static-archive`）

静态库已带 `-fPIC` 时，可在 `package()` 中用一次最小链接调用把 `libz.a` 整体打包成
SONAME 为 `libz.so` 的共享库，与 `libpng16.so*` 一并放入包内 `lib/`，由 `$ORIGIN/../lib`
RPAIH 解析：

```bash
"<cc>" -shared -fPIC -Wl,-soname,libz.so \
  -o <pkg>/lib/libz.so \
  -Wl,--whole-archive <zlib_pkg>/lib/libz.a -Wl,--no-whole-archive
```

既与配方所链接的 zlib 版本一致，又**不向系统 `/lib`、`/lib64` 安装任何同名库**
（不污染系统运行时，符合 R26 初衷）。

**验证**：`env -i "<pkg>/bin/cjxl" --version` rc=0；`readelf -d <pkg>/lib/libz.so` 显示 SONAME。

**替代方案**：包内软链 `libz.so -> /usr/lib/libz.so.1`（削弱自包含性，不推荐）。

---

*本文件由同名 `.kv` 字段派生生成（kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
