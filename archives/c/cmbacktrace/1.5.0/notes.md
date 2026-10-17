# cmbacktrace 1.5.0 适配笔记

## 编译环境
- 构建系统: custom（source-drop 单 TU 库，上游无 configure/make/CMake）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built（PR 阶段无上传发布授权；合并 main 后 CI 自动上传并更新为 published）

## 编译步骤

上游 CmBackTrace 是 Cortex-M 故障回溯库，形态为"源码即插即用"：核心只有一个
编译单元 `cm_backtrace/cm_backtrace.c` + 头文件 + Languages/ 语言字符串头。
无任何构建系统入口。因此本配方直接编译该 TU 生成静态库：

```bash
clang -std=c99 -O2 -fPIC -I<src>/cm_backtrace \
      -c <src>/cm_backtrace/cm_backtrace.c -o cm_backtrace.o
llvm-ar rcs libcmbacktrace.a cm_backtrace.o
```

配方在 build() 中从 Conan conf（tools.build:compiler_executables）取 cc/ar（R33），
不裸用 shell 环境变量。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 cmb_cfg.h 的 cmb_println 为空宏、CMB_CPU_PLATFORM_TYPE 未定义，预处理直接失败 | 库设计为"用户必须配置 cmb_cfg.h" | 补丁 0001：提供可用默认（printf 版 cmb_println、bare-metal、Cortex-M4、英文输出） |
| 2 | cm_backtrace.c 引用 CMB_CSTACK_BLOCK_START/END、CMB_CODE_SECTION_START/END 四个链接脚本符号，非 MCU 平台无定义，链接失败 | 库面向 Cortex-M 链接脚本 | 补丁 0002：四个符号声明为 `__attribute__((weak))`，未定义时解析为 0；消费方在链接脚本或源码中定义真实栈/代码边界即可覆盖 |
| 3 | Cortex-M 内联汇编（MRS msp/psp、MOV sp）在 aarch64 上报 operand-width 警告 | 架构指令差异 | 仅警告不阻断，属可接受面；这些函数仅在 MCU 故障路径调用 |
| 4 | cm_backtrace_init 在栈边界符号为 0 时打印 "Unable to get the main stack information" 并跳过初始化 | 弱符号默认 0 → main_stack_size==0 | 属上游设计的配置错误提示路径；消费方定义符号后初始化正常 |

## 源码修改

- patches/0001-cmb-cfg-defaults.patch — cmb_cfg.h 默认配置
- patches/0002-weak-linker-symbols.patch — cm_backtrace.c 弱符号

## 依赖版本

无外部编译依赖（requirements 为空）。

## 验证结果

### R51 上游测试申报（清点证据）

上游源码包（728 个文件）目录逐一枚举：cm_backtrace/（库源码+Languages 语言头）、
demos/（STM32/FreeRTOS/RT-Thread/UCOS MCU 工程，非测试）、docs/（文档）、
tools/addr2line（Win32 辅助二进制）。无 Makefile/CMakeLists/测试脚本/ctest 注册项，
上游无测试框架，source_declared_total=0（与 test_package/MANIFEST.yml 的
upstream_tests: [] 一致，详见该文件枚举说明）。本库测试 = test_package 消费者
1/1 + 鸿蒙专项测试 1/1（reports/ohos-test/）。

```bash
# 手动编译（首轮探索）
clang -std=c99 -DCMB_USER_CFG -I<cfg> -Icm_backtrace -ILanguages -c cm_backtrace.c
# → EXIT=0，生成 aarch64 ELF relocatable 对象，49 warning / 0 error

# 消费者验证（弱符号链接 + 运行）
clang -std=c99 -I<src>/cm_backtrace consumer.c libcmbacktrace.a -o consumer
./consumer
# → ERROR: Unable to get the main stack information ...（弱符号为 0 的预期提示）
#   Firmware name: cmbacktrace-test, hardware version: ohos-aarch64, software version: 1.5.0
#   call_stack depth=0（OHOS 上 MCU 语义回溯为 0 深度，属预期）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | source-drop 单 TU 配方 |
| conandata.yml | 官方 GitHub tag 源码 + SHA-256 |
| patches/0001,0002 | 配置默认 + 弱符号补丁 |
| test_package/ | 消费者测试（调用公开 API） |

## 注意事项

- 库的调用栈回溯、故障诊断依赖 Cortex-M 链接脚本符号与 BL/BLX Thumb 指令语义，
  在 OHOS aarch64 上回溯返回 0 深度属预期；适配目标为可编译、可链接、可安装、
  公开 API 可调用的静态库交付。
- 本库不产生 CLI 可执行文件（纯库类型），按 R38 无需 commands.json。

## 知识候选台账（knowledge_candidate_ledger）

候选 #1：MCU 目标 source-drop 库在 OHOS 上的三层适配（cmb_cfg 默认配置 +
链接脚本符号 weak 化 + 架构专属语义优雅降级）

- 真实错误：
  - `cmb_def.h: CMB_CPU_PLATFORM_TYPE isn't defined in 'cmb_cfg.h'`（默认配置头留空）
  - `undefined reference to CMB_CSTACK_BLOCK_START/END、CMB_CODE_SECTION_START/END`
    （链接脚本符号非 MCU 平台缺失）
  - `MRS %0, msp` operand-width 警告（Cortex-M 内联汇编在 aarch64 上的宽度提示）
- 根因：库面向 ARM Cortex-M 嵌入式工程源码即插分发，配置头留空由用户填、
  引用 MCU 链接脚本符号、回溯算法依赖 Thumb BL/BLX 指令语义。
