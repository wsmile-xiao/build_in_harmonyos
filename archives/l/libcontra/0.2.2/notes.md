# libcontra 0.2.2 HarmonyOS PC 适配笔记

> 申请人: liucu, 队伍: 龙骑士
> 上游: https://git.alteholz.dev/alteholz/libcontra/
> 状态: 待真机预检 (本轮仅完成未提交工作树, 未 commit/push)

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libcontra |
| 版本 | 0.2.2 (首次适配, 无后缀) |
| 构建系统 | CMake (最低要求 3.7/3.18, 真机 cmake 由 HMBS 统一提供) |
| 语言 | C (约 1458 行 ANSI C) |
| 许可证 | GPL-2.0-only (LICENSE 为 GPL v2; 库头文件声明 version 2, 无 or later) |
| 第三方依赖 | 无 (仅链接系统 libdl) |
| 源码 | Debian pool libcontra_0.2.2.orig.tar.bz2 (顶层目录 libcontra-v0.2.2) |
| sha256 | eb001b3c57e90c8b845c930b442d2de0dc6d2a6c7e8e43ca197ca58de076a3b3 |

libcontra 是连接追踪库: 通过 LD_PRELOAD 预加载 libcontra.so,
拦截并记录 socket/connect/bind/listen/accept/send/recv/setsockopt/
getsockopt/gethostbyname/gethostbyaddr/getaddrinfo/freeaddrinfo/poll/close
等网络函数调用。另产出 libcontra-only-connect.so (仅跟踪 connect)。
两个库均为 SHARED, SOVERSION 1。

## 二、上游测试清点 (R51 第一步)

顶层 CMakeLists.txt 含 include(CTest)/enable_testing() 并
add_subdirectory(testlib); testlib/CMakeLists.txt 共 13 条 add_test():

| 用例 | 命令 | 说明 |
|------|------|------|
| contra_test_start | echo | 首标记 |
| contra_test_pwd | ../../testlib/test_pwd_script | harness 自检 |
| contra_test_server | ./test_server | 二进制直调, 确认构建成功 |
| contra_test_00 | test_server_00 | 基础 server 日志比对 |
| contra_test_01 | test_server_01 | socket() |
| contra_test_02 | test_server_02 | bind() |
| contra_test_03 | test_server_03 | listen() |
| contra_test_04 | test_server_04 | accept()+connect() 双端 |
| contra_test_05 | test_server_05 | recv()+send() 双端 |
| contra_test_06 | test_server_06 | setsockopt()+getsockopt() |
| contra_test_07 | test_server_07 | gethostbyname()+gethostbyaddr() |
| contra_test_08 | test_server_08 | freeaddrinfo()+getaddrinfo() |
| contra_test_end | echo | 尾标记 |

功能用例原理: test_server_common 以 LD_PRELOAD 加载构建出的
libcontra.so, 运行 test_server/test_client (-t N), 把日志与
testlib/log-template/ 下 11 份模板 diff 比对 (比对前 cut -b26- 去
25 字符时间戳, sed 去版本号)。配方 build() 以 cmake.test() 完整
执行全部 13 个, 不跳过 (R51 第二步由真机预检执行并回填数字)。

风险提示 (TODO 载明 tests are flaky): 04/05 双端用例含 sleep 2
时序, 若真机出现偶发失败需按日志个案处理, 不得整体跳过。

## 三、源码修改清单 (配方内字符串修复, 均为 POSIX 兼容, 无 __OHOS__ 宏, R8 合规)

