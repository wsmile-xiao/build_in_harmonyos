# nob.h 3.9.0 适配笔记

## 编译环境
- 构建系统: none（header-only 单头文件库，无 configure/make/cmake）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64 工具链）
- 状态: built

## 编译步骤

header-only 库无编译步骤；配方仅打包头文件（package_type=header-library）：

```bash
conan create archives/n/nob.h/3.9.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

消费者与鸿蒙专项测试经 test_package 编译运行（CMake + C99）：

```bash
cmake --build build/clang-15-armv8-17-release -- -j20
./test_nob_consumer   # 3 断言 ALL PASS
./test_nob_ohos       # 10 断言 ALL PASS
```

上游测试按官方驱动方式运行（`clang -x c -o nob nob.c && ./nob`），
日志：`$HOME/tmp/nob-run-all.log`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 FAIL：conanfile.py 缺少 build() 方法 | G1 结构门禁要求 header-only 无构建配方显式声明 build()/export_sources()（E257） | 补 no-op build()、export_sources()、apply_conandata_patches() |
| 2 | 上游 chain 用例 UNEXPECTED OUTPUT：合并流顺序相反 | OHOS(musl 系) libc 对管道 stderr 无缓冲先落、stdout 全缓冲后落，与 glibc 录制快照顺序相反；内容逐字节一致 | 归因 libc 缓冲策略，非库缺陷；如实计入 18/19 台账（详见知识草稿 DRAFT-nob.h-3.9.0-err2out-merge-order-libc-buffering） |
| 3 | 上游测试编译需 -D_POSIX_C_SOURCE=200112L | OHOS libc 下 clock_gettime/CLOCK_MONOTONIC/nanosleep/PATH_MAX 需 POSIX 特性宏（E138/E152 同族） | 采用 shared.h 官方标志编译测试（配方不涉及） |
| 4 | W3 JC 命中其他库基线隐藏文件 | archives/c/cloog、kics、thc 提交前已存在的 .staging-verified/.build-closed 基线文件 | 基线隔离复验：记录路径与隔离前 SHA-256，临时隔离复跑 W3，原样恢复并核对恢复后 SHA-256（e3b0c442… 一致），未提交该基线 |

## 源码修改

无补丁（patches/ 空；header-only 库无需修改上游源码）。

## 依赖版本

无运行时/构建依赖（header-only，自包含）。

## 验证结果

- conan create（OHOS aarch64 profile）：通过，test_package 2 用例 13 断言全绿
  （test_nob_consumer 3 断言 + test_nob_ohos 10 处 CHECK 调用）
- 上游测试：19 个独立用例全部编译并运行，18 PASS / 1 顺序敏感（chain，内容一致）
- 全量通过率：18/19 = 94.7%

```bash
./nob test   # RC=1（chain 顺序差异），日志见 $HOME/tmp/nob-run-all.log
```

## 交付物

- archives/n/nob.h/3.9.0/conanfile.py（header-library 配方）
- archives/n/nob.h/3.9.0/conandata.yml（官方 URL + SHA-256）
- archives/n/nob.h/3.9.0/test_package/（消费者用例 + 鸿蒙专项测试 + MANIFEST）
- knowledge/drafts/DRAFT-nob.h-3.9.0-err2out-merge-order-libc-buffering.kv/.md

## 注意事项

- 上游 dual-license：MIT OR Unlicense（配方 license 字段如实声明）。
- chain 用例顺序差异属 libc 缓冲策略（musl 系 vs glibc），非库门禁失败；
  若未来上游以 setvbuf 固定缓冲顺序可自然转绿（参见 DRAFT-E658 同族）。
- reports/test-report.md 为本地运行台账，不入 PR（实测数据已内联至 manifest/MANIFEST）。