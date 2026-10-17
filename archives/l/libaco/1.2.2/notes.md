# libaco 1.2.2 适配笔记（HarmonyOS / aarch64）

## 编译环境
- 构建系统: cmake（上游无 configure/CMake，端口新增 CMakeLists.txt 补丁）
- 编译日期: 2026-09-01
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 源码获取与核验
- 官方 tag: v1.2.2 = commit c19352548c971412a41dcedd85017b92e9bce33f（git ls-remote 核验）
- tarball: https://github.com/hnes/libaco/archive/refs/tags/v1.2.2.tar.gz
- SHA-256: 66495660fd6834bfc94f024c3a64cd4c145cd6ce6576d2d95af15c493b3d825a
- 版本声明: aco.h 中 ACO_VERSION_MAJOR/MINOR/PATCH = 1.2.2，与 README changelog v1.2.2 一致

## 上游测试台账（aarch64-unknown-linux-ohos, clang 15）
- 全目录扫描: 9 个独立测试源（tutorial_0..6 + synopsis + benchmark）
- 全量通过率: 8/9（tutorial_0..6、synopsis 全部 exit 0；tutorial_4/5 按 test.sh 预期 abort=134 视为通过；benchmark 为长时基准，30s 内仍在真实执行，非阻塞）
- 适配前基线: 9/9 全部构建即被 acosw.S/aco.h 的 aarch64 `#error "platform not support"` 拦截（上游仅 x86_64/i386）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 acosw.S/aco.h 无 aarch64 支持，编译即 #error | 上游仅实现 i386/x86_64 汇编上下文切换 | 新增 0001-aarch64-support.patch：acosw.S 加 aarch64（GAS 语法）acosw/aco_save_fpucw_mxcsr/aco_funcp_protector_asm/aco_funcp_entry_asm；aco.h/aco.c 注册 aarch64 寄存器布局与 reg[] 大小 |
| 2 | OHOS clang 集成汇编器不识别 `.intel_syntax`（x86 专用） | aarch64 汇编器不支持 Intel 语法指令 | aarch64 分支用 GAS 原生语法；`.intel_syntax` 仅保留在 x86_64 分支内 |
| 3 | `and sp, sp, #imm` / `bic sp, sp, #0xf` 报 invalid operand | 该集成汇编器不接受 sp 立即数逻辑指令形式 | 改用 `mov x9,sp / and x9,x9,#-16 / mov sp,x9` |
| 4 | 新协程首启的「return 触发 protector」语义在 aarch64 上无对应机制 | aarch64 用 x30(lr) 而非栈存返回地址 | 引入 aco_funcp_entry_asm trampoline：body 指针暂存 x19 槽(reg[0])，trampoline 对齐 sp、置 x30=protector 后 br x19 |
| 5 | GitHub 直连超时 | 网络受限 | 用 CI 镜像映射同款 gh-proxy.com 获取官方源；hash 与官方 tarball 一致 |

## 源码修改
- 0001-aarch64-support.patch: acosw.S / aco.h / aco.c + 新增 test_aco_ohos_aarch64.c（鸿蒙 aarch64 专项测试）
- 0002-add-cmakelists.patch: 新增 CMakeLists.txt（构建可安装库）

## 鸿蒙专项测试（test_aco_ohos_aarch64.c）
- t1 单协程 yield×5 参数保持、自然退出
- t2 双协程共享栈交错切换 save/restore
- t3 callee-saved 寄存器（x19..x28/d8..d15）跨切换保持
- t4 fpcr/fpsr(fenv) 每协程独立保存/恢复
- 4 项全部 PASSED，exit 0

## 依赖版本
- 无第三方 Conan 依赖（libc + clang 运行时）

## 验证结果
- conan-verify: 待跑
- 上游测试: 8/9 通过（见台账）
---

**编译结束**: 2026-09-01 18:19
**最终状态**: built
