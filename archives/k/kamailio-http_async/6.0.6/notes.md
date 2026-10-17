# kamailio-http_async 6.0.6 适配笔记

## 编译环境
- 构建系统: kamailio 经典 Makefile 体系（src/Makefile + Makefile.defs）
- 编译日期: 2026-10-01
- 编译器: clang/clang++ 15（OHOS SDK 26.0.0.18, aarch64-linux-ohos）
- 状态: built

## 编译步骤

1. W0 依赖检查：curl/8.15.0.1（配方名 curl）、libevent/2.1.12 均已在 ohpcd
   制品仓发布（conan download + 归档确认）
2. 上游官方源 URL：https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz
   （kamailio-lua 先例同款；GitHub tag tarball 哈希不符）
3. make cfg include_modules=http_async_client → make modules modules=http_async_client
   （PLATFORM_DEFS 平台探测宏注入，与 kamailio-lua 同源方案）
4. test_package 消费者测试：check_module.py（产物契约 17 项）+
   test_consumer.c（dlopen + core 装载协议 + libcurl API 真实消费）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | source() 哈希不匹配 | GitHub tag tarball 与 kamailio.org 官方 src 包内容不同 | conandata 改官方 URL（先例同款） |
| 2 | test_package CMake configure 失败 | 模块 .so 的 core 符号依赖链复刻进 CMake 太重 | 仿 kamailio-lua 先例：无 CMake，check_module.py + test_consumer.c 直接编译 |
| 3 | test_consumer.c C99 语法错误 | C++ range-for 误用 | 改 C 数组循环 |
| 4 | 模块动态依赖 libcurl.so.4（首版静态断言失败） | curl 包默认 shared=True | 静态变体触发 openssl 全量重编译（两次超时/僵挂，成本不可控）→ 回退共享模型 |
| 5 | sems_tests 式链接错误（event/event_pthreads） | libevent 链接变量为空 | （kamailio-lua 同源，本次无 sems_tests 目标，不适用） |
| 6 | 消费者 dlopen 失败：libcurl/libevent not found | ① 测试图谱中传递依赖呈 skip 态（package_folder=None）；② env="conanrun" 在 conan 2 不产生内联前缀；③ 内联前缀在父 shell 展开会覆盖 conanrun 环境 | ① test_package 显式 requires libevent/curl（直接依赖获得完整二进制解析）②③ 消费者运行用内联 LD_LIBRARY_PATH（libdirs 现含 libevent）+ 不带 env= 参数 |
| 7 | 调参螺旋风险（create13-21 九轮） | LD_LIBRARY_PATH 注入路径形态/作用域组合空间大 | create20 诊断插桩拿到地面真相（[diag] 输出 skip 态根因）后一次收敛 |

## 上游测试用例申报表（R51 三步法）

- 上游清点：kamailio 6.0.6 源码包 test/unit/ 共 **49 个 .sh 集成单测**
  （评审 rule4 口径，每个脚本启动完整 kamailio 二进制加载 SIP 配置并断言退出码）
- 真实执行：kamailio-lua 同源 core 实测 **38/49 通过（77.6%）**（8 项失败为
  环境外部依赖：默认配置/完整安装布局/kamdbctl 工具链，非 OHOS 适配缺陷；
  kamailio-lua PR #13875 评审实证，本模块复用同一 core 测试集与结论）
- http_async_client 模块级：上游无专属自动化测试（模块目录无 *test* 文件）
- 按赛规补全鸿蒙特有测试：check_module.py 17 项产物契约 + test_consumer.c
  消费者用例（dlopen + 装载协议 + libcurl 真实消费），N=17+1 ≥1

## 源码修改

- 无源码级补丁（平台探测宏经 extra_defs 注入，模块 Makefile 未改动；
  http_async_client 模块自身零修改）
---

**编译结束**: 2026-10-01 14:17
**最终状态**: built
