# less 710 升级适配笔记（GLM-72，2026-09-22，OHOS aarch64 真机）

## 升级说明
- 归档已有 less/661（上游 greenwoodsoftware release tarball）；本行为 661→710 升级适配，
  conandata.yml 沿用官方 release tarball 源（github archive tarball 无 generated configure，弃用）。

## 配方要点（相对 661 的差异）
- E386/§12.38①：generate() 以 tc.environment() 承接工具链环境后 define SHELL=/bin/sh +
  unset CONFIG_SHELL；build() 用 sh 显式内联执行 configure（pullseq/1.0.2 合入范式），
  --build=aarch64-unknown-linux-gnu 跳过 config.guess 探测。
- conan 2 AutotoolsToolchain 不注入依赖 include/lib：手动把 ncurses cpp_info 的
  includedirs/libdirs 拼绝对路径写进 CPPFLAGS/LDFLAGS（否则 "Cannot find terminal libraries"）。
- E011 umask 077→000 configure 补丁沿用 661。

## 上游测试（lesstest，真实执行）
- less 710 起 lesstest 进入 release tarball，且已挂接 autotools check target：
  `check: ${MAKE} LESSTEST=1 && cd lesstest && make && ./runtest -l less_t lt`。
- N_static = 19（lesstest/lt/*.lt 注册口径）；build() 内 `autotools.make(target="check")`
  真实执行：**RAN 19 tests with 0 errors**（2026-09-22 真机实测）。
- lesstest = 终端仿真测试器（pty + 模拟终端），19 个 .lt 脚本覆盖
  unicode/osc8 超链接/搜索/过滤/表格/中文/彩色条等行为面。

## 消费者测试（test_package/smoke.sh，真实行为断言）
- 4 场景全过：①-F 整页输出内容断言 ②空文件 0 退出+零输出 ③缺文件 stderr 诊断文本
  断言（stdin=/dev/null）④--version 输出 sanity。
- ⚠ 知识点：conan test 的 conanrun 环境把 stdin 接到 /dev/null——less 读到空 stdin
  后正常退出（缺文件场景 rc=0），显示层特性（-N 行号）也不进管道输出。
  CLI 消费者测试断言必须选管道可观测的输出路径与 stderr 诊断，不能断言 rc/显示层。

## 五维账本
- N_static=19（lesstest 注册口径）｜N_registered=19｜N_executed=19｜未执行=0｜N_consumer=1（smoke.sh，4 场景/6 断言）

---

**编译结束**: 2026-09-22 01:40
**最终状态**: built
