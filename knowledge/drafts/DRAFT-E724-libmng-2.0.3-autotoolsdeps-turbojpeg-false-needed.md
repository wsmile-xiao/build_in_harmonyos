# DRAFT-E724-libmng-2.0.3-autotoolsdeps-turbojpeg-false-needed — AutotoolsDeps 双组件包把未用组件内联进 NEEDED

> **Contributor**: atomcode-executor | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: medium | **Category**: conan / autotools / loading / ohos

## 问题签名

```text
$ readelf -d .libs/libmng.so.2.0.2 | grep NEEDED
 (NEEDED)  Shared library: [libturbojpeg.so.0]     ← 源码 0 引用的假依赖
 (NEEDED)  Shared library: [libz.so]
 (NEEDED)  Shared library: [libjpeg.so.62]
 ...
运行期（目标机无 turbojpeg）:
Error loading shared library libturbojpeg.so.0 (needed by ./consumer)
```

## 根因

conan 2 `AutotoolsDeps` 生成器按 pkg-config **组件名**展开 LIBS。多组件包
libjpeg-turbo 提供 `libjpeg` + `turbojpeg` 两个组件，整体内联进
`LIBS="-llcms2 -ljpeg -lturbojpeg -lz ..."`。

上游 configure.ac 用 `AC_CHECK_LIB` 探测 jpeg/lcms2 时，conftest 链接命令
**前缀已带整串污染 LIBS**——任何函数探测"成功"都被 -lturbojpeg 兜底，
探测结果无法反映真实闭包。LIBS 原样写入 Makefile 后，libtool 逐个 -l
链接，假依赖固化进 NEEDED。

- libmng 源码 `grep -rn turbojpeg` **0 命中** → 纯生成器假象；
- E467 是同根因的另一症状（configure 探测期 conftest 加载失败 rc=77），
  本条是污染固化进成品 NEEDED 的症状；修法共通：都不吃 AutotoolsDeps
  的 LIBS。

## 修复（manual-flags-unset-libs）

配方 `generate()`（elfutils 先例）：

1. **不用 AutotoolsDeps**；遍历 `self.dependencies` 手拼
   `CPPFLAGS(-I)` / `LDFLAGS(-L)`——只给路径，不给 -l 库名；
2. `os.environ.pop("LIBS", None)` 清空污染；
3. 鸿蒙 PC 构建机即目标机时，configure 运行期探测（AC_CHECK_LIB 的
   conftest 要加载依赖 .so）需 `LD_LIBRARY_PATH` 指向各依赖包 lib/；
4. configure 的 AC_CHECK_LIB 自行探测出干净 `LIBS=-lz -ljpeg -llcms2`。

构建后 `readelf -d` 验证 NEEDED 恰好
`{libz.so, libjpeg.so.62, liblcms2.so.2, libc.so}`。

## 证据链（feat/libmng-2.0.3）

- 污染复现：source AutotoolsDeps 生成脚本后构建，readelf -d 含
  `NEEDED [libturbojpeg.so.0]`；
- 源码审计：`grep -rn turbojpeg libmng-2.0.3/` 0 命中；
- 修复验证：conan create 后 NEEDED 恰好 4 项；
- test_ohos H2 双断言（闭包精确匹配 + 无 turbojpeg）通过，10/10。

## 适用边界

仅适用于上游 configure 用 AC_CHECK_LIB 自行探测依赖的场景。若上游
硬编码 LIBS 或用 `pkg-config --libs` 取组件名，需改上游或接受组件闭包。

## 验证命令

```bash
conan create archives/l/libmng/2.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
readelf -d <pkg>/lib/libmng.so.2 | grep NEEDED   # 期望无 turbojpeg
```
