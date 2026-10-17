# tbox 1.7.8 adaptation notes (GLM-42, 2026-09-17; GLM-49 整改 2026-09-20)

- 任务: 13604; 平台: tbox/1.7.8 (开源鸿蒙PC专项积分赛-依赖); 分支 feat/tbox-1.7.8
- 上游: https://github.com/tboox/tbox archive/refs/tags/v1.7.8.tar.gz
  sha256=eda4ea0fe53b55594a0c4842fcf1f3510fec5b183936142873c47455fdaefa4a
- 构建体系: 自带 xmake.sh 的 configure 脚本（非 autotools）。CC 环境变量注入 OHOS clang，
  `--plat=linux --arch=arm64 --toolchain=clang --mode=release --kind=static --demo=y`，
  特性探测（libc/posix 函数）自动适配 musl。`make -j2 && make install`。
- 补丁: 无（零补丁）。
- 依赖: 无（零外部依赖；small 模式默认关闭可选模块 xml/zip/regex/database/coroutine 等，打包上游默认核心）。
- 测试账本（五维，2026-09-20 GLM-49 整改后）:
  - 上游静态（N_static）: 160（src/demo 下 *.c 源文件实测口径，与审查实测一致；xmake 将全部源
    编入单一 `demo` 可执行程序，顶层 demo.c 的 main 串行调度各模块入口）
  - 可执行入口（N_runner）: 97（`demo` 无参数运行输出注册 testname 清单；其余 63 项为无独立
    入口的辅助/实现源，随入口一同编译执行）
  - 实际执行: 97/97 入口全部执行（build() 内逐入口 `demo <testname>`，stdin=/dev/null，
    20s 超时保护，逐项输出 UPSTREAM-DEMO 进度行与 LEDGER 汇总行）
  - 执行结果: PASS 84 / FAIL 7 / TIMEOUT 6（2026-09-20 真机实测，与 conan-create 日志同源）。
    非 PASS 逐项分类：FAIL — memory_check（rc 133/SIGTRAP：上游内存自检断言触发 core dump，
    演示自身检查行为）、network_ping / network_unix_echo_client / network_unix_echo_server /
    platform_poller_client / platform_poller_process / platform_poller_server（rc 255，示例自身
    失败码：依赖 ICMP/外部网络、unix 域套接字、子进程 poller 等环境能力，OHOS 真机不可用或受限）；
    TIMEOUT — network_whois、platform_event、platform_lock、platform_semaphore、
    platform_poller_fwatcher、platform_poller_pipe（按设计阻塞等待外部触发，20s 保护终止）
  - 消费者测试（N_consumer）: test_package/test.c 1 个程序，真实调用 tb_init/tb_snprintf/tb_strcmp/tb_malloc/
    tb_memset/tb_free/tb_exit，3 项断言（初始化、格式化往返、核心分配器读写回验），链接 libtbox.a，退出码断言
- packaging: make install 布局 include/tbox/** 与 lib/libtbox.a；cpp_info.libs=["tbox"]（demo 源不进包，仅构建期执行）。
- API 备注: tb_init 是双参宏 (priv, allocator)，tb_exit() 零参，small 模式核心库无 tb_a2n（位于可选模块）——
  消费者测试只使用核心确定 API。
- 已知限制: 上游默认（small 模式）模块集；如需 xml/zip/regex 等模块应显式开对应 --xxx=y 重打包。
  上游示例执行 13 项非 PASS（FAIL 7 / TIMEOUT 6）均为环境能力或示例自身行为所致（见测试账本分类）。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-17 05:21（2026-09-20 GLM-49 整改重验，conan create rc=0）
**最终状态**: built
