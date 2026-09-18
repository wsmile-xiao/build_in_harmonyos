# psocksxx 1.1.1 适配笔记（HarmonyOS PC · autotools + CppUnit TAP 测试）

## 定位
- 产出静态库 libpsocksxx.a + include/psocksxx/ 头文件（C++ POSIX socket 封装）。
- 上游 autotools + libtool；GitHub tag archive 无 configure，build() 内 `autoreconf -fi` 自举。
- 上游自带 CppUnit 测试套件（test/，TAP 输出），本包在 build() 中真实执行。

## 源
- https://github.com/uditha-atukorala/psocksxx/archive/refs/tags/v1.1.1.tar.gz
- sha256: 1524eb0b33eae2db70ea21a5817d952bbe872ca16ff23e946c4e54a6c823a645

## W0/W0b
- preflight_check.sh：配方无运行时依赖，通过。
- 历史归档 archives/p/ 无 psocksxx 历史配方（本包为首配）。
- lang-preflight：detected=cpp（25 文件 100%），构建系统 autotools，通过。
- 构建期依赖（不入包）：automake/1.18、libtool/2.5.4（CI 沙箱无 autotools，tool_requires 自举，
  与已合入 abiword-plugin-* 同方案）；cppunit/1.15.1（make check 测试专用）。

## 探索构建（真机 conan create 全量验证，6 轮迭代）
1. **E386 shell 根因与修法（本包最重要发现）**：configure 报
   `working directory cannot be determined`。根因不是 getcwd 全局不可用，而是
   **ohos-aarch64 profile 的 [buildenv] 把 SHELL/CONFIG_SHELL 钉死在 hnp bash**
   （ci/conan/profiles/ohos-aarch64:32-33），而 hnp bash 在 HMDFS 构建目录下 getcwd 必挂，
   configure 自举时经 $CONFIG_SHELL re-exec 即死。修法：build() 开头把 generators 目录下全部
   环境脚本中的 `/data/service/hnp/bin/bash` 文本替换为 `/bin/sh`，并同步写 os.environ。
   - **反面教训（新坑）**：不能用第二次 `Environment().vars(self,"build").save_script("conanbuild")`
     覆盖——聚合器会把同名脚本 source 进 conanbuild.sh 形成**自递归**，进程空转、每层重跑
     toolchain 序言直到 `printenv: Argument list too long`，无任何产物。
2. **C++17 移除动态异常规范**：psocksxx（2015）大量 `throw(X)` 声明，profile cppstd=17 下
   nsockaddr 一个文件就 16 个硬错误。修法：`tc.extra_cxxflags.append("-std=c++14")`
   （追加在 profile 的 -std=c++17 之后，clang 取后者），C++14 下该特性仅废弃、仍合法。
3. **AM_PATH_CPPUNIT 静默禁用陷阱**：conan cppunit 包不提供 `cppunit-config` 探针脚本，
   AC_PATH_PROG 找不到 → HAVE_CPPUNIT=false → make check 零执行（正是审查红线）。
   修法：build() 生成最小 cppunit-config shim（--version/--cflags/--libs 指向 conan 包）入 PATH，
   测试被真实启用。
4. **VPATH 目录**：make check 必须在 build_folder（顶层 Makefile 在那儿）而不是 source_folder。
5. package() 删除 libtool .la 与 .pc（烤死绝对路径），保留 include/ + lib/libpsocksxx.a。

## 上游测试账本（R51 五维）
- N_static = 49：7 个 CppUnit 套件头文件中 CPPUNIT_TEST( 声明逐一清点——
  lsockstream 6、nsockaddr 6、nsockstream 5、sockstreambuf 20、socktimeoutexception 3、
  tcpnsockstream 8、udpnsockstream 1。
- N_registered = 1（check_PROGRAMS=tap-runner.tap，runner 数不替代原子用例数）。
- N_executed = 49（TAP 输出 TOTAL: 49，无一跳过）。
- 通过 35 / 失败 14，失败逐条技术原因（均有原始日志/探针证据）：
  - **13 个 local（unix 域）socket 用例**（sockstreambuf_test 的 test_local_* 10 个 +
    lsockstream_test 的 3 个）：OHOS PC 设备**全平台拒绝 AF_UNIX bind()**——补丁把 socket 路径
    移到可写目录后，bind 报 `Operation not permitted`；python3 探针在
    /storage/Users/currentUser/tmp、/data/local/tmp、/data/service/el1 三处可写位置直接 bind
    均被拒（EPERM/EACCES）。属平台策略缺失，非配方可修。
  - **1 个 DNS 用例**（nsockaddr_test::test_constructor_fail）：断言 `nsockaddr("invalid.domain")`
    抛 sockexception，但设备解析器对任意域名做泛解析（探针：`ping invalid.domain` 解析到
    fake-IP 198.18.10.6），异常永不触发。属环境限制，不能反向削弱断言。
- build() 的基线校验：make check 后解析 test-suite.log，断言 TOTAL=49/PASS=35/FAIL=14，
  偏离即抛错（不吞错误，防 CI 环境漂移静默通过）。

## 消费者测试（test_package）
- 1 程序 / 3 断言：以库使用者身份编译链接打包产物，内建 loopback TCP echo 服务线程，
  经 psocksxx::tcpnsockstream + nsockaddr 写读往返，断言回显内容与退出码。
  输出 "psocksxx consumer echo round-trip OK"。

## 路径 B 判断
- 候选知识三条：①profile [buildenv] SHELL 钉 hnp bash 的 E386 根因+env 脚本替换修法
  （经验汇总 §12.38 已有同族权威条目，查重命中）；②conanbuild.sh 二次 save_script 自递归坑
  （新，但最佳归属是经验汇总/检查清单条目）；③AF_UNIX bind 全平台拒绝（平台能力事实，
  适配检查清单条目形态）；④cppunit-config shim 模式（autotools+cppunit 家族可复用）。
- 判定：本轮按**纯 A** 申报——①查重命中；②③④按 §13 分流沉淀至经验文档/检查清单（同一知识
  唯一权威版本），不重复建知识库草稿与 Issue。若审查侧认为②③④满足知识库门槛，可后续按
  知识库扩展流程补报。

## 状态
built —— conan create 真机验证通过（上游 49/35/14 基线校验 + 消费者回环断言全绿）。

---
**编译结束**: 2026-09-18 04:05
**最终状态**: built
