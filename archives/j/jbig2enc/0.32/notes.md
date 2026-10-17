# jbig2enc 0.32 适配笔记

## 编译环境
- 构建系统: autotools（git archive 无 configure，autoreconf -fi 自举）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

1. 依赖：leptonica/1.85.0（制品仓，带六格式链）；tool_requires automake/1.18 + libtool/2.5.4 + pkgconf/3.0.5
2. `conan create archives/j/jbig2enc/0.32 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
3. build() 内部流程：
   - pkg.m4（pkgconf 包内 share/aclocal/pkg.m4）拷入 m4/ → aclocal 拾取 PKG_CHECK_MODULES 宏
   - `autoreconf -fi` 生成 configure（含 config.guess 2023-08-22，原生识别 HarmonyOS）
   - apply 0001 补丁（umask 077→022）
   - `./configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos --enable-static --disable-shared`（PKG_CONFIG_PATH 指向 PkgConfigDeps 生成目录；LD_LIBRARY_PATH 从 LDFLAGS -L 集合回填）
   - `make -j1`（E074：HMDFS jobserver fifo EPERM）
   - `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf: possibly undefined macro: PKG_CHECK_MODULES | CI 无 pkg.m4（PKG_CHECK_MODULES 宏属于 pkg-config 包） | tool_requires pkgconf/3.0.5，build() 把包内 share/aclocal/pkg.m4 拷入 m4/ |
| 2 | cannot run C compiled programs | 交叉编译未声明 --host | AutotoolsToolchain 显式 --host/--build=aarch64-unknown-linux-ohos |
| 3 | cannot run C compiled programs（第二次，conftest 链接 leptonica .so 后运行失败） | conftest 的 NEEDED 库不在加载路径 | 从 LDFLAGS 的 -L 集合回填 LD_LIBRARY_PATH |
| 4 | config.status: could not setup config files machinery (Permission denied) | configure umask 077 在 HMDFS 产生 drwx--S--- 不可写临时目录（E011/E114 类） | 0001 补丁 umask 077→022（liburcu 0003 同款） |
| 5 | aclocal: @am_AUTOM4TE@ failed / automake: autoconf inaccessible | hnp 装的 automake 硬编码绝对路径 | _prepare_autotools_env() 把 AUTOCONF/AUTOM4TE/ACLOCAL 等 env 指向 PATH 实际工具（abiword 同款） |
| 6 | make jobserver mkfifo EPERM | HMDFS fifo 限制（E074） | make -j1 |

## 源码修改

- 无源码修改、无补丁文件。umask 077→022 修复在 conanfile.py build() 里对 autoreconf 生成的 configure 做运行时文本替换（automake 1.17/1.18 生成的 configure 行号有漂移，补丁 hunk 会 miss；abiword-plugin-clarisworks _drop_umask_077 同款），tarball 源码零改动。

## 依赖版本

- leptonica/1.85.0（唯一三方库依赖；configure.ac 全文仅 AC_CHECK_LIB(leptonica) + PKG_CHECK_MODULES(LEPTONICA, lept>=1.74) + AC_CHECK_LIB(m)）
- 上游 subprojects/*.wrap 是 meson wrapdb 镜像清单（leptonica/giflib/libjpeg-turbo/openjpeg/libpng/libtiff/libwebp/zlib-ng），autotools 构建不读取，全部通过 leptonica 传递依赖间接链接
- 不依赖 lcms/jbig2dec（jbig2dec 是解码方向的姐妹件，编码器不需要）

## 验证结果

```bash
# conan create 验证（ohos-aarch64 交叉）
conan create archives/j/jbig2enc/0.32 -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2
# → jbig2enc/0.32: Package created + test_package PASS

# 上游测试等价真跑（meson 注册 basic 测试，src/meson.build:58）
jbig2 -s -a -v images/feyn.tif             # PASS: exit 0 + 74057 字节有效 JB2（\x97JB2 魔数）
# 上游 autotools CI 测试链
jbig2 -a -p -v images/feyn.tif > feyn.jb2  # PASS: 83620 字节 JB2 流
python3 jbig2topdf.py -s feyn.jb2          # PASS: 84469 字节有效 PDF（%PDF-1.4）

# 消费者测试（test_package）
jbig2 test_input.png > out_generic.jbig2   # PASS: \x97JB2 魔数 + 非空
jbig2 -s -p test_input.png                 # PASS: output.sym + output.0000 非空
```

## 交付物

| 文件 | 说明 |
|------|------|
| libjbig2enc.a | 静态库（jbig2enc/jbig2arith/jbig2sym/jbig2comparator 四模块） |
| jbig2 | CLI 工具（bin/，commands.json 声明） |
| jbig2topdf.py | PDF 包装脚本（bin/，上游 make install 自带） |
| jbig2enc.h 等 6 头文件 | include/ |

## 注意事项

- 上游测试口径：N=1（src/meson.build:58 meson 注册 basic 冒烟测试——全树唯一注册测试目标；autotools 无 TESTS、CMake 无 add_test，CI workflow 测试步骤为手工命令非注册目标）→ 已等价真跑 PASS + 消费者测试 3 项兜底
- 2026-09-24 自查修正：初版误报 N=0（漏查 src/meson.build 的 test() 注册），复核上游三套 CI workflow 与三个构建系统后修正为 N=1 并补真跑证据
- 上游 jbig2 工具默认 -static 链接（jbig2_LDFLAGS=-static），包内 jbig2 二进制动态链接 leptonica .so（conanrun 解析）
- 运行 jbig2 需要 LD_LIBRARY_PATH 含 leptonica 依赖链 libdir（conanrun env 自动处理）

---

**编译结束**: 2026-09-23
**最终状态**: built
