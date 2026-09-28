# yder 1.4.20 适配笔记

## 任务来源

- 平台任务 contrib-12282（开源鸿蒙PC专项积分赛），分支 `feat/yder-1.4.20`，2026-09-22 认领（API 留证：pending→assigned）
- 上游：github babelouest/yder v1.4.20，sha256=c1a7f2281514d0d0bba912b6b70f371d8c127ccfd644b8c438c9301a0fd4c5f2
- 语言实测（R47 lang-preflight）：**C**（9 个 .c，主体 100%，cmake）

## 选库核验（§3.2 否决线）

1. 他人已移植：main 档案无 yder；制品仓 conan list "yder/*" -r=ohpcd = 0
2. 语言/构建生态：C + CMake；依赖 orcania（制品仓 orcania/2.3.3 已发布，恰好满足上游 ORCANIA_VERSION_REQUIRED="2.3.3"）
3. 可行性：高（小体量 9 文件日志库）
4. 难度定级：A（纯编译适配，零补丁）

## 降级边界声明

- WITH_JOURNALD 显式关闭（平台无 systemd；上游本就自动探测关闭，此处钉死保证确定性）
- 上游测试（test/yder_test.c）依赖 check 框架与 valgrind，平台均无，无法执行（R51 如实申报）；验证由 test_package 消费者测试承担（console/file 双后端 + 写盘断言 + 级别常量序 + 重初始化，4 项断言）

## 构建要点

- CMake + CMakeDeps（find_package(Orcania)）；上游自有 BUILD_SHARED/BUILD_STATIC 开关与 conan options 显式映射
- 构建期清空 LD_LIBRARY_PATH（lld/libxml2 盾惯例）；不做 strip（llvm-strip 产物 exec 被平台拒绝）

## 编译结束

（设备 conan create + conan-verify 结果见 reports/）
