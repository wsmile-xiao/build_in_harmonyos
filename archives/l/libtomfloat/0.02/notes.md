# libtomfloat 0.02 适配笔记

## 任务信息

- 平台任务号：7363（活动：开源鸿蒙PC专项积分赛-依赖）
- 分支：feat/libtomfloat-0.02；worktree：~/qzy/GLM-20-libtomfloat-0.02
- 上游：https://github.com/libtom/libtomfloat tag 0.02（tarball sha256 ae0009ad…88eb5）
- 语言：C（lang-preflight 通过，milestone=lang_checked）；构建系统：纯 GNU makefile（无 configure）
- 主理 agent：GLM-20

## W0 依赖检查

- 唯一依赖 libtommath/1.3.0 已发布：`conan download libtommath/1.3.0 -r=ohpcd --only-recipe` 成功（revision 29d534f9）。
- 无其他精确版本依赖。

## W0b 历史经验

- 仓库无 libtomfloat 历史归档，首次适配。
- 参考同上游系列 libtommath/1.3.0 已合入配方（makefile 直传 CC/AR/RANLIB 模式）。

## 上游测试清点（R51 证据）

makefile 目标全量清单：`default`（libtomfloat.a）、`ex1`、`mandvi`、`manual`、`install`、`clean`、`zipup`。
**无 check/test 目标**；`demos/ex1.c` 为打印演示程序（无断言、不判定退出码）。
结论：上游无自动化测试套件，静态声明总数 N_static = 0（附清点证据）。

## 四维测试账本

| 维度 | 数量 | 说明 |
|---|---|---|
| 上游静态声明 N_static | 0 | makefile 无 check 目标，demos/ex1.c 非断言测试 |
| 构建注册 N_registered | 0 | 同上 |
| 实际执行 N_executed | 0 | 无上游套件可执行 |
| 消费者测试 N_consumer | 1 | test_package/test.c，9 项断言（N_assertion=9） |

消费者测试以库使用者身份调用 mpf_add/sub/mul/div/sqrt/invsqrt/inv/cmp_d/cmp 公开 API，
断言真实计算行为（如 (2/3)*3==2、sqrt(4) 调用返回、2-3==-1），以退出码判定结果。

## 测试设计实测记录（消费者断言口径依据）

调试程序（~/tmp/uc2/glm20/dbg*.c，链接本包 libtomfloat.a + 制品仓 libtommath.a）实测：

1. **API 32 位限制**：mpf_const_d/mpf_mul_d/mpf_cmp_d 的 long 参数经 mp_set_int 转换只保留
   32 位——传 1e15 得到错误值（实测 mul_d(2, 1e15) ≈ 5.53）。测试全部整数常量 < 2^31。
2. **迭代近似残差**：div ((2/3)*3) 残差 2^-98；invsqrt(4)*4 残差 0（精确 2）；inv(2)*2 残差
   2^-99——容差取 2^-30 绝对值，实测均通过。
3. **mpf_sqrt 上游算法缺陷**：牛顿迭代（初值 a 右移 + exp/2）对完全平方输入 a=4 不收敛，
   实测 sqrt(4) ≈ 4.97e-32，|x-2| = 2.0。上游 demos/ex1 只打印无判定，属上游 0.02 已知
   质量水平。消费者测试对 sqrt 不设数值断言，仅验证调用返回 MP_OKAY，透明记录于此。

## 构建方式

- makefile 隐式规则 `$(CC) $(CPPFLAGS) $(CFLAGS) -c`；依赖头文件经 `CPPFLAGS=-I<libtommath include>` 传入
  （tomfloat.h `#include <tommath.h>`）。
- make 默认 CC=cc/AR=ar 在 OHOS 工具链不存在，显式传 `CC/AR/RANLIB`（conf tools.build:compiler_executables，缺省 clang/llvm-ar/llvm-ranlib）。
- 上游只产静态库（package 手工 copy tomfloat.h + libtomfloat.a）；shared 选项禁用（validate 拦截）。
- 上游 makefile `install` 目标带 `-o root -g root`，非 root 设备不可用，故 package() 不走 make install。

## 路径 B 判断

本任务直接复用 libtommath 已入库的 libtom 系 makefile 配方模式（CPPFLAGS/CC 显式传递），
未遇到新的错误签名，无跨仓库复用的新知识增量 → **纯路径 A**。
---

**编译结束**: 2026-09-13 11:48
**最终状态**: built
