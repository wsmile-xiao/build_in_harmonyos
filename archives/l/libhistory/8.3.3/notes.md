# libhistory 8.3.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS SDK)
- 状态: built

## 版本语义

libhistory 随 GNU readline 同源同版发布，无独立上游 tarball：

- 源码基线：readline-8.3.tar.gz（https://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz，
  sha256 fe5383204467828cd495ee8d1d3c037a7eba1389c22bc6a041f627976f9061cc）
- 官方补丁：readline83-001/002/003（https://ftp.gnu.org/gnu/readline/readline-8.3-patches/）
- 8.3.3 = 基线 + 前 3 个官方补丁，沿用官方 readline-8.2.13 的「基线.补丁数」命名惯例

官方补丁为 context diff 格式，而 Conan 2 的补丁解析器仅支持 unified diff
（直接声明官方原文件会在 conan create 报 "Failed to parse patch: no patch data
found"，W3 实测），故转换为语义等价的 unified diff：用 context-diff 解析器
解析官方原文件（覆盖官方混用的分开块/合并块两种 hunk 格式），old 块与干净
readline-8.3 源码逐行匹配定位（允许官方 -patched 行号与逐补丁应用间的偏移），
new 内容由 difflib 生成 unified hunk；回验为双重量化：①git apply 三个补丁到
干净源码后的每个文件与解析所得 new 内容逐字节一致；②与官方补丁逐步应用语义
对照（W4 审计复核通过，含官方惯例的 patchlevel 计数更新 0→1→2→3）。
readline83-003 共三段：input.c（反向 i-search SIGINT 段错误：删除
READLINE_CALLBACKS 条件编译包裹、SIGINT 分支去掉 else 与 RL_STATE_CALLBACK
条件并新增注释）、isearch.c（_rl_isearch_cleanup 重构：RL_UNSETSTATE 前移、
cxt==0 提前返回）、patchlevel（2→3）。
三个官方补丁只改 readline 行编辑库（input.c/display.c/isearch.c）与
patchlevel 计数文件，不改 history 源文件，但作为 8.3.3 版本定义完整应用，
保持与上游 8.3.3 状态一致。

## 上游测试清点（R51）

| 项目 | 清点结果 |
|------|----------|
| tests/ 目录 | 无（`ls tests` → No such file or directory） |
| Makefile check 目标 | 存在但为空目标（Makefile.in:347 `check:` 无命令体） |
| ctest 注册 | 无（源码树无 CMakeLists.txt） |
| pytest 注册 | 无 |
| examples/ | 演示程序（histexamp.c 等，非断言测试套件） |

结论：上游无自动化测试套件，`make check` 为空操作。本包测试由 test_package
自行实现（9 项断言，直接调用 libhistory API，不链接 readline 库）。

## 编译步骤

conan create（OHOS aarch64 profile）：
1. get() 下载 readline-8.3.tar.gz 并解包（strip_root）
2. apply_conandata_patches 按序应用 4 个补丁（readline83-001/002/003 + config.guess）
3. sed 修复 configure 的 umask 077 → 002（HMDFS 上 config.status 的 mktemp 目录写入受限）
4. ./configure --enable-static --disable-shared（CFLAGS 追加 -fPIC -O2）
5. make -j1
6. make install 后仅保留 history 组件（lib 删除 libreadline*、pkgconfig 删除 readline.pc、不打包 share/）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 上游 config.guess 无 OHOS 分支 | 0001-config.guess.patch（与 readline 8.3 相同） |
| 2 | configure 在 HMDFS 上 config.status 临时目录创建失败 | umask 077 阻止 mktemp 目录内写入 | sed 改 umask 077 → 002 |
| 3 | 静态库链入下游共享库报 relocation 错误 | OHOS musl 默认 BIND_NOW | CFLAGS 追加 -fPIC -O2 |
| 4 | .so 污染 /lib、/lib64 风险 | readline 系统同名库族 (R26) | --enable-static --disable-shared |

## 源码修改

- readline83-001.patch：官方 readline83-001 的 unified 等价转换，input.c 事件钩子等待输入死循环修复 + patchlevel 0→1
- readline83-002.patch：官方 readline83-002 的 unified 等价转换，display.c rl_save_prompt 后 NULL 解引用修复 + patchlevel 1→2
- readline83-003.patch：官方 readline83-003 的 unified 等价转换（input.c + isearch.c + patchlevel 2→3），input.c 反向 i-search SIGINT 段错误修复、isearch.c 清理函数重构
- 0001-config.guess.patch：config.guess 添加 HarmonyOS 检测分支（本适配补丁，unified 格式）

## 依赖版本

无（history 库不使用 termcap/ncurses；readline 行编辑库部分才需要 curses）。

## 打包范围

- lib/libhistory.a（静态，-fPIC）
- lib/pkgconfig/history.pc（readline.pc 已删除）
- include/readline/ 头文件全集保留（history.h 依赖 rltypedefs.h、rlstdc.h、rlconf.h 等；
  消费者 `#include <readline/history.h>`）。三个官方补丁不改头文件，本包头文件与
  readline/8.3 逐字节一致，消费者同时依赖两包时 include 路径合并无内容冲突
- share/（man/info 文档）不打包

## 注意事项

- 本包只交付 history 组件；需要行编辑（readline 库）的消费者应依赖 readline 包
- 若上游后续发布 readline-8.3.3 合并 tarball，可切换 sources URL 并保持 sha256 校验

## 制品基线差异说明（2026-09-19）

W3/conan-verify 每轮验证使用随机命名的 ws/tmp 私有 CONAN_HOME，构建目录路径随轮次
变化并嵌入 libhistory.a 的归档成员元数据（ar 时间戳/构建路径），同源码逐轮产物哈希
不同属预期。conan-verify L5 提示：同源码重验出现制品差异时可删除 reports/baseline.json
重立基线（语义等同首轮）。2026-09-19 第二轮验证与首轮基线出现 lib/libhistory.a 差异
（+0 -0 ~1，构建路径差异），已按该提示重立基线并记录本节，无实质性制品变化。
