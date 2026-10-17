# libaribcaption 1.1.2 适配笔记

## 1. 调研

- 上游: https://github.com/xqq/libaribcaption (xqq, MIT)
- 源码: v1.1.2 tar.gz, SHA256 `649b50bde99272b97c66af2a8400163e2f84eae072d252daa26baaaf0866a1c2`
- CMake ≥ 3.28 (本地 4.1 满足)
- 选项: `ARIBCC_BUILD_TESTS`(OFF), `ARIBCC_SHARED_LIBRARY`(OFF), `ARIBCC_NO_RENDERER`(OFF), `ARIBCC_USE_FONTCONFIG/FREETYPE/EMBEDDED_FREETYPE`(ON)
- 库目标 `aribcaption`, 安装 targets + `libaribcaption.pc`
- OHOS 走 CMake else 分支(非 ANDROID/APPLE/WIN32) → fontconfig + freetype 渲染后端

## 2. 关键决策

| 问题 | 决策 | 依据 |
|---|---|---|
| find_package 找不到 conan 包 | patch 改 CONFIG 模式 + 设置 `${FREETYPE_LIBRARIES}`/`${Fontconfig_LIBRARIES}` 为 conan target | 交叉根下内置 Find 模块失败;SDL2_ttf patch 先例 |
| SONAME 缺失 | `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"]="-Wl,-soname,"`(尾逗号,CMake 拼 target 名) | 实证: 注入完整 flag 会产生 `libaribcaption.solibaribcaption.so`;不注入则 NEEDED 记录相对路径 `../../libaribcaption.so` |
| 上游测试无 ctest | conanfile `build()` 里逐 target build + `self.run()` | 上游测试全部 EXCLUDE_FROM_ALL;TEST_QUALITY_SPEC 要求 test() 有 self.run() |
| 测试编译失败(DrawChar) | patch 0006/0007 补 `aspect_ratio` 参数 | 上游 v1.1.2 tag 的 test 代码滞后于库代码(tag 后 commit 改了签名),上游自身 bug |
| caption2srt/ffmpeg 测试 | `ARIBCC_SKIP_FFMPEG_TESTS` 跳过 | 需外部 MPEG-TS 样本(argv 传入)+ avcodec/avformat,仓库不携带 |
| 共享库下部分测试不可链接 | 共享模式只跑 test_decode/test_capi;test_alphablend/drcs/fontconfig_freetype 仅静态 | Canvas/Bitmap 等内部类无 ARIBCC_API,共享库 `CXX_VISIBILITY_PRESET hidden` 隐藏符号——上游设计如此 |
| musl 拒载 conan 依赖库 | 运行时闭包: 按 SONAME 复制依赖 .so + `binary-sign-tool` 签名 + LD_LIBRARY_PATH | 实证: 链接期 `-Wl,--code-sign` 的空签名不足以被 musl 加载器映射;签过的库可正常加载 |
| 字体环境 | 生成 fonts.conf: `/system/fonts` + 可写缓存 + Hiragino/YuGothic/Rounded M+ → Noto Sans CJK JP 别名 | /system/fonts/NotoSansCJK-Regular.ttc 含 JP/KR/SC/TC/HK face(ftprobe 实证假名+汉字字形齐);无别名时 fontconfig 回落到 Warang Citi,假名缺字 → DrawChar error 2 |
| libpng 依赖位置 | `test_requires`(host context) | CMakeDeps 不生成 tool_requires 的 config 包;astlib/gtest 先例 |
| build profile | 本机用 `ohos-aarch64-dev`(编译器在 ~/usr/local/bin);CI 用 `ci/conan/profiles/ohos-aarch64`(/data/service/hnp/bin) | CI worker 与本机工具链路径不同;CI 上 pr:b=pr:h 全交叉自举,无 x86_64 build 依赖 |

## 3. 上游测试执行情况(实测)

- 定义: 8 个测试目标(alphablend/capi/caption2srt/decode/drcs/ffmpeg/fontconfig_freetype + png_writer/stopwatch/sample_data 为辅助库)
- 可执行(无外部样本): 5 个 — test_alphablend、test_decode、test_capi、test_drcs、test_fontconfig_freetype
- 实际执行与通过:
  - 静态包: 5/5 全部通过(exit 0)
    - test_alphablend: count=1000, average=4.431ms
    - test_decode: 解码出日文文本
    - test_capi: PNG 比对通过
    - test_drcs / test_fontconfig_freetype: 渲染 + PNG 比对通过(字体经 fonts.conf 别名到 Noto Sans CJK JP)
  - 共享包: 2/2(test_decode、test_capi)——其余 3 个依赖共享库隐藏的内部符号(上游设计),仅静态可链接
- 排除: caption2srt、ffmpeg(需外部 MPEG-TS 样本,上游不携带)

## 4. 消费者测试(test_package, 实测通过)

- test_package (C API): sample_data_1 解码 GOT_CAPTION + 文本非空;sample_data_drcs_1 DRCS map 非空;NULL/truncated/garbage 输入不崩溃、不产出字幕(ERROR/NO_CAPTION)
- test_cpp_api (C++ API): Decoder::Initialize + Decode + Caption::text(std::string, 有效 UTF-8) + regions 非空 + drcs_map size=3

## 5. 鸿蒙测试(harmonyos-test/run.sh, 实测全过)

- ELF: AArch64 machine ✓、DT_SONAME=libaribcaption.so(相对)✓、DT_NEEDED 含 libaribcaption.so ✓、`.codesign` 段(binary-sign-tool 签名后 readelf -S)✓
- 运行: uname machine=aarch64 sysname=HarmonyOS ✓、`__MUSL__` ✓、真实解码 status=2 文本非空 ✓

## 6. CI 门禁(scoped, 实测)

`CI_PACKAGES="archives/l/libaribcaption/1.1.2" zsh ci/conan/build_and_test.sh` → exit 0:
- L0/JC/G0: pass(配方完整性、垃圾文件、知识图谱)
- L1: pass(test_package 执行)
- L1e: pass(负向验证——真实依赖)
- L4: pass(patch 干净)
- L5: pass(SONAME 相对路径等)
- 本机跑法: `CONAN_PROFILE=ohos-aarch64-dev`(本机工具链);CI worker 用默认 `ohos-aarch64`

## 7. 遗留

- 无
