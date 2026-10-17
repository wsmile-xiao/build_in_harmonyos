# mpsolve 3.2.1 adaptation notes (GLM-42, 2026-09-17)

- 任务: 13605; 平台: mpsolve/3.2.1 (开源鸿蒙PC专项积分赛-依赖); 分支 feat/mpsolve-3.2.1
- 上游: https://github.com/robol/MPSolve archive/refs/tags/3.2.1.tar.gz
  sha256=7edb7899d69a3e09848b893b12f360b8a83429a18eee4a7f193fcfc8692dca71
- 定位: application（MPSolve CLI + libmps）；commands.json 包级（R38）。
- 依赖链关键: **gmp/6.3.0.1（CXX 构建，--enable-cxx）**——libmps 的 formal 模块
  （formal-monomial.cpp/formal-polynomial.cpp）无条件编译且使用 GMP C++ 绑定
  （mpq_class），基础版 gmp/6.3.0 不含 libgmpxx/gmpxx.h。check/0.15.2 经
  PKG_CHECK_MODULES 驱动上游 make check。
- 补丁 0001 (portability): mps/mpc.h 声明 `register signed long int`——C++17 已移除
  register 关键字，-std=c++17 下 nroots-polynomial.cpp 等编译失败；去掉关键字。
- 构建要点（E386/§12.49 + E011 家族，全部设备实证）:
  ① 全部 configure/make 经 `env -u CONFIG_SHELL SHELL=/bin/sh` 路由（hnp bash getcwd 缺陷）；
  ② autoreconf -fi 需 ACLOCAL_PATH 指向 pkg-config 的 share/aclocal（pkg.m4 缺失否则
     PKG_CHECK_MODULES 展开为语法错误）；
  ③ 生成的 configure 中 `(umask 077 && mkdir ...)` 包裹在 HMDFS 上导致
     config.status "can't create ./conf*/subs1.awk: Permission denied"——sed 生成物
     umask 077→022（E011 受控方案，保留临时目录创建，仅放松掩码）；
  ④ GMP_CFLAGS/GMP_LIBS 内联注入（configure.ac 原生支持；GMP_LIBS 含 -lgmpxx）；
  ⑤ make check 的 check 框架 IPC 临时文件按 TEMP→P_tmpdir(/tmp)→TMPDIR→"." 取路径，
     /tmp 只读 → TEMP 重定向到可写目录（picotcp 同款）；测试二进制运行时
     LD_LIBRARY_PATH 补 libgmpxx/libcheck 路径。
- 测试账本（四维）:
  - 上游静态注册: 90（src/tests 15 个程序：14 个 .c + check_formal.cpp 的 START_TEST 逐项计数）
  - 实际执行: 15/15 程序构建并执行，teST 套件汇总 PASS: 16（含 libmps 内部 1 个）；check 框架
    报告 Checks 合计 135 次（部分 tcase 循环执行，次数>静态注册数）、Failures: 0、Errors: 0
  - 通过率口径: 程序级 16/16；用例级静态 90/90 全数执行，0 失败
  - 消费者测试: smoke_mpsolve.sh 1 个——按官方输入格式喂 x^2-2，断言输出含
    ±0.141421356…e1（±√2，科学计数法），实测通过
- 未执行子项: examples（--disable-examples，依赖额外语言绑定）、GTK/Qt UI 与
  graphical-debugger（--disable-*，OHOS 无桌面栈）——均为非测试入口的组件。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-17 19:48
**最终状态**: built
