# libavif 1.4.2.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 liblibavif.so，供 dlopen 及作依赖。
- 版本 1.4.2.1 为 R37 递增版本：上游源码仍为官方 v1.4.2 发布包，
  配方在本项目 1.4.2 成熟配方基础上重建，无源码差异。

## 关键适配
- OHOS 工具链自发现（ohos.toolchain.cmake，profile [conf] user_toolchain /
  OHOS_NDK_HOME / SDK 布局 glob 三级回退），绕开 conan_toolchain 在
  os=OHOS 下把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035）。
- llvm-ranlib 兜底：OHOS SDK 的 llvm/bin 只有 llvm-ar 没有 llvm-ranlib，
  cmake 造静态库 <AR> qc && <RANLIB> 会 ENOENT；SDK 有就用 SDK 的，否则用 PATH 里的。
- 依赖 preload：`CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 注入 ohos-find-deps.cmake，
  把各依赖 package_folder 加进 CMAKE_FIND_ROOT_PATH/PREFIX_PATH 并把
  FIND_ROOT_PATH_MODE_{PACKAGE,INCLUDE,LIBRARY} 置 BOTH，绕开
  ohos.toolchain 用普通 set()（非 CACHE）压住命令行 cache 变量的 ONLY 限制。
- 解码后端接 dav1d（-DAVIF_CODEC_DAV1D=SYSTEM），关 libyuv/apps/tests/examples/man。
- ELF 签名：lib/ 的 .so 与 bin/ 可执行文件用 llvm-objcopy + binary-sign-tool 自签，
  否则 dlopen/exec 报 Permission denied。
- test_package：C 探针真实调用 avifVersion()/avifCodecName()/avifImageCreate，
  并断言解码后端为 dav1d（证明 DAV1D=SYSTEM 真接上了），7 项断言。

## 状态
built（CI conan create + test 通过，验证通过未 upload）

## 结束
编译结束标记：libavif 1.4.2.1 适配完成，conan-verify 8 道门禁全部通过，
test_package 消费者测试 7 项断言通过，W4 Pre-PR 审计 verdict=pass。
最终状态：built（验证通过未 upload）。
