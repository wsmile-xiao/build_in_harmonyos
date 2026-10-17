# minimp3 0.0-git.ea99364 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统，conanfile.py 生成薄 CMakeLists.txt）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos 目标，OHOS aarch64 profile）
- 状态: built

## 上游形态

- 仓库: https://github.com/lieff/minimp3（master-only，无 tag 无 release）
- 版本号规则: 0.0-git.{master HEAD hash 前 7 位} → 本版本 = master @ ea99364f61c14656440e8d77e9c233ccf3124633
- 源码包: 官方 codeload master 分支 tarball（R39 官方源），sha256 实测:
  b7d27f8443461f37a0272a6f7f6db95546ead2c06cb3049728488588561b690d
  （git ls-remote 核验 master HEAD = ea99364f…，与版本号一致，无漂移）
- 许可证: CC0 1.0 Universal（public domain）
- 交付形态: header/源混合 —— minimp3.h(76,831B) + minimp3_ex.h(50,696B)，
  MINIMP3_IMPLEMENTATION 宏激活实现段
- 上游构建: 无 CMake/Makefile；.travis.yml 调 scripts/build.sh（gcc -O2 -std=c89 … -lm）

## 编译步骤

1. conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=…（CI 同款命令）
2. source(): 官方 tarball 下载解压（strip_root）
3. build(): save() 生成 minimp3.c（#define MINIMP3_IMPLEMENTATION + #include "minimp3_ex.h"）
4. build(): save() 生成薄 CMakeLists.txt（add_library + 上游测试 CTest 化 + install 规则）
5. cmake configure + build（clang 15 / c99 / 静态库）
6. cmake.test() → ctest 全量执行上游测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无构建系统 | minimp3 是单文件 header/源混合库，仅提供 .travis.yml | conanfile.py 生成 amalgamated 单 TU + 薄 CMakeLists.txt（MurmurHash3 先例同款打法），无源码补丁 |
| 2 | header-only INTERFACE 打包会丢失 ex API 符号 | minimp3_ex.h 含 14 个非 static 公共函数（mp3dec_load_buf/mp3dec_ex_* 等） | 薄静态库方案：编译单 TU 出 libminimp3.a，消费者免定义 MINIMP3_IMPLEMENTATION |
| 3 | 上游测试如何进 Conan 生命周期 | minimp3_test.c 是独立 TU（含自己的 main） | 原样编译为 minimp3_upstream_test 可执行 + CTest 注册 86 用例，build() 内 cmake.test() 真跑 |
| 4 | 无音频文件如何验证核心解码 | CI test_package 需自包含 | 合成 MPEG1 L3 静音帧（0xFF 0xFB 0x90 0x00 + 全零 main_data，417B），断言锚点全部 OHOS aarch64 实测校准 |

## 源码修改

无补丁。conanfile.py build() 中 save() 生成的两个文件（minimp3.c / CMakeLists.txt）
为增量打包层，上游 minimp3.h / minimp3_ex.h / minimp3_test.c 零修改。

## 依赖版本

W0 依赖审计: 零第三方依赖。
- minimp3.h: 纯算法，无系统头
- minimp3_ex.h: stdio/stdlib/string（musl libc）+ libm（floor 函数）
- minimp3_test.c: stdio/stdlib/math/string/time（+mmap 仅在 MINIMP3_TEST 宏下）

## 验证结果

```bash
# 上游测试真跑（本机 aarch64 OHOS，clang -O2 -std=c99 编译 minimp3_test.c 原样）:
#   83 个参考向量: PASS=83 FAIL=0（解码 + 与参考 PCM 比对，PSNR 全部合规）
#   自检模式 -t: EXIT=0（72 条 API 契约断言 + 全向量 PSNR 扫描）
#   模式抽样 -m 3 (iterate): EXIT=0; -m 6 (stream): EXIT=0
# conan create test_package 阶段: 24 条消费者断言全过（帧头解析/静音解码/
#   截断处理/detect-load 契约/ex 流式 API/参数错误契约）
# CTest 合计 86 用例（1 selftest + 83 向量 + 2 模式抽样）全部通过
```

## 注意事项

- 消费者链接 libminimp3.a 时不要定义 MINIMP3_IMPLEMENTATION（符号已在库内）
- musl/OHOS 的 libm 折叠进 libc，-lm 链接在 OHOS 上无害
- 上游 master 分支无版本 tag：引用本包固定用 minimp3/0.0-git.ea99364，
  后续上游演进需按 0.0-git.{新 hash7} 递增新版本目录
