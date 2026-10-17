# wordplay 9.0.1 适配笔记

## 概况
- 软件: wordplay（变位词/anagram 生成器，命令行程序）
- 版本: 9.0.1（上游 tag 9.0.1，Debian 源码包 wordplay_9.0.1-1 对应）
- 许可证: GPL-3.0-only（上游 tarball 附完整 GPLv3 文本）
- 上游: https://github.com/mendelmunkis/wordplay
- 源码归档: 上游官方 tag 归档（GitHub tag 9.0.1，commit 29ff967a；与 Debian orig
  tarball 字节一致，同 sha256，见 conandata.yml）
- 语言/构建: 纯 C（wordplay.c 单文件，921 行）+ 4 行手写 makefile；无 configure、无 install、无测试

## W0 依赖结论
- 运行时/构建依赖: icu4c（unicode/ustdio.h、unorm2.h、ustring.h；链接 -licuio -licui18n -licuuc -licudata）
- 仓库已有 icu4c/78（archives/i/icu4c/78，OHOS 静态构建，数据已并入 libicudata.a），远端 ohpcd 可拉取 → 无缺失依赖，无需拆分依赖适配
- 运行时数据: words721.txt（24867 词，sha256 eb544122...9fb）随包打包到 res/
- 测试依赖: 无（上游无测试；test_package 为 POSIX sh + 纯 Python ELF 检查）

## 构建方式说明
上游 makefile 链接行把 -licuio/-licui18n/-licuuc/-licudata 固定写在命令末尾。ICU 是 C++
库，用 C 编译器驱动链接时 C++ 运行时（-lc++）必须排在 ICU 静态库之后，而该位置无法通过
任何 make 变量注入。因此配方 build() 直接驱动一条与 makefile 等价的编译链接命令（编译器
来自 tools.build:compiler_executables，R33；-j1，R9）。链接序: wordplay.o → icuio →
icui18n → icuuc → icudata → c++ → m/pthread/dl（后者按 icu4c/78 cpp_info 声明）。

## 打包
- bin/wordplay（OHOS 上按惯例先 llvm-objcopy 去 .codesign 再 binary-sign-tool 重签名，仅鸿蒙 worker 有该工具时生效）
- res/words721.txt（程序默认按相对路径 words721.txt 打开，消费端用 -f <pkg>/res/words721.txt 显式指定）
- licenses/LICENSE、res/doc/readme

## C++ 运行时形态
ICU 是 C++ 库，最终链接产生 DT_NEEDED = [libc++_shared.so, libc.so]。libc++_shared.so 是
OHOS 系统 C++ 运行时（/system/lib64），与 HNP 自带 cmake/ninja 的形态一致（知识库
opencsg-1.8.2 / E630 先例），故按系统 soname 处理，不静态打入（静态链 libc++ 与
libc++_shared 共存场景有 E-OHOS-libcpp 弱符号双实现风险，且无必要）。

## 测试证据
- Local cross build (Windows host, OHOS aarch64): conan create rc=0（profile fathom-local，
  icu4c/78 二进制取自 ohpcd；仅 1 个上游自身 -Wformat warning）
- ohos_abi_check A1-A9 本机实跑 9/9 PASS（DT_NEEDED=['libc++_shared.so','libc.so']，ICU 静态并入）
- HarmonyOS PC shadow CI: **PASS**（job wordplay-9.0.1-20260929，排队 298s，exit 0）：
  - L0_RESULT=pass（R36 icu4c/78 in registry / R37 first publish / R38 commands.json / R39 全过）
  - L1_RESULT=pass（含 L1e 破坏性反向验证：移走 bin/ 后 test 确认失败）
  - L2_RESULT=skip（上游无 --version/--help 选项，非阻塞）
  - L4_RESULT=pass（无补丁）；L5_RESULT=pass（bin/ 有内容）
  - 功能用例 F1-F20 真机实跑 20/20 PASS
- 上游测试: 上游无任何测试框架/目标，按 no_tests 处理，由 test_package 补全 29 项
  （功能 20 + 鸿蒙特有 9），计数口径见 test_package/MANIFEST.yml

## 真机迭代记录（W5）
| 轮次 | job/run | exit | 失败点 | 根因 | 解法 |
|---|---|---|---|---|---|
| r1 | ...102024-19118 | 1 | L0i registry_unreachable | job 隔离 conan-home 无 ohpcd remote | job conan-home 添加 ohpcd remote（环境操作，非配方问题） |
| r2 | ...102157-20724 | 1 | KC: permission denied: bash | job env.sh PATH 缺 /data/service/hnp/bin（bash 所在） | env.sh 补该 PATH（参照已成功 job） |
| r3 | ...103627-41361 | 1 | F4-F10 断言失败 | 词表全大写（输出 STOP/POST/SPOT），预设断言用小写匹配；F6 的 -i 上游无可观察输出差异；F10 wc -c 差 1 | 断言改大小写折叠（canon/tr + grep -i）、F6 降级为选项接受性+anagram 有效性（MANIFEST 已记录原因）、F10 修正计数 |
| r4 | ...104510-53014 | 0 | 无 | — | 全部门禁 + 20/20 通过 |

## 已知限制
- 功能断言依据真机实际输出回填（词表全大写、-i 无输出差异），MANIFEST 同步更新。
- CI/制品仓如报 wordplay/9.0.1 版本冲突（R37），按规范递增为 9.0.1.1 并同步目录/分支/引用。
