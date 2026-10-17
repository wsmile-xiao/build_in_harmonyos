# DRAFT-raw-makefile-shared-lib-soname-patch — 纯 Makefile 手写链接行缺少 DT_SONAME，应在 Makefile 链接规则内补 -Wl,-soname（补丁形态）

- 触发事件：complete-striped-smith-waterman 1.2.5 适配，W3 本地 CI 的 L5 SONAME 门禁失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-raw-makefile-shared-lib-soname-patch

## 现象

W3 本地 CI（build_and_test.sh）L5 SONAME 质量门禁失败：

```
[fail] L5a: libssw.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
       文件: /lib/libssw.so
[fail] L5: SONAME quality gate failed (1 errors)
```

`readelf -d libssw.so` 动态段无 `(SONAME)` 条目。同一链接行在 Linux 上
曾被上游长期使用（Makefile 手写 `$(CC) $(CFLAGS) -fPIC -shared -rdynamic -o $@ $<`），
但门禁按可链接共享库必须有「相对路径 DT_SONAME」为硬性质量要求。

## 根因

上游为纯 Makefile 项目（无 configure/CMake/Meson），共享库链接规则是手写裸链接：

```make
$(LIB): ssw.c ssw.h
	$(CC) $(CFLAGS) -fPIC -shared -rdynamic -o $@ $<
```

链接命令行从未传递 `-Wl,-soname,<libname>`；与既有 CMake 场景（E383 /
DRAFT-cmake-harmonyos-platform-soname-flag：CMake 4.x 无 Platform/HarmonyOS.cmake
导致 `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 为空）**触发面不同**——
此处与 CMake 平台模块完全无关，是上游 Makefile 自身链接行就不带 soname；
L5 门禁对纯 Makefile 构建的 .so 同样生效。

## 修复（补丁形态，本轮真实验证）

在 `patches/*.patch` 中给 Makefile 共享库链接行追加 `-Wl,-soname,<libname>.so`：

```patch
 $(LIB): ssw.c ssw.h
-	$(CC) $(CFLAGS) -fPIC -shared -rdynamic -o $@ $<
+	$(CC) $(CFLAGS) -fPIC -shared -rdynamic -Wl,-soname,libssw.so -o $@ $<
```

conandata.yml `patches:` 段声明该补丁（patch_type: portability），
`apply_conandata_patches(self)` 在 build() 应用。验证：

```bash
readelf -d $PKG_CACHE/lib/libssw.so | grep SONAME   # → [libssw.so]
# W3 重跑 L5_RESULT=pass
```

## 适用边界 / 反例

- 适用：纯 Makefile / 手写链接规则的共享库，L5 门禁失败且 readelf 确认无 DT_SONAME；
  与包名一致的裸 SONAME（`libxxx.so`）即满足「相对路径」要求（门禁仅禁绝对路径）。
- 反例 / 不适用：CMake 工程（走 E383 / DRAFT-cmake-harmonyos-platform-soname-flag
  的 conan flag 方案）；上游本就用 versioned SONAME（libfoo.so.0）时无需裸名；
  纯静态库（无 .so 无此门禁）。
- 注意：补丁 hunk 计数必须与真实文件一致（git diff 生成，勿手写行数），
  conan apply_conandata_patches 对 hunk 头行数敏感（-24,7 与内容行数不符 →
  "patch stream is incomplete"）。

## 与既有条目关系

- similar_to E383（CMake 场景 SONAME flag 注入）、DRAFT-cmake-harmonyos-platform-soname-flag
- caused_by L5 SONAME 质量门禁 + 上游 Makefile 链接行无 soname
- 无 conflicts_with；prerequisite_of 无