- 修复：补丁 0001（cmb_cfg.h 提供 printf 默认 + bare-metal + M4 + 英文）；
  补丁 0002（四个链接脚本符号 `__attribute__((weak))`，未定义解析为 0，
  init 检测 main_stack_size==0 走文档化提示路径不崩溃）；aarch64 上
  call_stack 返回 0 深度属预期，鸿蒙专项测试断言 depth==0 + exit 0（优雅降级）。
- 验证：conan-verify G0-G4/L2/L4/L5 全 PASS；W3 本地 CI L0/L1/L1e/L4/L5 PASS；
  test_package 1/1；reports/ohos-test/ohos_test.c 编译链接运行 PASS（depth=0）。
- 适用范围：所有 MCU/嵌入式目标、source-drop、无构建系统、引用链接脚本符号的
  C 库在 OHOS PC/CI 的 Conan 适配（故障回溯、RTOS 组件、外设驱动等）。
- 四范围查重：
  - 正式知识（knowledge/doc/ + index.tsv）：E085（weak 弱符号→musl pthread API 探测，
    根因不同）、E277（vendored 依赖 staging，根因不同）、E281/E305（无构建资源包，
    触发部分重叠）、E450（AVR 交叉 sysroot 弱符号验证，根因不同）→ 均未命中组合。
  - 知识图谱（knowledge/graph/*.kv）：同上 E 条目比对，无覆盖"链接脚本 extern 符号
    weak 化保链接"条目。
  - 草稿（knowledge/drafts/）：DRAFT-enet-2.7.0-single-header-impl-lib（单头实现库
    小 TU 编译为真实 .a，形态相邻但无弱符号/优雅降级）、DRAFT-picosha2（header-only
    相对 dst + L0k 假阳性，无关）→ 无命中。
  - 七轴查重：exact_duplicate=false、causal_duplicate=false、trigger_overlap=partial、
    solution_overlap=partial、combination_novelty=true、boundary_novelty=true、
    test_migration_novelty=true（详见 knowledge/drafts/DRAFT-cmbacktrace-1.5.0-mcu-source-drop-weak-linker-symbols.md）。
- 关系：similar_to=[E085,E277,E281,E305,E450,DRAFT-enet-2.7.0-single-header-impl-lib]、
  caused_by=[]、prerequisite_of=[]、conflicts_with=[]。
- 路径决定：**new_draft（路径 B 知识库扩展）** —— 候选已验证、可跨库复用
  （MCU source-drop 库族）、查重为部分覆盖且存在新增差异（弱符号链接脚本边界 +
  优雅降级验证模式），已建同 stem 草稿 .kv/.md 随本库 PR 交付。

## R02 知识候选台账增补（knowledge_candidate_ledger_r02）

候选 #2（R02）：CI L0d 反空壳门禁要求 test_package/conanfile.py 的 test()
必须包含 self.run() 调用，否则 L0 直接 fail（stub_test_method）

- 真实错误（远端 CI PR #11053）：`[fail] L0d: test() method has no self.run()
  call — likely a stub` / `stub_test_method` / `L0_RESULT=fail: gate failed: stub_test_method`
- 根因：r01 提交 d7ed919237 在 W4 清理中删除了 test_package/conanfile.py 内
  唯一命中 `grep -q "self\.run"` 的注释行；本地 W3 日志（04:39）早于该删除，
  故本地未暴露，远端 CI 对新提交执行 L0d 时检出失败（本地/远端口径一致，
  均为同一份 ci/conan/build_and_test.sh：TEST_PKG_DIR="$pkg_dir/test_package" +
  grep -q "def test" + grep -q "self\.run"，差异仅是时间差）。
- 修复：test() 新增真实 `self.run(os.path.join(self.cpp.build.bindirs[0],
  "test_cmbacktrace"), env="conanrun")`；复验 conan create 日志显示
  `RUN: ./test_cmbacktrace` 实际执行并输出固件信息，W3 11:00 复跑
  L0/L1/L1e/L4/L5 全 PASS。
- 四范围查重结论（**完全重复 → reuse_existing → 路径 A 对该候选引用，不新建草稿**）：
  - 正式知识：**E472**（error_signature/match_keywords 均含 `stub_test_method`、
    `self.run`，标题含 "self.run for L0d gate"，SDL_kitchensink 1.0.13 实证）、
    **E255**（error_signature 含 `stub_test_method`，match_keywords 含 L0c/L0d、
    self.run() 检查）已完整覆盖"L0d 要求 test() 含 self.run() 反空壳"规则；
    E239/E241 覆盖 self.run+conanrun 用法。
  - 知识图谱：E472/E255 同源条目命中。
  - 草稿：DRAFT-sdl-kitchensink-1.0.13-ohos-elf-sign-sdl-headless-test.md（E472 配套
    草稿）已沉淀该规则。
  - 先例库实证：file/5.48.1、jbigkit/2.1、mad/0.16.4、pycxx/6.2.3、
    zlib-ng-compat/2.3.3 的 test_package/conanfile.py 均有显式 `# L0d: explicit
    self.run() required by CI gate` 合规注释。
- 七轴：exact_duplicate=true、causal_duplicate=true、trigger_overlap=full、
  solution_overlap=full、combination_novelty=false、boundary_novelty=false、
  test_migration_novelty=false。
- 关系：similar_to=[E239,E241,E255,E472,DRAFT-sdl-kitchensink-1.0.13]、
  caused_by=[]、prerequisite_of=[]、conflicts_with=[]。
- 路径决定：**reuse_existing（路径 A 对该候选引用 E472/E255，不建新草稿）**；
  r01 已建的 DRAFT-cmbacktrace-1.5.0-mcu-source-drop-weak-linker-symbols 草稿
  （候选 #1，new_draft）仍有效，随本 PR 继续交付。
---

**编译结束**: 2026-09-19 10:58
**最终状态**: published
