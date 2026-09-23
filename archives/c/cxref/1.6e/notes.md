# cxref 1.6e 适配笔记

## 语言判定说明（R47，重要）

lang_detect.py 首跑报 `task=cpp(默认), detected=mixed → env_unsupported`，`--lang c` 重跑仍报
mixed。经实证为分母污染的假阳性，判定依据：

- 统计的 35 个"源文件"含 contrib/ 下 9 个 perl + 1 个 python 与 doc/ 下 1 个 perl（FAQ-html.pl，
  被 doc/Makefile.in 的 faq-html 目标引用、挂在 docs 构建链，属文档生成辅助工具）。
  除该文档辅助外，其余 .pl/.py 均位于 contrib/（emacs 插件、第三方小工具），不参与主程序构建与安装。
- 按 R47 边界规则"辅助脚本不算主体"，主体为 C：src/ 15 个 + cpp/ 4 个 + query/ 3 个 = 22 个 C 文件
  （另有 1 个根目录 ChangeLog.pre-1.6.cpp 为历史变更日志，非源码），主体 C 占比 >95%。
- 任务声明语言为 c（平台任务 6960、登记表一致），构建系统为 autoconf（configure.in 老式命名，
  lang_detect 未识别报 none，亦为工具盲区）。
- 结论：detected=c，与任务语言匹配，继续适配主流程。本节即为该判定的证据留存。

## 编译环境
- 构建系统: autotools（autoconf-2.13 时代 configure + 手写 Makefile.in，非 automake）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（OHOS SDK llvm）
- 状态: built

## 编译步骤

探索阶段（设备真机，R1 探索模式）：

```bash
cd ~/builds/cxref-1.6e.work
# E011：顶层与嵌套 cpp/configure 的 umask 077 → umask 022
sed -i 's/umask 077/umask 022/g' configure cpp/configure
# 老 configure 认 $CC 不认 clang 按名查找
export CC=clang
./configure --prefix=$HOME/tmp/cxref-explore
make -j1 && make install
# 验证：安装后 cxref -html sample.c 生成 HTML 交叉引用，cxref-cpp defines 命中
```

配方固化：两个 umask 修正经 `refresh-patch --auto` 固化为 patches/000{1,2}（strip:1）；
build() 以 `unset CONFIG_SHELL && ./configure --prefix=<最终包目录>` + `make -j1`；
package() 直接 `make install`（prefix 即包目录，无需 DESTDIR）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `no acceptable C compiler found in $PATH` | autoconf-2.13 的 AC_PROG_CC 只按名字试 gcc/cc 等，不认 clang | AC_PROG_CC 尊重 $CC，经 AutotoolsToolchain 环境注入 CC=clang |
| 2 | `can't create ./confXXXX/subs1.awk: Permission denied`（顶层与嵌套 cpp/configure 各一次） | configure 以 umask 077 建临时目录，HMDFS UID 映射导致当前进程不可写（E011） | 两个 configure 内 umask 077 → umask 022，固化为 0001/0002 补丁 |
| 3 | conan 内 configure 报 `working directory cannot be determined` | 同 ddpt：profile buildenv 的 CONFIG_SHELL 指向 hnp bash，其 getcwd 在 HMDFS 上 EPERM（E386 同域） | configure 前 `unset CONFIG_SHELL` |
| 4 | 安装后 `cxref -html` 报 cxref-cpp 找不到 `cxref-cpp.defines` | cpp/Makefile.in 把 `$(datadir)/cxref-cpp.defines` 绝对路径烧进 cxref-cpp 二进制；DESTDIR 安装或 prefix 与实际位置不符即断链 | configure `--prefix=<最终包目录>` 且原位安装（不 DESTDIR），bin/ 与 share/ 自洽；包内无共享/系统前缀注入 |

## 上游测试清点（R51）

- 上游无自动化测试套件：顶层与各子目录 Makefile.in 均无 check/test 目标（all: programs docs，
  install: programs）；无任何测试注册入口。N_static = 0（如实申报）。
- 消费者测试：test_cxref.c（1 个程序，N_consumer=1）驱动安装后的 cxref 二进制：
  ① `-html` 处理样例 C 文件：退出码 0 + sample.c.html 生成 + 内容含被引用函数名 add；
  ② 未知选项 `--version`：退出码 1 + usage 横幅含 `Version 1.6e`；
  ③ 缺失输入文件：输出 `Cannot access the file`（注意：上游对坏文件以 rc=0 退出，属上游行为，
     测试如实不断言退出码，只断言错误消息）。
  共 6 项断言，全部在设备真机探索阶段实证。

## 依赖版本

无第三方依赖（构建期需 bison/flex，OHOS 工具链镜像自带于 /data/service/hnp/bin）。

## 验证结果

conan-verify（2026-09-11 设备真机，8 道门禁全过，报告 `reports/conan-verify-report.md`）：
- G2 conan create 成功（日志 `reports/conan-create.log`）。
- test_package 实际执行，6/6 断言通过（日志同上，`PASS: ... × 6` + `all cxref behaviour checks passed`）：
  1. `cxref -html sample.c` 退出 0、生成 sample.c.html 且内容含被引用函数 add；
  2. 未知选项 `--version` 退出 1 且 usage 横幅含 `Version 1.6e`；
  3. 缺失输入文件输出 `Cannot access the file`（上游 rc=0 行为如实断言消息）。
- 测试账本：N_static=0（上游无测试套件，如实申报）；N_consumer=1（test_cxref 程序），N_assertion=6（括注）。
- finish/W3 本地 CI 模拟 100% 通过（`reports/w3-local-ci.log`），conandata.yml 官方 URL 还原确认。

## 路径 A/B 判断（§6.2，2026-09-11）

**结论：纯路径 A，不走路径 B。** 判断依据：

1. **证据门槛核对**：两个补丁均为既有条目 E011 的直接应用；CONFIG_SHELL 问题命中既有条目 E386
   （同域，ddpt 包同日实证），无新错误签名。
2. **拟沉淀知识主题核对**：cxref-cpp datadir 烧死路径问题属单包上游设计（--prefix 原位安装的
   常规对策），无跨仓库复用价值；语言判定的分母污染为工具实现盲区，已回填软件级 manifest 供
   知识库核对，不构成新知识条目。
3. **知识库查重结论**：本次无新增知识草稿；G0/引擎命中均为既有条目。
4. **真实验证证据**：设备真机 6/6 消费者断言通过（见上"验证结果"，补于 conan-verify 后）。

## 注意事项

- 安装产物：bin/ 下 cxref（cxref-inst 启动器）、cxref-cc（包装脚本）、cxref-cpp、cxref-cpp-configure、
  cxref-query；share/man/man8 cxref.8 + man1 三页；share/cxref/cxref-cpp.defines。
- cxref 运行时经 PATH 查找 cxref-cpp（cpp_info.bindirs=["bin"] 保证同包可见）。
- 贡献目录 contrib/（emacs 插件等）与 doc/ 文档不参与构建，不进入安装产物。
