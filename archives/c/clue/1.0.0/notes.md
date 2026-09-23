# clue 1.0.0 适配笔记

## 编译环境
- 设备: HarmonyOS PC (aarch64)，HongMeng Kernel 1.12.0，HMDFS
- 构建系统: makefile（上游无 CMakeLists，仅 `tests/Makefile`；打包本体 header-only copy）
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4（conan profile `ci/conan/profiles/ohos-aarch64`：os=OHOS, os.version=6.0, arch=armv8, libc++17 宿主配置；上游用例按自身 `-std=c++03` 编译）
- Conan: 2.29.1（OHOS 适配版）
- 状态: built（conan-verify G0–G4 通过 + W3 本地 CI 通过；未 upload，发布以 CI release 流水线为准）

## 软件定性（W0/W0b 预检结论）
- 上游: https://github.com/martinmoene/clue tag `v1.0.0`，C++03 header-only
  日志库，单头 `include/clue.hpp`（694 行），BSL-1.0。
- 零依赖：仅标准库；`<syslog.h>` 只在用户显式定义 `clue_LOG_TO_SYSLOG` 时引入，
  默认 console 后端、上游测试用 `clue_LOG_TO_STRING`，均不触碰 OHOS libc 的
  syslog 符号，无平台适配风险。
- vcpkg 端口同版本同 REF（SHA512 与官方归档一致），conan-center-index 无此库。
- 历史核验：本仓库 `archives/` 无 clue 归档、git log 无 clue 提交、
  GitCode 无 `feat/clue-1.0.0` 同分支任何状态 PR（2026-09-03 查证）→ 新软件首适。
- CI 能力矩阵：仅需 make + clang（均在列 ✅），无 Rust/OCaml 类环境阻断。
- 知识库比对：E257（无 CMake 的 header-only 必须保留显式 `build()`）、
  E321（martinmoene lite 系 Conan2 配方骨架与 CMakeDeps 消费口径）。
  本配方 `build()` 非 no-op：直接运行上游真实测试，两条门禁均满足。

## 编译步骤

```bash
# 配方内（conan create 驱动）：
conan create archives/c/clue/1.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=clue/* --user=ohpcd --channel=stable
# build() 执行: make -j2 -C tests
#   → /data/service/hnp/bin/clang++ -Wall -Wextra -Weffc++ -std=c++03 -I../include \
#       -o test_clue test_clue.cpp test_clue_part2.cpp
#   → ./test_clue（上游 Makefile all 目标自带运行，失败即 make 非零 → G2/W3 拦截）
# package(): 仅 copy include/clue.hpp + LICENSE_1_0.txt
```

配方外探索验证（同一设备、同一编译器路径）：完整解包后直接
`make -j2 -C tests CXX=/data/service/hnp/bin/clang++`，通过后再进 conan 流程。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费测试编译报 `use of undeclared identifier 'the_log'` | clue 短名宏 `LOG_INFO/LOG_ERROR` 展开为**非限定** `the_log()`（clue.hpp 307 行），宏不是命名空间成员，`clue::LOG_INFO(...)` 写法也不合法 | 消费者 TU 与上游测试同款 `using namespace clue;`（test_package/test_clue_consumer.cpp），不改上游源码、不引入平台宏 |
| 2 | `test_clue` 运行 exit 0 但无任何输出，无法取证用例数 | 本版本 lest_cpp03 成功时默认静默（`confirm` 析构仅在 `failures>0` 或 `-p/--pass` 时输出） | 证据统一用 `./test_clue -p`；配方 build() 维持上游默认（失败必阻塞，成功静默 exit 0） |
| 3 | `make -j2` 出现 `jobserver mkfifo: ~/GMfifo*: Operation not permitted` | HMDFS 不允许创建 FIFO（make 4.4.1 jobserver） | GNU make 降级为串行执行并继续，实测非致命（两 TU 单目标本就无并行需求）；保留 `-j2` 与社区惯例一致，记录此告警 |
| 4 | conan-verify G1 报缺"补丁应用调用" | G1 结构门禁要求 `apply_conandata_patches` 钩子存在（即使补丁集为空） | `build()` 开头调用 `apply_conandata_patches(self)`，与参考包 nanobench 同构 |
| 5 | finish 过程把 `conandata.yml` 的 url 改写为 gh-proxy 镜像列表且"恢复"不完全 | `conan-verify`/`finish` 的 E017 镜像注入副作用（`.ghfast-bak` 为原始备份） | 从 `.ghfast-bak` 恢复官方原始 url 后才提交；镜像注入现场保留于任务私有目录（`conandata-mirror-rewritten.evidence`），未入库。**本 PR 提交的 conandata.yml 为纯官方 URL**（R39） |

