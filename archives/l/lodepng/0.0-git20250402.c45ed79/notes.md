# lodepng 0.0-git20250402.c45ed79 适配笔记

## 上游调查（commit c45ed7951fb9df607351013d288d71faef6eea87，2025-04-02）

- 仓库：https://github.com/lvandeve/lodepng
- 提交信息："unittest fixes"（仅改 lodepng_unittest.cpp：版权年 2024→2025，修复 testSize/testColorConvert2 索引笔误）
- 源码归档：`https://github.com/lvandeve/lodepng/archive/c45ed7951fb9df607351013d288d71faef6eea87.tar.gz`
- sha256：`ebc4de0d21f7f8c375a17bbe4b0947a5e0b08953a4708c1268e5db7260057506`（261702 字节，已实测下载验算）
- 许可：Zlib（LICENSE 文件原文为类 Zlib 宽松许可）
- 语言：C（C90 兼容）+ C++ 便利封装同源文件
- 版本串：`LODEPNG_VERSION_STRING = "20241228"`（源码内嵌，非 git tag）
- 外部依赖：无（zlib/deflate 自实现，不链接系统 zlib；benchmark/showpng 需 SDL2，仅开发工具）

### 源码结构

```
lodepng.cpp / lodepng.h      库本体（被测物，约 2000+ 行头文件文档）
lodepng_unittest.cpp         上游自包含单测（4001 行，doMain 调用 38 个测试组）
lodepng_util.cpp / .h        单测依赖的工具源（chunk 读写辅助）
lodepng_benchmark.cpp        基准工具（需 SDL2，本配方未接入）
lodepng_fuzzer.cpp           模糊工具（需 libFuzzer，本配方未接入）
pngdetail.cpp                调试工具（本配方未接入）
Makefile                     仅构建 unittest/benchmark/pngdetail/showpng，无库安装目标
examples/                    C/C++ 用例（含编解码/SDL/OpenGL 示例）
```

### 上游测试清点（写入申报表）

| 项目 | 数量 | 来源 |
|------|------|------|
| gtest TEST/TEST_F | 0 | 全树无 gtest 引用 |
| pytest def test_ | 0 | 无 Python 测试 |
| ctest 注册 | 0 | 无 CMakeLists，无 CTestTestfile |
| make check 目标 | 0 | Makefile 无 check 目标，仅 unittest/benchmark/pngdetail/showpng |
| 自包含 unittest 二进制 | 1 | lodepng_unittest.cpp → ./lodepng_unittest |
| doMain 测试组 | 38 | doMain() 函数体逐行计数（PNG 16 + 颜色 13 + zlib 7 + 工具 2，testFewColors 非 DISABLE_SLOW 全量） |
| tests/ 目录 | 0 | 无独立测试目录 |

PNG 固定向量全部 base64 内嵌于单测源码（如 testPngSuite 的 basi0g*.png），无外部数据文件依赖；
doMain 未调用 testDisk*（需外部文件），全部 38 组离线可跑。

## 编译环境

- 构建系统：custom（编译器直驱，无上游构建系统可复用）
- 编译日期：2026-09-18
- 编译器：clang 15 / 目标 aarch64-linux-ohos
- profile：ci/conan/profiles/ohos-aarch64
- 状态：built（待真机预检回填实测证据后由 HMBS 统一提交）

## 编译步骤

```bash
# 库（静态默认；shared=True 时走 -shared 分支产出 liblodepng.so）
c++ -O2 -fPIC -c lodepng.cpp -o lodepng.o
llvm-ar rcs liblodepng.a lodepng.o && llvm-ranlib liblodepng.a
# 上游测试（等价于 Makefile 的 unittest 规则，但跳过需 SDL2 的 benchmark/showpng）
c++ -O2 -I. lodepng.cpp lodepng_util.cpp lodepng_unittest.cpp -o lodepng_unittest
./lodepng_unittest
# 安装
# include/lodepng.h + lib/liblodepng.a(.so) + licenses/LICENSE + hmbs_upstream_result.json
```

编译器/归档器按 E392 从 `tools.build:compiler_executables` 字典获取，
`build()` 内无任何 CC/CFLAGS 系 shell 裸变量（R33 合规）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无库构建目标，Makefile 只产出开发工具 | lodepng 设计为源码级集成（README："No library is necessary"） | 配方直编 `lodepng.cpp → liblodepng.a/.so`，头文件原样安装；消费者走常规 `find_package(lodepng)` |
| 2 | 上游 `main()` 失败仍返回 0，退出码无法判负 | `catch(...){ cout << "*** TEST FAILED ***"; } return 0;` | `_run_upstream_tests` 解析 stdout：必须同时含 `testPngSuite` 进度与 `test successful`，且无 `*** TEST FAILED ***`/`caught error!` 才判 passed；输出缺失横幅即判 failed 并抛异常阻断构建 |
| 3 | `tools.build:compiler_executables` 取值方式 | OHOS profile 存字典，直接取子键在部分 conan 版本报错（E392） | `_tool()` 先整体 `check_type=dict` 取键，再回退子键形式，最后回退 PATH 名 |
| 4 | benchmark/showpng 需 SDL2 | 上游 Makefile 的 benchmark/showpng 链接 `-lSDL2` | 仅构建运行 `unittest`（PNG/颜色/zlib/工具全覆盖），benchmark/fuzzer/pngdetail 工具不接入；在 MANIFEST 审计中如实声明 |

## 源码修改

无补丁。上游单源文件在 OHOS aarch64 下无需移植修改。

## 依赖版本

- 无外部依赖（纯 C/C++，仅 libc/libc++；zlib 自实现）

## test_package 验证内容

消费者测试 `test_lodepng.cpp` 实质验证编解码能力（5 组）：

1. `LODEPNG_VERSION_STRING == "20241228"`（版本身份，证明链的是本包快照）
2. `lodepng::encode` 返回 0 且产出标准 PNG 签名（89 50 4E 47 0D 0A 1A 0A）
3. `lodepng::decode` 还原 16x16 尺寸且像素与原图逐字节一致
4. `lodepng_error_text(0)` 返回非空可读信息
5. 截断一半的 PNG 解码返回非零错误（反向对照，证伪 harness 有效）

链接 Conan 包内 `liblodepng`（`lodepng::lodepng` CMake 目标），非系统库。

## 验证结果

```bash
# 待 HMBS 真机预检回填（本轮仅交付未提交工作树，不预填数字）：
# conan create archives/l/lodepng/0.0-git20250402.c45ed79 --user=ohpcd --channel=stable
# 期望：build() 内 ./lodepng_unittest 打印 38/38 passed 标记；
#       test_package 内 ./test_lodepng 打印 5/5 passed 标记。
```

## 交付物

| 文件 | 说明 |
|------|------|
| liblodepng.a（或 .so） | 编译自 lodepng.cpp 的全部编解码符号 |
| include/lodepng.h | 公共头文件（含 C 与 C++ API） |
| licenses/LICENSE | 上游 Zlib 许可原文 |
| hmbs_upstream_result.json | 上游 verdict 持久化（供 test_package 在缓存命中时重放） |

## 注意事项

- 版本号 `0.0-git20250402.c45ed79` 为上游无 release 时的快照命名（日期 + 短提交号），与库内 `20241228` 版本串并存：前者定位源码归档，后者为上游自声明版本。
- `testFewColors` 为组合爆炸慢测（上游默认全量），真机耗时以预检日志为准；如超时再评估是否需 `DISABLE_SLOW`（当前配方坚持全量）。
- 产物无可执行文件，属纯库包，无需软件级 `commands.json`（R38）。
