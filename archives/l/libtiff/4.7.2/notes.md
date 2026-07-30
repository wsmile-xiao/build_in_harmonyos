# libtiff 4.7.2 编译笔记（HarmonyOS PC · Conan cmake）

## 产物
`libtiff.so`、`libtiffxx.so`（C++ 封装）。

## 编解码后端
八个后端全部接入，均由 conan 依赖提供（不依赖设备上预装的系统库）：

| 后端 | CMake 开关 | 依赖包 |
|------|-----------|--------|
| zlib | `-Dzlib=ON` | zlib/1.3.1.1 |
| libdeflate | `-Dlibdeflate=ON` | libdeflate/1.25 |
| JPEG | `-Djpeg=ON` | libjpeg-turbo/3.2.0 |
| Zstd | `-Dzstd=ON` | zstd/1.5.7 |
| WebP | `-Dwebp=ON` | libwebp/1.6.0 |
| LERC | `-Dlerc=ON` | lerc/4.1.1 |
| JBIG | `-Djbig=ON` | jbigkit/2.1 |
| LZMA | `-Dlzma=ON` | xz/5.6.2 |

## 关键适配
- 关掉不需要的构建目标：`-Dtiff-tools=OFF -Dtiff-tests=OFF -Dtiff-docs=OFF -Dtiff-contrib=OFF`。
- 产物 `.so` 经 `llvm-objcopy --remove-section .codesign` 去旧签名后由
  `binary-sign-tool sign -selfSign 1` 自签（HarmonyOS XPM 拒绝未签名/被改动的 ELF）。
- 无源码补丁。

## 状态
built —— 真机 `conan create` 通过。

## 待改进：test_package 目前是空壳
现有 `test_package/test.c` 只做 `dlopen` + `dlsym("TIFFOpen")`，
**既没有真实读写断言，也没有验证上表任何一个编解码后端确实可用**。
也就是说：八个后端全开只是**构建配置**层面的事实，运行期是否真能用未被测试覆盖。

按本仓其他配方的做法（geos / elfutils / musl-* 等均为真实断言），
这里应改为直接链接 `libtiff` 并逐后端断言：
用各 `COMPRESSION_*` 写一张小图再读回、比对像素。改动需在真机复验后另提。
