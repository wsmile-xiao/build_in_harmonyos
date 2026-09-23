# butteraugli 0-20190319 适配笔记

## 编译环境
- 构建系统: makefile（上游 butteraugli/Makefile，无 configure/install）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ (15.0.4) / llvm-ar / llvm-ranlib
- 状态: built

## 编译步骤

```bash
# 依赖：libpng/1.6.58 + libjpeg/10（ohpcd 制品仓已发布；zlib 由 libpng 传递引入）
conan install --requires=libpng/1.6.58 --requires=libjpeg/10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 探索性编译（在源码根目录，-I.. 由 Makefile 提供以解析 butteraugli/butteraugli.h）
cd <src>/butteraugli
make CXX=clang++ CXXFLAGS="-std=c++11 -I.. -I<png_inc> -I<png_inc>/libpng16 -I<jpeg_inc>" \
     LDFLAGS="-L<png_lib> -L<jpeg_lib>" -j1
# → butteraugli.o butteraugli_main.o butteraugli（arm64 ELF 可执行程序）

# 运行验证
LD_LIBRARY_PATH=<png_lib>:<jpeg_lib> ./butteraugli docs/vs_fuzz_left.png docs/vs_fuzz_right.png <tmp>/heat.ppm
# → 2.341576（感知差异得分），热力图 PPM 正常生成（P6 648x360），rc=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 误生成 autotools 模板（configure + AutotoolsToolchain） | 生成器按 init-build 的 build_system 探测结果选择了 autotools 模板，而 butteraugli 上游实际是纯 Makefile | 按 templates/conanfile-makefile.py.tmpl 重写 conanfile.py：build() 直接 `make -C butteraugli`，无 configure 步骤 |
| 2 | `#include "butteraugli/butteraugli.h"` 找不到 | 源码 include 路径是相对源码根目录的 butteraugli/ 子目录，若在 butteraugli/ 目录内编译需 `-I..`（Makefile 已内置） | 编译 cwd 保持源码根目录、用 `make -C <root>/butteraugli`，保留 Makefile 自带 `-I..` |
| 3 | 上游 Makefile 无库归档/install 目标 | butteraugli.o 即库代码，无 libbutteraugli.a | 配方 build() 用 `llvm-ar rcs libbutteraugli.a butteraugli.o && llvm-ranlib` 补归档；package() 手工 copy 头文件/库/可执行程序 |
| 4 | 内存加载依赖库失败（libpng16.so.16 symbol not found） | 运行时未设 LD_LIBRARY_PATH，找不到 conan 缓存中的依赖库 | 探索阶段 LD_LIBRARY_PATH 指向依赖 lib；conan test_package 由 VirtualRunEnv/conanrun 环境自动注入 |
| 5 | /tmp 只读导致热力图写失败 | HMDFS /tmp 只读（E002 已知陷阱） | 输出路径改用 $TMPDIR（/storage/Users/currentUser/tmp） |

## 源码修改

无补丁（patches/ 为空）。上游源码未做任何改动。

## 依赖版本

- libpng/1.6.58（ohpcd 制品仓）
- libjpeg/10（ohpcd 制品仓）
- zlib/1.3.1.1（libpng 传递依赖）

## 验证结果

```bash
# 探索编译产物（初始就绪/usr）：
butteraugli 比较两张官方 docs 图像 → 得分 2.341576，热力图 PPM 生成成功
# conan-verify 八道门禁覆盖（G0-G4 + L2/L4/L5），详见 .ci-result.json / reports
```

## 注意事项

- R33 落实：所有编译器/归档器必须从 Conan conf（tools.build:compiler_executables:*）获取，禁止裸用 ${CC}/${CFLAGS}。
- 版本标识 0-20190319 对应上游 commit 71b18b636b9c7d1ae0c1d3730b85b3c127eb4511（2019-03-19），上游无 tag/release。
- 本库同时产出静态库（libbutteraugli.a，包 butteraugli/butteraugli.h API）与可执行程序（butteraugli CLI → commands.json 已在软件级声明，R38）。
---

**编译结束**: 2026-09-05 18:21
**最终状态**: built
