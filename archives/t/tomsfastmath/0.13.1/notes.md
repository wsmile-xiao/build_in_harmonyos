# tomsfastmath 0.13.1 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/libtom/tomsfastmath
- 正式标签：`v0.13.1`（git tag 指向 commit `adf0549383e9d41cf7ec6aeb6b3ad6189d731488`）
- 源码 tarball：`https://github.com/libtom/tomsfastmath/archive/refs/tags/v0.13.1.tar.gz`
- SHA-256：`207e8624382e815f58bc5c3d4aad725d94588a6cc465d34634e6533dcaae2e0d`（tarball 实测）
- 许可证：上游 LICENSE 为双许可条款，文件正文为 Apache License 2.0，按 **Apache-2.0** 申报
- 平台任务：7323（`tomsfastmath/0.13.1`，依赖活动 activity_id=6）

## 结构
- 大数运算库（libtom 系，libtommath 姊妹项目）：makefile + makefile.shared 构建静态库 libtfm.a；头文件 `src/headers/tfm.h`
- src/ 按运算分目录（addsub/mul/sqr/bit/shiftn/mont/...），另有 pre_gen/mpi.c 预生成合并版（需自行选择构建方式；makefile 用分文件）
- demo/stest.c（自测，9 项 passed 输出）+ demo/test.c（主测试套件，Montgomery/素数/RSA 段，"Passed." 2 段）+ mtest/（对拍 libtommath 的工具，需 ltm 依赖，本适配不使用）
- 依赖：无任何第三方依赖（C99，libc）

## 分支基线说明
- 分支 `feat/tomsfastmath-0.13.1` 基于 fork `origin/main`（9b49d7903），理由同前（W3 JC6 原子性判定用 origin/main...HEAD；fork main 为 upstream main 祖先，PR diff 不受影响）

## 上游测试（四维账本）
- 上游 makefile 目标：`make`（libtfm.a）、`make test_standalone`（demo/test），demo/stest.c 需手工链接；姊妹库 libtommath/1.3.0 配方（archives/l/libtommath/1.3.0）已确立"build() 内嵌上游测试运行"的先例，本配方沿用
- **N_static（静态声明）= 11**：demo/test.c 2 个 `Passed.` 输出段（Montgomery #1/#2）+ demo/stest.c 9 个 `passed` 输出（mul×3/sqr×3/mont×3）
- **N_executed = 11，failed = 0**：
  - `./stest`：9 passed，退出码 0
  - `./test`：2 段 Passed.（Montgomery #1/#2），failed=0，退出码 0；内联素数扫描 512→639 bits 为段内迭代非独立用例
- 构建与运行证据：设备 `~/tmp/uc2/tomsfastmath-0.13.1/dl/src0131/tomsfastmath-0.13.1/{build.log, stest_run.log, test_run.log, test.done=RC=0}`
- 运行方式：`make CC=<clang> AR=<ar> RANLIB=<ranlib> -j2 && make test_standalone && ./stest && ./test`（CC/AR/RANLIB 经 conan conf `tools.build:compiler_executables` 注入，R33 合规；未修改任何上游文件）

## 消费者 API 口径（试编译迭代确认）
- `fp_count_bits` 返回"最高置位位序+1"（2^160 的计数为 161 而非 160，首轮断言写 160 已纠正）
- 有符号语义：`fp_sub` 结果可负（`sign == FP_NEG`），`fp_cmp_d` 比较无符号立即数
- 消费者测试 7 项断言：位计数、加法、平方、有符号减法双向、十进制字符串输出、大数平方位宽

## 路径 B 判断（结论：不走 B，纯路径 A）
- 零补丁、零上游修改、构建零报错；libtommath 姊妹配方已覆盖 makefile 系模式，无新增跨仓库知识。按纯路径 A 交付。

## test_package（消费者验证）
- Conan L1：CMakeDeps + find_package（C99），消费者程序 `test_tomsfastmath.c`（1 个程序，7 项断言），链接打包 libtfm.a
- `test()` 经 bash 包装执行二进制（OHOS mksh 规避），退出码 0 判定通过

## 后续
- 状态：built（2026-09-12 finish 收尾）
- 无 commands.json（纯库，无命令行产物）
---

**编译结束**: 2026-09-12 07:29
**最终状态**: built