| 补丁 | 原因 | 说明 |
|------|------|------|
| recipe _disable_docs() (原 0001 补丁, 已删) | 顶层 LaTeX 块整体注释 (INCLUDE/SET/ADD_LATEX_DOCUMENT 调用块, 否则宏未定义悬空报错) + 桩 macro(ADD_LATEX_DOCUMENT) 兜底, 哨兵保证幂等; Doxygen 改 QUIET 且 doc 去掉 ALL | 顶层 CMake 无条件 INCLUDE LaTeX 模块并构建手册; libcontra/CMakeLists 以 FIND_PACKAGE(Doxygen) + doc ALL 目标强制构建 API 文档; 真机/CI 无 pdflatex/doxygen, configure 或默认构建失败 | 配方 _disable_docs() 注释顶层 INCLUDE(docu/UseLATEX.cmake)、Doxygen 改 QUIET 且 doc 去掉 ALL (原 0001 补丁因上游文件比预期短打不上，已删除，改走行号无关的 replace_in_file) 选项 (默认 OFF) 包裹 LaTeX 段; Doxygen 改为 QUIET 查找并以 IF(DOXYGEN_FOUND) 包裹文档目标, doc 目标去掉 ALL |
| recipe _fix_install_dirs() (原 0002 补丁, 已删) | libcontra/src/CMakeLists 把 CMAKE_LIBRARY_OUTPUT_DIRECTORY 硬编码为 /usr/lib, INSTALL DESTINATION 亦指向该绝对路径, 会写出包外且污染系统目录 | 删除绝对输出目录设置, INSTALL 改用已 include 的 GNUInstallDirs 的 ${CMAKE_INSTALL_LIBDIR} (相对路径, 进入 Conan 包内 lib/) |
| recipe _fix_test_shebangs() (原 0003 补丁, 已删) | 14 个测试脚本 shebang 为 #!/bin/bash, OHOS 无 /bin/bash (bash 由构建环境经 PATH 提供) | 改为配方在 build() 内探测绝对 bash 路径后逐脚本 pin shebang 为 #!<absolute-bash> (预检显示 env 方式下 10 个 shell 用例仍全挂，仅 echo/二进制通过，故不用 env 依赖 PATH) |
| recipe _fix_out_of_source_tests() (原 0004 补丁, 已删) | 上游测试均为相对路径 (ctest 注册 ../../testlib/..., 脚本互调 ../../testlib/test_server_common, 模板引用 ../../testlib/log-template), 仅在 build/ 置于源码内时成立; Conan cmake_layout 为 out-of-source 构建, 相对路径失效 | ctest 注册改用 ${CMAKE_CURRENT_SOURCE_DIR} 绝对路径; 调用脚本以 SCRIPT_DIR (由 $0 dirname 推导, 相对 $0 亦可正确解析) 定位 test_server_common; test_server_common 以 COMMON_DIR 定位 log-template。被测二进制与被测 .so 仍经 CWD (ctest 二进制目录) 的 ./test_server 与 ../libcontra/src/libcontra.so 定位, 行为不变 |

## 四、打包说明

- 上游 install() 只装两个 .so, 不装头文件; 配方手动把
  libcontra/src/libcontra.h 复制到 include/ (公共 API 唯一头文件)。
- package_info: libs = ["contra", "contra-only-connect"],
  cmake_target libcontra::libcontra, Linux/OHOS 下 system_libs = ["dl"] (R32 写法)。
