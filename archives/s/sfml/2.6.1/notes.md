# sfml 2.6.1 适配笔记

## 范围

仅构建 HarmonyOS PC 可用的 System 和 Network 模块。

## 平台适配

- 将 HarmonyOS 纳入 SFML Unix/Linux 平台分支。
- HarmonyOS 缺少 `pthread_cancel` 和异步取消配置，线程终止路径不做任何操作（保持 joinable，等待线程自然结束）。
- 禁用 Window、Graphics 和 Audio，避免引入 X11、UDev、OpenGL、OpenAL 等不可用依赖。
- 包内仅保留 System、Network 公共头文件、库和 Conan 组件元数据。
- 链接时强制 `-Wl,--enable-new-dtags`，将 RPATH 降级为 RUNPATH；让 conanrun 的
  `LD_LIBRARY_PATH` 优先于 RUNPATH，避免 test_package 阶段运行时动态库找不到
  （CMake/ld.lld 自动嵌入的相对路径在 package 目录与 test_package build 目录
  不一致时会失效）。沿用 apache-arrow fix(0309c6d3) 同款方案。

## 验证

消费者测试调用 Clock 和 Packet API，验证计时以及整数、字符串序列化。补丁已通过干净上游源码的 `patch --dry-run -p1`。

## 限制

`sf::Thread::terminate()` 在 HarmonyOS 上不能强制终止线程，terminate() 为 no-op（不分离线程，保持 joinable）；调用方应优先使用协作式退出并通过 `wait()` 回收线程。
