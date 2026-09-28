# DRAFT-fyba-4.1.1-vpath-relative-include：autotools 子目录 `-I../兄弟` 相对包含在 out-of-source（VPATH）构建下失效

> Contributor: pc4-4 | Status: Draft | Updated: 2026-09-27
> Source: fyba 4.1.1 适配 HarmonyOS PC（task fyba-4.1.1-r01-pc4-4）
> 对应：`knowledge/drafts/DRAFT-fyba-4.1.1-vpath-relative-include.kv`

## 现象

autotools 工程 out-of-source（VPATH，`srcdir != builddir`，conan basic_layout 的标准形态）
编译某子目录时，跨子目录头文件找不到；但同样的源码 in-source 构建（configure 在源码目录运行）全绿：

```console
src/FYBA/fyba.h:88:10: fatal error: 'fygm.h' file not found
 #include <fygm.h>
```

关键线索：上游 `src/FYBA/Makefile.am` 的 `AM_CPPFLAGS` 里有 `-I../GM -I../UT`。

## 根因

`-I../GM` 是**相对当前子目录**（`src/FYBA`）的路径，语义依赖"编译命令在源码树内执行"：

- **in-source 构建**：编译命令在 `src/FYBA/` 执行，`../GM` → `src/GM/`（源码树存在头文件）→ 通过。
- **VPATH/out-of-source 构建**（conan 默认）：configure/make 在 `build-release/` 下运行，编译命令
  实际在 `build-release/src/FYBA/` 执行，`../GM` → `build-release/src/GM/`——构建目录里只有
  编译产物，头文件仍只在源码树 → `fygm.h file not found`。

automake 子目录 Makefile 里 `$(top_srcdir)` 恒指源码根，`-I$(top_srcdir)/src/GM` 在源码树与
构建树两种布局下都能解析到正确的头文件目录。

## 方案（按侵入性从低到高）

1. **补丁改为 `$(top_srcdir)` 相对路径（推荐，最小侵入）**：
   `-I../GM -I../UT` → `-I$(top_srcdir)/src/GM -I$(top_srcdir)/src/UT`
   单列补丁（patch_type: portability），在 PR「文件修改说明」披露。实测 fyba 补丁后
   conan create G2 PASS + W3 本地 CI PASS。
2. 配方改 in-source 构建（`layout(src_folder=".")`）：绕开 VPATH，但非常规，与 conan
   cleanup/产物隔离可能冲突，仅当无补丁空间时使用。

## 验证

```bash
conan create archives/f/fyba/4.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望：三库 libfyba/libfygm/libfyut 编译链接通过，无 'fygm.h file not found'
```

## 适用边界 / 反例

- **适用**：多子目录 autotools 库、Makefile.am 用 `-I../sibling` 引用相邻子目录头文件、out-of-source 构建。
- **反例**：in-source 构建全绿**不能**证明无问题（本模式在 in-source 下因相对路径凑巧成立）；
  单目录库、或子目录引用 `$(top_srcdir)` 的库不命中。