## 源码修改

无。零补丁（`patches: {}`），未引入任何平台条件编译宏；上游两测试 TU 与
头文件均原样编译通过。

## 依赖版本

无编译依赖（requires 空）。构建工具：make 4.4.1 / clang 15.0.4（设备基线）。

## 验证结果

设备实跑（全部在 HarmonyOS PC aarch64 本机）：

```text
# 1) 上游测试（配方外探索，make -j2 -C tests → exit 0；-p 取证）
$ ./test_clue -p
... 25 行 "passed:"（test_clue.cpp 23 + test_clue_part2.cpp 2）
All 15 selected tests passed.        # 源码 16 CASE；"clue version" 带
                                     # [.clue][.version] 隐藏标签，默认不选

# 2) 上游断言可失败性（仅私有拷贝，把 LOG_ALERT 期望 severity 改为 DEBUG）
1 out of 15 selected tests failed.   # test_clue.cpp:119: failed: ... for 1 == 7
make Error 1；直接运行 exit=1        → 恢复后 All 15 selected tests passed.

# 3) conan-verify（G1 完整 / G0 通过 / G2 conan create 干净构建 / G3 / G4 通过）
clue/1.0.0@ohpcd/stable#ed6056c9032fd07650f047db5ebc375e
  :6b129b068851896169fae42d399fa922d239ce8a (package id)
package(): Packaged 1 '.hpp' file: clue.hpp
package(): Packaged 1 '.txt' file: LICENSE_1_0.txt
clue consumer checks: 14/14 passed   # test_package 实跑

# 4) test_package 断言可失败性（把 "hello 42" 期望改为 "hello 43"）
FAIL line 55: clue::the_log().text() == std::string("hello 43")
clue consumer checks: 13/14 passed   # conan test exit 1
→ 恢复原期望后 conan test exit 0，clue consumer checks: 14/14 passed
```

- 上游用例实数：**15/15 selected 通过**（25 项断言评估），源码 16 CASE。
- 新增消费者用例：**14/14 通过**（C++98 编译，验证打包头文件真实 API）。
- `.ci-result.json`：W3 本地 CI exit_code=0（finish 自动写入，含 log_sha256）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方，build() 跑上游测试 |
| conandata.yml | 官方 GitHub tag 归档 + 设备实测 sha256 |
| test_package/{conanfile.py,CMakeLists.txt,test_clue_consumer.cpp,MANIFEST.yml} | 消费者测试（14 CHECK）+ 上游测试声明 |
| manifest.yaml / notes.md | 本归档元数据 |
| archives/c/clue/{manifest.yaml,README.md} | 软件级元数据 |

## 注意事项

- 消费方若需要 syslog 后端，须自行定义 `clue_LOG_TO_SYSLOG`；该路径依赖
  libc `syslog(3)`，本包默认不编译该路径（OHOS 下可用性未在本任务验证范围）。
- 短名宏与全局 `LOG_*` 同名冲突（syslog 宏等），多库共存时建议消费方定义
  `clue_NO_SHORT_NAMES` 并改用 `clue_LOG_*` 前缀宏。
- R46 result.json 生命周期草稿未启用：外部调度器未指定 `--out`/`OHC_RESULT_OUT`，
  按 AGENTS 口径设备默认草稿不作为本任务结果文件。
---

**编译结束**: 2026-09-03 20:36
**最终状态**: built
