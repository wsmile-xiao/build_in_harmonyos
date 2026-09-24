# psimd 0.0-git20200517.072586a 适配笔记

## 软件信息

- 上游: <https://github.com/Maratyszcza/psimd>（便携 128-bit SIMD intrinsics，
  单头文件 `include/psimd.h`，NEON/SSE/AVX/WAsm SIMD128 多后端）
- 版本快照: `072586a71b55b7f8c584153d223e95687148a900`（2020-05-17，
  "Fix psimd_qfma_f32 for FMA-enabled x86 processors"；上游仓库 2024-05-27 起归档只读，
  master HEAD 即此提交，无 tag 无 release）
- 版本串 `0.0-git20200517.072586a` 为任务指定（distro 风格 git 快照版本），
  与仓库先例 `asmjit/0.0-git20231115.1da9e4d`、`autobahn-cpp/17.5.1-git7cc5d37` 一致
- 任务语言: C++（psimd.h 为 C/C++ 兼容单头，消费者测试用 C++ 编写）

## 编译环境

- 构建系统: 无（header-only，配方仅复制头文件，不调用上游 CMake）
- 编译日期: 2026-09-19
- 真机: 10.195.180.238（HarmonyOS PC，HongMeng Kernel 1.12.0，aarch64），
  隔离 job `device-b/psimd-kb-20260919`（独立 CONAN_HOME/TMPDIR）
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，OHOS SDK 26.0.0.18_2）；
  Conan 2.29.1（OHOS 适配版）
- 状态: built

## 上游测试清点（R51 三步法第 1 步，实测）

| 清点项 | 结果 | 依据 |
|---|---|---|
| 源码包文件总数 | 6 | CMakeLists.txt, configure.py, confu.yaml, include/psimd.h, LICENSE, README.md |
| test/ 目录 | 不存在 | zip 解包清单 |
| *test* 源文件 | 0 | 无命中 |
| ctest 注册 | 0 | CMakeLists.txt 无 enable_testing()/add_test()，仅 INTERFACE 目标 + INSTALL(FILES) |
| make check / pytest 入口 | 0 | 无 Makefile，无 Python 测试 |
| 上游测试结论 | **0 个** | 上游零测试，消费者测试为唯一运行期验证 |

## 编译步骤（真机实际执行）

1. 官方源码 zip 下载校验（sha256=dc615342bcbe51ca885323e51b68b90ed9bb9fa7df0f4419dbfa0297d5e837b7，GitHub 直连可用）
2. 隔离环境 `conan create`（本地 profile：settings 同 `ci/conan/profiles/ohos-aarch64`，
   工具链路径改指本机 harmonybrew SDK——仓库 profile 硬编码 CI worker 的 /data/service/hnp 路径，本机不存在）
3. test_package 消费者测试执行（编译期 NEON 双拼写门禁 + 12 项 API 断言 + 不透明输入）
4. 真机证据采集：宏转储、反汇编计数（bsl 族=2、fmla=1）、三个负例对照
   （reports/knowledge-evidence.md EVID-00..05）
5. 影子 CI 门禁（提交后执行，见 reports/ 回填）

## 遇到的问题与解决方案（真机实测）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMakeLists 声明 `cmake_minimum_required(2.8.12)`，CMake 4.x 会拒绝 | 上游 2020 年归档不再维护 | header-only 配方不调用上游 CMake，仅复制头文件（E257 模式），不兼容不触发（E103/E321 不适用） |
| 2 | 首跑消费者测试编译期 #error：门禁判 `__ARM_NEON__` 未定义 | **OHOS SDK clang 只预定义 `__ARM_NEON`（无尾下划线），不定义 `__ARM_NEON__`**（标准 aarch64 clang/gcc 两者皆有；C/C++ 模式一致） | 门禁改双拼写（与 psimd.h 自身守卫一致）；psimd 上游本就同时接受两种拼写，后端实际激活 |
| 3 | -O3 下首个测试二进制反汇编向量指令总数为 0 | 常量输入被完全折叠 | 断言输入过 `__asm__ volatile("" : "+r"(x))` 不透明屏障；重建后 bsl=2、fmla=1 |
| 4 | 负例（-U NEON 宏）下 psimd.h 在 665 行报 `float32x4_t` 未声明 | 上游潜在缺陷：qfma 守卫（`__aarch64__`）与 arm_neon.h include 守卫（`__ARM_NEON__\|\|__ARM_NEON`）不匹配 → aarch64 无 NEON 宏时头自毁（硬编译错误，非静默退化） | 无需修复（OHOS 上 `__ARM_NEON` 已定义）；消费者门禁置于 include 之前，给出可行动报错（知识草稿边界事实） |
| 5 | 仓库 CI profile 的编译器路径在本机不存在 | profile 硬编码官方 CI worker 的 /data/service/hnp 路径 | job 本地 profile 覆盖（settings 不变，路径指向本机 SDK），与 psimd 适配本身无关 |

## 源码修改

- 无补丁（patches: {}）。header-only 打包不动上游源码；包内 psimd.h sha256 与源码一致。

## 依赖版本

- 无第三方 Conan 依赖（自包含单头）
- 消费者测试仅需 libc/libm（fmaf）

## 验证结果（真机实测）

- conan create: 退出码 0（隔离 CONAN_HOME，ohos-aarch64 profile）
- 消费者测试: **12/12 断言通过**（ctest 1/1 + 直接执行；二进制原生运行）
- 上游测试: 0（上游零测试，见清点表）
- 后端激活证据: 双拼写宏门禁通过 + `__ARM_NEON=1` 宏转储 + 反汇编
  `bsl v0.16b`/`bif v0.16b`（vbslq_s8 路径）与 `fmla v3.4s`（vfmaq_f32 路径）
- 负例对照: 5 项全部按预期（EVID-00..05，含 fmla 不可作判据的收缩实证）
- 包完整性: `include/psimd.h` + `licenses/LICENSE`，头文件 sha 与源码一致
- 影子 CI: L0/L1 pass、L2 有据 skip、L4 pass、L5 warn（header-only 产物为 include/，见 reports/knowledge-evidence.md 第 6 节）；Build Summary 1/1 Success

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library，E257 no-op build） |
| conandata.yml | 官方源码 URL + sha256（CI 自动加镜像 fallback） |
| test_package/ | 消费者测试（test.cc：双拼写门禁+不透明输入+12 断言）+ MANIFEST.yml |
| reports/ | knowledge-evidence.md（五步证据链 + 环境指纹 + 测试统计） |
| knowledge/drafts/ | DRAFT-psimd-0.0-simd-backend-activation-evidence.kv/.md（知识草稿） |

## 注意事项

- 本任务为知识库扩展任务，PR 前缀【知识库扩展】
- 知识路径：路径 B（知识库扩展）——主草稿为 SIMD 后端激活验证契约
  （含 OHOS clang NEON 宏拼写分歧、常量折叠、FMA 收缩三个实证混淆因子）；
  E257/E103/E321 为既有知识复用，不重复申报
- 真机结果为独立验证证据，不替代官方 PR CI
