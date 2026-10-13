# subunit

subunit 测试结果流协议的 C 绑定(libsubunit)。

- 平台任务:`subunit/1.4.5`(自导入,积分赛-依赖 5 火种)
- 上游:https://github.com/testing-cabal/subunit(tag 1.4.5)
- 形态:C 库(单翻译单元 child.c + child.h);上游 tarball 仅含 autotools 输入,
  配方的 build() 内嵌最小 CMakeLists 包装，上游产品源码零改动；
  cmake/CMakeLists.txt 为可读对照，不是 export_sources 输入。
  原始 C/Check 测试使用已发布的 Check 框架，在任务私有临时目录内完整执行。
- 消费:`find_package(subunit)` → `subunit::subunit`;API 为
  subunit_test_start/pass/fail/error/skip 与 subunit_progress
- 协议成功事件为 `success:`，不是 `ok:`；消费者逐字节验证实际输出。
- 当前目标证据为 subunit-20261005-r005：原始 C 测试 6/6、消费者 1/1、
  鸿蒙专属测试 1/1，并完成释放及任务进程清零；平台 CI 单独回读。
- 许可:Apache-2.0 OR BSD-3-Clause
- 下游:vitrage-dashboard、aetos(声明依赖);Python 绑定(python-subunit)独立任务
