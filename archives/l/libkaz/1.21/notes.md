# libkaz 1.21 adaptation notes

## 源码来源与同源验证链

- 上游权威仓库：savannah nongnu `kazlib.git`（https://savannah.nongnu.org/projects/kazlib/），
  发布 tag `kazlib-1.21` = commit `a2585e85abe6562a6797c5a558ef9f20419293a6`。
- 上游**不发布 tarball**：Savannah 下载区（download.savannah.nongnu.org/releases/kazlib/）
  为空目录，cgit 的 snapshot 功能对该仓库禁用（snapshot URL 返回仓库 HTML 页）。
  因此 conandata.yml 采用 GitHub 自动同步镜像 `GitMirroring/kazlib` 的 tag tarball：
  - 同步性证据：镜像 tag `kazlib-1.21` 指向**与 savannah 官方 tag 相同的 commit SHA**
    （GitHub API tags 接口实测），Git commit SHA 相同即树与历史逐位一致；
  - 确定性证据：`archive/refs/tags` 与 `codeload` 两个端点各下载一次，sha256 均为
    `b6163e9e06e1c55342db7b259693af186e98bc55178db9f28035acea3a225348`（字节一致）；
  - 内容一致性证据：镜像 tarball 解包后与本地 `git clone` savannah 仓库 checkout
    `kazlib-1.21` 的树 `diff -r --exclude=.git` 完全一致。
- 镜像域名不在 PF7 黑名单，为 https 官方同步源；CI 对 github.com URL 自动附加镜像回退。

## 构建方案

- 上游自带手写 `Makefile.gcc`（无 configure/cmake）。配方在 `build()` 中以
  `make -f Makefile.gcc libkaz.a` / `libkaz.so.1.0.0` 两步构建静态库与共享库，
  C++ 测试 `tests/dict-1` 由配方显式编译（见下）。
- 上游 `project` 目标里的 5 个自测驱动规则把头文件作为链接输入
  （`tdict: dict.c dict.h` → `$(CC) -o tdict dict.c dict.h`），GCC 传统上容忍、
  clang 明确拒绝（"cannot specify -o when generating multiple output files"；
  已在本地实测复现）。OHOS 工具链只有 clang，故配方按 Makefile 同款条件
  （同一 CFLAGS + `-DKAZLIB_TEST_MAIN`，tsfx 链接库对象 except.o/hash.o）逐个
  直编译这 5 个驱动——同源码同宏的等价编译，不是自建替代测试。
- **C++ 测试 tests/dict-1 也由配方显式编译**：其一，内建 %.o:%.cc 规则只认
  CXXFLAGS，而上游给 tests/%.o 追加的 `-I$(shell pwd)` 加在 CFLAGS 上，到不了
  这条规则（build 目录布局下 dict.h 不在 tests/ 内必然失配，CI 实测复现）；
  其二，CI worker 的 conan buildenv 会导出自己的 CXXFLAGS（实测 `-fPIC -O2`），
  环境变量会压制上游 `CXXFLAGS ?=` 的推导。配方因此显式内联 CXXFLAGS（取上游
  推导值，即 CFLAGS 滤去 -Wmissing-prototypes），并以 Makefile 同款链接物
  （tests/dict-1.o + dict.o）亲手编译。
- **工具链必须经环境变量传递**：Makefile.gcc 用 `CFLAGS ?=` 读默认值并为目标
  叠加目标专属 CFLAGS；命令行变量赋值会压制目标专属追加（GNU make 语义），
  环境变量则与 `?=`/`+=` 正常叠加。
- CFLAGS 在上游默认（`-Wall -W -Wmissing-prototypes -ansi -O2 -DNDEBUG`）基础上
  仅追加 `-fPIC`：共享库由 `libkaz.a` 经 `-Wl,--whole-archive` 链接（上游 1.21
  的 a2585e8 提交引入），aarch64 下源对象必须 PIC。
- **list 模块并入安装库**：上游 `OBJS := except.o hash.o dict.o sfx.o` 不含
  `list.o`（list 按上游 README 预期由宿主工程直接并入源码），纯 `-lkaz` 消费者
  将缺失 `list_*` API。配方在 `make libkaz.a` 后以库同款旗标补编 `list.o` 并
  `ar rcs libkaz.a list.o`，再由 make 经 whole-archive 链出 `.so`——安装库因此
  覆盖全部五个模块；消费者测试链接并调用 `list_*` 正是对该保证的端到端验证。
  不修改任何上游源文件。
- 工具名取自 Conan conf `tools.build:compiler_executables`（R33），ar/ranlib 由
  编译器同目录推导，不改 PATH。
- 零补丁：无任何源码修改，conandata.yml 无 patches 段。

## 上游测试（R51 三步法）

1. 清点：`Makefile.gcc` 的 `PROGS=tlist tdict thash teh tsfx`（各模块源文件的
   `KAZLIB_TEST_MAIN` main）+ `TESTS=tests/dict-1`（C++ 模板包装测试），共
   **6 个测试程序**；无 ctest/make check 目标。清单记录于
   `test_package/MANIFEST.yml`。
2. 实跑：`build()` 在构建后逐个执行 6 个驱动。交互式 REPL（tlist/tdict/thash）
   以 stdin 脚本驱动真实操作（增/查/删/排序/转储 + 1.21 新增严格上下界）；
   `tsfx` 以 argv 表达式驱动；`tests/dict-1` 自带断言；`teh` 验证嵌套捕获后落入
   **上游设计内**的未处理异常路径（SIGABRT，shell 状态 134）。对每个驱动断言
   退出码与输出标记（成功内容必须出现、失败标记必须不出现），证据在 W3 conan
   create 日志中。
   - **OHOS 平台行为（首轮 W3 实测）**：管道下 stdout 为块缓冲，`abort()` 触发
     崩溃处理（shell 报 Signal 6）时缓冲内容被丢弃，`teh` 的两条 caught 输出与
     cleanup 行无法捕获。断言因此落在可捕获证据上：fflush 过的 `throw exception? `
     提示、stderr 的 `Unhandled exception` 且身份为 `group=99, code=99`——该身份
     只有在内层捕获、重抛、外层捕获全部完成后才可能出现（若嵌套捕获失效，报告的
     将是 `nasty exception` 的 group=1）。macOS 干跑同断言集通过，本地还能看到
     全部四行输出，可作为行为参照。
3. 消费者：`test_package/test.c` 链接安装后的库，走 list/dict/hash 公共 API
   （含 1.21 的 `dict_strict_lower_bound/upper_bound` 与缺失键分支），21 个
   assert，作为鸿蒙特有消费者测试。

## 平台要点

- 纯 ANSI C，仅依赖 libc，无第三方依赖（W0 实测制品仓无 libkaz/1.21 占用）。
- 头文件按上游 `install` 目标布局装到 `include/kazlib/`，消费者以
  `<kazlib/dict.h>` 引用，避免 `hash.h`/`list.h` 这类通用名与并发包冲突。
- `tsfx` 表达式实参需保证可解析（语法错误会 exit 1），选用上游文档风格表达式。
- **1.21 严格上下界的命名与 STL 相反**（源码注释明示）：
  `dict_strict_lower_bound(k)` 返回大于 k 的最小键，`dict_strict_upper_bound(k)`
  返回小于 k 的最大键。消费者测试按此语义断言（本地干跑曾按 STL 语义误断言，
  以实现与 REPL 实测为准修正）。