- 非系统同名库 (contra 不在 /lib//lib64), 保留 .so 动态链接 (R26 不触发)。
- 纯库, 无 bin/ 产物, 无 commands.json (R38)。
- license 字段 GPL-2.0-only, LICENSE 原文装入 licenses/。

## 五、消费者测试 (R34)

test_package/test_libcontra.c 链接 libcontra::libcontra, 7 个真实断言:
libcontra_init 可调用、af2string(AF_INET/AF_INET6) 映射字符串、
sock2string(SOCK_STREAM/SOCK_DGRAM)、oname2string(SO_REUSEADDR)、
一次真实 socket(AF_INET, SOCK_STREAM, 0) 调用。非空壳。

## 六、合规自查 (.gitcode 审查规则)

- R34: test 源文件实调被测 API, 非打印字符串; test() 含 self.run 真实执行。
- R32: 平台判断用 in ("Linux", "OHOS")。
- R33: 编译器经 CMakeToolchain/conf 获取, 无裸 $CC/$CFLAGS; 测试执行经 CONFIG_SHELL bash 包裹。
- R39: conandata URL 为 Debian/Ubuntu 官方池 (非个人 fork/CDN), 三个 URL 同字节同 sha256; 上游 git 主页记入 homepage/url 字段。
- R8/PF5: 配方内修复无平台宏 (仅注释文档构建、重定向安装目录、脚本路径与 TMPDIR)。
- R6: 未改任何生成文件。
- R37: 首次适配用上游版本 0.2.2。
- W2: 本分支仅含 archives/l/libcontra/0.2.2。

## 七、验证记录

- [x] 配方内字符串修复经本地仿真验证 (按补丁上下文重建 mock 源码树, 13 项断言全过, 含幂等性)
- [x] 真机两轮证实录制补丁与 pristine 0.2.2 树行号不符 (0001 hunk3、0002 hunk1 越界 EOF), 故删除全部补丁文件, conandata 无 patches 节, apply_conandata_patches 为 no-op
- [x] test_libcontra.c 的断言字符串与上游实现逐字核对
  (af2string "2 IP protocol family"/"10 IP version 6"、sock2string "1 Sequenced ... "、
  oname2string "Reuse of local addresses is supported"、af2string 缺省返回 "default")
- [ ] 真机预检待 HMBS 后台执行 (conan create + 13 ctest + test_package),
  第二轮预检 pwd 已过、00-08 仍挂，定位为相对 LD_PRELOAD 路径在 out-of-source 下失效，配方在 build() 内定位已构建 libcontra.so 绝对路径并 pin；同时失败时在尾部打印 LastTest.log 供下轮聚焦。第三轮透出真实错误为 test_server_common[63/64] declare 不可用及[71] array 括号语法错误，即 CTest 在 /bin/sh 下执行 bash 脚本；修复改为在 testlib/CMakeLists.txt 注册层面对全部 shell 用例强制经绝对 bash 启动，二进制/echo 用例不动。通过前不 commit、不 push、不建 PR

- [ ] Round-5 真机预检待复跑:同一指纹第3次,改走不同策略.上轮 find_program+STATUS 显示 HMBS_BASH-NOTFOUND 且 configure 内 FATAL_ERROR 熔断,真机能力 shell 仅 /bin/sh、chmod=0、/tmp 只读.本轮取消 configure 期 bash 硬依赖,改用可选探测 HMBS_TEST_SHELL(有 bash 则用 bash,无则 /bin/sh)+14 个 harness 脚本 POSIX 化(declare 去关键字、array 改字符串、[[ 改 []、&> 改写、source 改 .)+TMPDIR 内存 guarded 重定向(消除 test_server_02 无 mktemp 行的 replace 警告)+test_package 改直调优先.不断言删减,不跳过用例.通过前不 commit、不 push、不建 PR

- [ ] Round-6 真机预检待复跑:本轮指纹为 test_server_common[64]rcc/[65]rcs not found + [72] unexpected '('.根因为 V1 版 POSIX 化存在 5 处缺陷:declare 无=变量被削成裸命令;含=数组元素被跳过;declare 带数组提前 continue 未转换;mktemp 替换引入未闭合引号;function 改写丢弃行尾体.本轮改走 V2 加固版 _port_test_scripts_to_sh(数组先于 shlex 提取、裸变量补空串、含=数组一律转字符串、&>保留文件名、function 保留体、新增(( ))/let/shopt/pushd 处理、${name[idx]} 通配)+mktemp 去引号+build 内新增 _dump_harness_diag 打印 50-90 行供下轮定位.不断言删减,不跳过用例.通过前不 commit、不 push、不建 PR

- [ ] Round-7 真机预检待复跑:复核 V2 后仅剩 test_server_common[72] unexpected '(' 单点(rcc/rcs 错误已消失,证明 declare 修复有效).单行正则永远匹配不到跨行数组,故本轮改走新策略:预处理阶段先做反斜杠续行合并,再把多行 VAR=(...)/declare VAR=(...) 按括号配平折叠成单行字符串赋值,另加 VAR[idx]=val 转追加语义;失败尾部同时打印 harness 40-100 行与 /bin/sh -n 门禁结果,做到只读取证不改测试口径.不断言删减,不跳过用例.通过前不 commit、不 push、不建 PR

- [ ] Round-8 真机预检待复跑:门禁证实 Round-7 后仍仅剩同文件同行号 [72] 单点,全部其余 13 个脚本 sh -n 已过,故放弃再补单行正则,改走括号配平与 span 展开新策略:引号感知 _match_paren/_extract_arrays 替代 [^)]* 模式(可穿越 $(...) 嵌套且不碰引号内伪数组);简单命令行的 <(...) / >(...) 展开为 TMPDIR 临时文件中转(setup/teardown,保留 LD_PRELOAD 等行首 env);if/while/until/elif ((...)) 与 ((...)) &&/|| 链转 POSIX test;数组/元素赋值容忍行尾注释;失败尾部新增 60-80 行 FOCUS 紧凑取证.不断言删减,不跳过用例.通过前不 commit、不 push、不建 PR
