# nift 3.0.3 适配笔记（W3 已通过，.ci-result.json exit_code=0）

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-09-04
- 编译器: clang/clang++（OHOS SDK llvm 15.0.4，aarch64-linux-ohos）
- 目标平台: HarmonyOS PC (aarch64 / OHOS)
- 状态: built（conan-verify 全门禁 PASS + W3 本地 CI 通过，.ci-result.json exit_code=0；
  制品实际上传发生在 PR 合并后 CI release 流水线）

## 软件概述
nift（nifty-site-manager / nsm）是 C++ 跨平台静态网站生成器，自包含项目：
内嵌 Lua-5.3/LuaJIT、exprtk、rapidjson、hashtk。构建产物为命令行可执行文件
`nift` 与 `nsm`（同一二进制，nsm 为原名，Makefile 链接后 cp nift）。

## 编译步骤
```bash
# 默认（沿用上游 Makefile 的 -O3 与平台宏）
make CC=<clang> CXX=<clang++> LUA_VERSION=5.3 -j8
# 内存受限机可 NIFT_OPT=-O0/-O1 覆盖 CXXFLAGS、NIFT_JOBS 调并行度
# 打包（package() 内执行，不依赖上游 install 的 chmod）
copy nsm / nift -> <pkg>/bin/
```

关键点：
1. nsm Makefile 未设 LUA_VERSION 时默认编译内嵌 **LuaJIT**。显式传
   `LUA_VERSION=5.3` 切到内嵌 **Lua-5.3** 的 `generic` 目标（本机 uname 返回
   HarmonyOS，走 Makefile 通用 *nix 分支；generic 仅在 `make-lua` 的
   `5.3 *` 通配分支命中）。Lua 5.3 适配成本远低于 LuaJIT。
2. Lua-5.3/src 子 Makefile 硬编码 `CC= gcc -std=gnu99`；把 `CC=`/`CXX=` 放最
   外层 **make 命令行**，经 MAKEFLAGS 自动传播到子 make 即可覆盖。
3. 上游 install 目标执行 `chmod 755` + `mv` 到 `${DESTDIR}${PREFIX}/bin`。
   本机 HMDFS 对部分 inode 拒绝 chmod（E046）会中断 install，因此配方
   `package()` 用 `copy2` 把 nsm/nift 拷入包内 bin/（语义等价、不依赖 chmod）。
4. 链接仅依赖系统 libc / libc++_shared.so（原生 OHOS 运行时）；liblua 静态
   内嵌进二进制。编译期无外部 conan 依赖。
5. 上游无 `make check`/测试目标，官方 tag 无 tests/ 目录——以 test_package
   的 11 项消费者功能断言代替（真实执行打包的 nift/nsm，R34）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 默认走 LuaJIT 构建 | 顶层 BUNDLED 分支优先 LuaJIT | build() 显式传 LUA_VERSION=5.3 走 Lua-5.3 generic |
| 2 | Lua 子 make 报找不到 gcc | Lua-5.3/src/Makefile `CC= gcc` 覆盖环境 | CC/CXX 放 make 命令行（MAKEFLAGS 传播到子 make） |
| 3 | 上游 make install 在 chmod 处失败 | HMDFS 拒绝 chmod（E046 平台限制） | package() 直接 copy nsm/nift 到 bin/，不依赖 chmod |
| 4 | 无 check/test 目标，无 tests/ | 上游未提供测试套件 | test_package 以 11 项消费者用例（版本/init-html/资源镜像/模板引擎 E2E/增量/Lua/init）真实构建断言代替（R34） |
| 5 | 沙箱内 python 长任务约 60s 被 SIGTERM | AI 沙箱对用户目录 python 进程有时限 | 本地 conan create/verify 用 NIFT_OPT=-O0 NIFT_JOBS=8 压缩到 ~45s 完成；CI 无此限制 |
| 6 | W3 本地 CI (build_and_test.sh) G0e 红 | 上游 main 曾合入根目录 BUILD.gn/oh-package.json 而 G0e 白名单未更新 | 上游已强制更新移除该两文件；本分支已对齐最新上游 main（见 notes 尾部），需在最新 main 上重跑 finish |

## 源码修改
无补丁（patches/ 为空）。构建参数（LUA_VERSION/CC/CXX，可选 CXXFLAGS 覆盖）
均在 conanfile.py build() 内注入，未改动任何上游源文件。

## 依赖版本
- 无外部 conan 依赖（自包含）。
- 内嵌：Lua 5.3.5（Lua-5.3/）、exprtk、rapidjson、hashtk。

## 验证结果
```bash
$ nift --version
Nift (aka nsm) (c)2026 v3.0.3
$ nsm --version
Nift (aka nsm) (c)2026 v3.0.3
$ nift init-html   # 空目录 → 构建 tracked 文件，产出 output/index.html 等
```
- conan-verify 全部门禁 PASS（G0/G1/G2/G3/G4 + L2/L4/L5），最终配方复验 RC=0。
- `conan create` 真实通过（RC=0），内嵌 test_package 11/11 断言全过
  （test_nift.sh：nift/nsm --version；init-html 最小站与静态资源镜像；
  track+自定义模板+build 的站点生成 E2E：模板选中/$[title] 替换/@content 注入/
  多页面；增量构建 hash 模式；内嵌 Lua `nift run`；`nift init` 通用建站）。
- 本机受限沙箱下 conan create 需以 `NIFT_OPT=-O0 NIFT_JOBS=8` 执行才能在
  python 进程时限内完成；CI（release 构建）默认参数即可。

## 交付物
| 文件 | 说明 |
|------|------|
| bin/nift | nift 命令行工具（OHOS aarch64 ELF） |
| bin/nsm  | nifty-site-manager 原名入口（同二进制拷贝） |

## 注意事项
- R38：产物为可执行文件 → 软件级 commands.json 已声明（type=tool，双入口 nift/nsm）。
- R26/R32：本包无系统同名库、无 OS 分支判断；产物为 application。
- R39：conandata.yml 仅写官方 GitHub tag URL（sha256 实测）；镜像 fallback 由
  CI 自动注入（conan-verify E017 也会临时注入并在结束恢复，勿提交 .ghfast-bak）。
- 铁律：patches/ 无平台宏；test_package 为实质消费者测试（PF3/R34）。
- **W3 本地 CI 已通过（.ci-result.json exit_code=0）**：上游 main 曾因合入把
  BUILD.gn/oh-package.json 放进仓库根目录导致 G0e 白名单 Hard Fail（与配方无关）；
  上游随后 force-update 移除该两文件，本分支已 `git reset --hard` 对齐最新
  upstream/main（8e758faaa）。本地为 shallow clone，junk_check 的 incremental
  差分无 merge-base 会回退整仓 full 模式（会误报其它包历史遗留 junk），故 W3
  通过 `JUNK_PR_DIFF=<commit diff>`（仅含本包 10 个新文件，等价真实 PR diff）
  驱动 JC 走 prdiff 模式；CI 侧由 buildbot pr.diff 天然提供，无需该变量。
- 本机受限沙箱对用户目录 python 进程约 60s 会 SIGTERM；本地 finish/conan create
  用 `NIFT_OPT=-O0 NIFT_JOBS=16 TMPDIR=~/tmp TMPPREFIX=~/tmp/zsh` 可在时限内完成。
  CI（release）无此限制，默认参数即可。
---

**编译结束**: 2026-09-04 11:46
**最终状态**: built（conan-verify PASS + W3 本地 CI PASS，.ci-result.json exit_code=0）
