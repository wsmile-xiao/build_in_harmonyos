# DRAFT: 隐式必需依赖（PNG/APNG）偶合宿主同名库 → 包不自包含

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan|dependency|cmake-find-module|self-contained` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-libjxl-tools-0.11.2-png-required-dependency-pinning.kv`

---

**匹配关键词**：libpng16.so.16, find_package(PNG), PNG_PNG_INCLUDE_DIR, PNG_LIBRARY, ZLIB_LIBRARY, /usr/local, DT_NEEDED, env -i, self-contained, APNG, JPEGXL_BUNDLE_LIBPNG

## 错误签名（error_signature）

```text
Error loading shared library libpng16\.so\.16|Error relocating .*png_.*: symbol not found|Found PNG: .*/usr/local/|DT_NEEDED.*libpng16
```

## 错误摘录（error_excerpt）

```text
$ env -i <pkg>/bin/cjxl --version
Error loading shared library libpng16.so.16: (needed by <pkg>/bin/cjxl)
Error relocating <pkg>/bin/cjxl: png_destroy_read_struct: symbol not found

# conan create 日志（构建期先兆）
-- Found PNG: /storage/Users/currentUser/usr/local/lib/libpng16.so (found version "1.6.43")
```

## 根因（root_cause）

libjxl 的 extras 编解码器**无条件**执行 `find_package(PNG)`（APNG 编解码无条件编译），
即使配方并未声明 libpng。CMake 官方模块 `FindPNG` 先 `find_package(ZLIB)`，再读取缓存变量
`PNG_PNG_INCLUDE_DIR` / `PNG_LIBRARY`；在构建机上这些变量由宿主前缀
（`/storage/.../usr/local`，装有自建 libpng 1.6.43）满足 → `cjxl`/`djxl` 得到
`DT_NEEDED libpng16.so.16`，而包内 `lib/` 未随附 → 仅当宿主 `LD_LIBRARY_PATH` 存在时才能运行。

## 推荐方案（rec_approach: `declare-and-pin-find-modules`）

1. `requirements()` 显式声明被隐式依赖的库：`self.requires("libpng/1.6.58")`（传递 `zlib/1.3.1.1`）。
2. `generate()` 用 `tc.cache_variables` 把官方 Find 模块钉到 Conan 包内实际文件：
   `PNG_PNG_INCLUDE_DIR` / `PNG_LIBRARY` / `ZLIB_INCLUDE_DIR` / `ZLIB_LIBRARY`。
3. `package()` 把 `libpng16.so*` 复制进包内 `lib/`，保持 `$ORIGIN/../lib` RPATH。
4. `test_package` 增加 `env={}` 空环境往返断言 —— 这是能捕获该类缺陷的关键检查
   （仅用 `env="conanrun"` 会被注入的宿主 `LD_LIBRARY_PATH` 掩盖）。

**验证**：`env -i "<pkg>/bin/cjxl" --version` 必须 rc=0 且无 `Error loading shared library`；
构建日志 `Found PNG:` 必须指向 Conan 包路径。

**替代方案**：`JPEGXL_BUNDLE_LIBPNG=ON`（让上游自带 libpng，代价是构建期多一次第三方下载构建）。

---

*本文件由同名 `.kv` 字段派生生成（kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
