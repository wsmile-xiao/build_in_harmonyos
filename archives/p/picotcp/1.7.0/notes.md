# picotcp 1.7.0 adaptation notes (GLM-42, 2026-09-17)

- 任务: 13603; 平台: picotcp/1.7.0 (开源鸿蒙PC专项积分赛-依赖); 分支 feat/picotcp-1.7.0
- 上游: https://github.com/tass-belgium/picotcp archive/refs/tags/v1.7.0.tar.gz
  sha256=8d4a2062360abb7e1334192511ffbaf7b2b6d02b8801ae70e9536926d28d8b18
- 构建体系: 无 configure；根 Makefile 直建静态库 libpicotcp.a。CC/AR/PREFIX/模块开关全部经 make 命令行变量注入：
  CC=<profile clang> AR=llvm-ar DEBUG=0 ADDRESS_SANITIZER=0 GCOV=0 -j2。
- 补丁 0001 (portability): Makefile 的 UNIT_LDFLAGS/UNIT_CFLAGS 增加 $(CONAN_UNIT_LDFLAGS)/$(CONAN_UNIT_CFLAGS)
  挂钩并去掉 -lsubunit——check 框架来自 conan 包 check/0.15.2（无 subunit 构建），同时保留 CFLAGS 继承
  （6LOWPAN=1 时上游在 CFLAGS 注入 -DPICO_6LOWPAN_LLS=1 等模块宏）。
- 补丁 0002/0003 (portability): check 0.15.2 的 START_TEST 宏带 (int _i) 形参，上游 2017 年测试代码
  在 modunit_pico_mld.c / modunit_pico_igmp.c 中重声明 'uint8_t _i' 触发重定义编译错误；
  删除本地声明，测试改用框架提供的形参，循环逻辑不变。
- 运行期约束: OHOS 构建机 /tmp 只读，check 的 IPC 临时文件按 TEMP→P_tmpdir→TMPDIR 优先级取路径，
  配方以 TEMP=<可写目录> 重定向（P_tmpdir 会遮蔽 TMPDIR，故两个变量都设）。
- 测试构建与打包构建分离：测试 pass 以 UNITS=1 6LOWPAN=1 IEEE802154=1 构建（units 目标硬链接
  6lowpan/802154 的 modunit，模块必须编入）；打包 pass 用上游默认模块集干净重建，二者 PREFIX 隔离。
  上游 make clean 只删 PREFIX 不删树内 stack/*.o modules/*.o，换配置重建前必须清树内 .o。
- 测试账本（四维）:
  - 上游静态注册（make units 入口，26 个 check 套件二进制）: 492 例
  - 实际执行: 492 例；通过 492；失败 0；错误 0（100%: Checks: 492, Failed: 0, Errors: 0）
  - 未执行子项及原因:
    ① make test TEST=1 的 picoapp/picoapp6 冒烟入口：依赖 Linux vdeplug/vde TAP 虚拟网络设施，OHOS 环境无此内核模块，平台受限不执行；
    ② make devunits 入口：引用的 test/unit/device/picotcp_mock.c 等资产未随 1.7.0 tarball 发布（上游归档缺陷），无法构建；
    ③ test/olsr_test.sh：依赖 vde 设备，同①。
  - 消费者测试: test_package/test.c 1 个程序，真实调用 pico_stack_init/pico_string_to_ipv4/pico_ipv4_to_string/
    pico_stack_tick，3 项断言（合法地址解析、往返一致性、栈 tick），链接 libpicotcp.a，退出码断言。
- packaging: 打包 conan-dist/include（构建期拍平的全部公共头 + 生成的 pico_defines.h + arch/ 平台头）
  与 lib/libpicotcp.a；cpp_info.libs=["picotcp"]。
- 已知限制: 打包库为上游默认模块集（6LOWPAN/IEEE802154 关闭）；测试入口验证了全模块集。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-17 05:17
**最终状态**: built
