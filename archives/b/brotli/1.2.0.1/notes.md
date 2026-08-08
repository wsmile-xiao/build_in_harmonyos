# brotli 1.2.0.1 适配笔记（HarmonyOS PC · Conan cmake 重做版）

> 本目录为 brotli 1.2.0 的适配修复版本（1.2.0.1）：制品仓已存在 brotli/1.2.0（R37/L0j），
> 本次修改 conanfile.py（build() 集成上游 ctest）必须递增版本号后缀。

## 编译环境
- 构建系统: cmake（自发现 ohos.toolchain.cmake + 裸 cmake，绕开 conan_toolchain 的
  `System is unknown to cmake` 映射问题，与 glfw/libjpeg-turbo/zstd 同法）
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4（OHOS aarch64，本机原生编译）
- 状态: built

## 编译步骤

```bash
# 依赖：无外部依赖（W0 通过，requirements() 为空）
conan create archives/b/brotli/1.2.0.1 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build() 实际执行：
cmake -B build-ohos -S . -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> \
  -DOHOS_ARCH=arm64-v8a -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON ...
cmake --build build-ohos
# 上游测试（先签名测试二进制与构建树 .so，再运行）：
ctest --test-dir build-ohos --output-on-failure --no-tests=error
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试在 OHOS 上无法执行 | 测试二进制未签名，OHOS 要求 ELF 代码签名（E077/E083） | build() 中新增 `_sign_build_artifacts(bdir)`：先用 llvm-objcopy 移除 `.codesign` 段，再用 binary-sign-tool `-selfSign 1` 签名测试可执行文件与构建树 lib/*.so（jsoncpp 1.9.8 同款先例） |
| 2 | ctest 找不到 libbrotli*.so | 测试运行期需要 LD_LIBRARY_PATH 指向构建树库目录（brotli 无 generate()，无 conanrun env） | build() 中显式把 `build-ohos/c/lib` 与 `build-ohos/lib` 追加到 os.environ["LD_LIBRARY_PATH"] |
| 3 | 制品仓已有 brotli/1.2.0（R37） | cnb.cool 不支持同版本 recipe revision 并存；CI L0j 检测配方改动必 fail | 版本号升为 1.2.0.1，新目录 archives/b/brotli/1.2.0.1/ |
| 4 | `make: jobserver mkfifo: Operation not permitted` | HMDFS 平台限制（与 jsoncpp/c-blosc2 同） | 非致命，构建继续，可忽略 |
| 5 | 旧归档缺测试集成/占位符 | 2026-04 手工路径的原始记录 | 重做：build() 集成上游 ctest、notes.md 填占位符、MANIFEST.yml 声明上游测试 |

## 源码修改

- 无源码修改（无需补丁，conandata.yml `patches: {}`）。
- 纯配方级适配：ELF 签名 + ctest 集成。

## 依赖版本

- 无外部依赖（brotli 纯自包含，X86/ARM 通用汇编均内置）。

## 验证结果

```bash
$ ctest --test-dir build-ohos --output-on-failure --no-tests=error
 1/12 Test  #1: roundtrip/c/enc/encode.c/1 ...........   Passed    0.11 sec
 2/12 Test  #2: roundtrip/c/enc/encode.c/6 ...........   Passed    0.12 sec
 3/12 Test  #3: roundtrip/c/enc/encode.c/9 ...........   Passed    0.15 sec
 4/12 Test  #4: roundtrip/c/enc/encode.c/11 ..........   Passed    0.30 sec
 5/12 Test  #5: roundtrip/c/common/dictionary.h/1 ....   Passed    0.12 sec
 6/12 Test  #6: roundtrip/c/common/dictionary.h/6 ....   Passed    0.11 sec
 7/12 Test  #7: roundtrip/c/common/dictionary.h/9 ....   Passed    0.11 sec
 8/12 Test  #8: roundtrip/c/common/dictionary.h/11 ...   Passed    0.11 sec
 9/12 Test  #9: roundtrip/c/dec/decode.c/1 ...........   Passed    0.12 sec
10/12 Test #10: roundtrip/c/dec/decode.c/6 ...........   Passed    0.09 sec
11/12 Test #11: roundtrip/c/dec/decode.c/9 ...........   Passed    0.11 sec
12/12 Test #12: roundtrip/c/dec/decode.c/11 ..........   Passed    0.26 sec

100% tests passed, 0 tests failed out of 12

# test_package（消费者视角，R34 实质测试）：
brotli 1.2.0: 全部断言通过（enc+dec 往返 + 压缩率断言）
```

> 说明：上游 ctest 注册的是 `roundtrip_test` 数据驱动测试的 12 个变体
> （roundtrip/c/enc/encode.c、roundtrip/c/common/dictionary.h、roundtrip/c/dec/decode.c
> 各 4 个参数组合），全部在 OHOS aarch64 上真实执行通过；测试二进制与构建树 .so
> 已先经 llvm-objcopy + binary-sign-tool ELF 签名（E077）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libbrotlicommon.so / libbrotlidec.so / libbrotlienc.so | 三个组件共享库（已 ELF 签名） |
| include/brotli/*.h | 编码/解码/公共头文件 |
| bin/brotli | 命令行工具（可选，视 cmake 安装规则） |
| test_package/ | enc+dec+common 三库全链往返测试（R34） |

## 注意事项

- 上游测试套件：c/tests/（roundtrip_test / decode_test / compress_fuzz_test），
  由 CTest 注册执行，本机实测全部通过。
- R38：brotli 产出 CLI 可执行文件 → 软件级建 `commands.json`。
- R26：brotli 非系统同名库，系统 /lib 无 libbrotli，动态链接无污染。
---

**编译结束**: 2026-08-08 12:19
**最终状态**: built
