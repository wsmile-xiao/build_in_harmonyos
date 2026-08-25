# boxes 2.3.1 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile → src/Makefile，递归 out 目录构建）
- 编译器: clang 15（从 Conan conf 获取）
- 构建工具: flex / bison（使用真机 /data/service/hnp/bin 自带的，不声明 tool_requires）
- 运行依赖（OHPCD Conan 包）: libunistring/1.0、pcre2/10.45.1（libpcre2-32）、ncurses/6.4（宽字符）
- 状态: built（真机预检通过）

## 构建步骤
1. `conan create . -pr:h=ohos -pr:b=ohos --build=missing`（ohos profile）
2. recipe 在 source_folder 内执行 `make -j1`（上游 in-source 构建，产物 out/boxes）
3. 产物 out/boxes 用 binary-sign-tool 签名（.codesign）
4. 构建树复制到可写工作区（/data/storage/el2/base/haps/entry/files/boxes-conan-tests/2.3.1），强制重签 out/boxes，运行上游测试

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan conf `tools.build:compiler_executables:c` 报错不存在 | 该 conf 是 dict，key 为 `c` | 用 `self.conf.get("tools.build:compiler_executables")` 取 dict，再取 `.get("c")` |
| 2 | include/lib 路径重复拼接（`/p/storage/.../p/include`） | cpp_info.includedirs 已是绝对路径 | 用 `os.path.isabs` 判断，绝对路径直接用 |
| 3 | 构建树 HMFS 上执行 ELF 报 Operation not permitted | HMFS 不允许 exec 未签名 ELF | 复制到可写工作区 + binary-sign-tool 签名 |
| 4 | 复制后旧 .codesign 使二进制仍不可执行 | HMFS 复制的旧签名失效 | force 重签（--remove-section .codesign 再签名） |
| 5 | 绘制路径报 'terminals database is inaccessible'，exit 1 | boxes 经 ncurses setupterm 检测色深，无 TERM+TERMINFO 时绘图失败 | 测试 env 设 TERM=xterm，TERMINFO/TERMINFO_DIRS 指向 ncurses 包 share/terminfo |
| 6 | 测试脚本 `set -u` 引用未定义 `$PWD` | conan/ohos 子进程 env 不导出 PWD | 测试 env 显式设 PWD=test_dir |
| 7 | 链接需 -lncurses 但 OHOS ncurses 包只出 libncursesw | ncurses 宽字符变体 | 补丁把 `-lncurses` 改为 `-lncursesw` |
| 8 | github 源码下载超时 | 设备访问 github 不稳 | conandata.yml URL 加 gh-proxy.com 镜像前缀，官方源兜底 |
| 9 | 赛方 CI 上 179 个用例报 `sed: bad regex '****...'` | 赛方 worker 的 sed 是 toybox，不认 GNU 扩展 `\b`：testrunner.sh 的 `/^:EXPECTED\b.*$/` 永不匹配，sed 范围越过 :EXPECTED 段把框线 `/****` 混进 filter 文件 | 补丁 0002 将其改为 POSIX 等价的 `/^:EXPECTED/`；同时把 173_help_text.txt 的 `\w` 改为 `[[:alnum:]_]`。只改测试框架解析 fixture 的方式，不动任何用例与期望输出 |
| 10 | CI-019 编译失败：config.h 无 OHOS 分支，bionic 需要 _GNU_SOURCE 暴露 strdup/strcasecmp | config.h 的 `#if defined(__linux__) || defined(__GLIBC__) || defined(__GNU__)` 未覆盖 `__OHOS__`，fall through 到 `_POSIX_SOURCE` (POSIX.1-1990)，clang 隐式声明 strdup/strcasecmp 报 error | 补丁 0003 将 OHOS 合入 Linux 分支：`|| defined(__OHOS__) || defined(__OHOS)` |

## 上游测试接入（真机实测）
- black-box 套件：`cd test && bash testrunner.sh --suite` → **184 tests executed, 184 successful, 0 failed**
- sunny-day 套件：`cd test && bash test-sunny-days-all.sh` → **216 tests executed, 216 successful, 0 failed**
  （72 个设计 × create/mend/remove 三个操作）
- 合计 **400/400 通过**。
- 计数解析自各 runner 的 "N tests executed, M successful, K failed" 末行。
- 结果持久化为包内 res/upstream_test_result.json，test_package 阶段读取并裸 print 输出 HMBS_UPSTREAM_TEST_RESULT 标记。

## utest 套件（未接入 conan create）
- utest/ cmocka 套件：main.c 注册 167 个单元测试函数，需单独编译 unittest 二进制
  （`make -C utest BOXES_PLATFORM=unix utest`，链接 -lcmocka --coverage）。
- 未集成进 conan create；已在 MANIFEST / PR 补充说明如实披露。

## test_package（消费者验证）
- test.sh 4 个真实用例：echo 画框、-d shell 设计、boxes -r 移除、--version 含 2.3.1
- 输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记。

## 验证结果（真机实测）
```bash
echo "Hello World" | boxes                       # 画框 ✅
echo "Test" | boxes -d shell                     # shell 设计 ✅
echo "Hello" | boxes | boxes -r                  # 移除盒子 ✅
boxes --version                                  # boxes version 2.3.1 ✅
```

## 注意事项
- boxes 依赖终端色深检测（ncurses setupterm），非交互/无 TERM 环境下绘图需 TERM=xterm + TERMINFO。
- 需要一个源镜像（gh-proxy.com）应对 github 下载不稳定。
- 需 flex/bison 构建工具；首次适配 pcre2-32 需 pcre2/10.45.1（启用了 enable-pcre2-32）。