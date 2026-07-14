# jbigkit 2.1 编译笔记（HarmonyOS PC · 手写 Makefile 静态库）

## 定位
- JBIG-KIT（ITU-T T.82 无损图像压缩）；libtiff 的 **JBIG codec 依赖**。
- 产出 **静态库 libjbig.a** + 头 `jbig.h`/`jbig_ar.h`。`package_info.libs = ['jbig']`，无外部依赖。

## 为什么手写（生成器不支持）
jbigkit 用**手写 Makefile**（非 cmake/autotools/meson），`conan_packager gen` 只支持那三种，故本配方**全手写**。

## 关键适配（build()）
- **CMakeLists 无**：`libjbig/` 下 `make libjbig.a`（jbig.o + jbig_ar.o → `ar rc` 归档）。
- **ar/ranlib 硬编码**：`libjbig/Makefile` 里是字面 `ar rc` / `ranlib`（非 `$(AR)`/`$(RANLIB)`），OHOS 无 gnu ar，
  build() 里 sed 成 `/data/service/hnp/bin/llvm-ar` / `llvm-ranlib`。
- **CC**：走 conan conf `tools.build:compiler_executables`（hnp clang）；**CFLAGS 命令行覆盖**为 `-fPIC -O2`
  （静态库要能链进 libtiff.so 等共享库，缺 -fPIC 会 `R_AARCH64 relocation` 报错）。
- 只编 `libjbig.a`，跳过 `libjbig85.a`（T.85，libtiff 不用）和 `tstcodec` 测试程序。
- **静态库无 .so → 无需代码签名**；test_package 走 **link+run**（`find_package(JBIG)` + 调 `jbg_dec_init`），非 dlopen。

## 待真机验证
配方已手写完，**尚未真机 `conan create`**。风险点：hnp 有无 gnu `make`；`llvm-ar` 归档静态库是否正常；
jbig.c 老 C 代码在 clang 下编译告警（非 -Werror，应无阻）。验证：离线源码 + 裸 `conan create -pr ohos-native`
+ test_package link+run。

## 状态
**built（真机已验）** — 2026-07-11 PC 2in1 (SDK 26.0.0.18) 裸 conan create -pr ohos-native 通过：make libjbig.a（llvm-ar 归档）+ test link+run jbg_dec_init，产物 libjbig.a 静态含 jbg_dec_init 符号。