# atools-apkbuild-lint 20.2.2 适配笔记

## 上游信息
- 名称：atools-apkbuild-lint —— Alpine aports `community/atools` 的子包
  （`subpackages="$pkgname-doc $pkgname-apkbuild-lint:apkbuild_lint:noarch"`，
  只安装 `usr/bin/apkbuild-lint`）
- 上游项目：atools，https://gitlab.alpinelinux.org/Leo/atools
- 版本：20.2.2（与 Alpine aports community/atools APKBUILD pkgver 一致）
- 许可证：MIT
- 描述：apkbuild-lint 是纯 POSIX/ash shell 脚本 linter（628 行），扫描 APKBUILD
  常见错误并输出 `[ALxx]` 标签行；源自 Void Linux xlint 的 Alpine 移植
- 本包边界：对齐 Alpine 子包——只装 `bin/apkbuild-lint`。源码树中的其他工具
  （aports-lint/initd-lint/secfixes-check/apkbuild-fixer/convert-volatile-source/
  print-go-deps.go）属于主包 atools 或 atools-doc，不在本包范围；
  Go 组件 print-go-deps.go 不参与构建与打包

## 源码包
- conandata URL：
  https://gitlab.alpinelinux.org/api/v4/projects/Leo%2Fatools/repository/archive.tar.gz?sha=20.2.2
- sha256：32e19ed3552c18adc44124b2697070bc173cdbaa1704407e05ddf6a6f97e9f01
- 选型说明：web 归档端点 `/Leo/atools/-/archive/20.2.2/atools-20.2.2.tar.gz`
  挂在 gitlab goaway 反爬墙后，实测 Conan/curl(Mozilla) UA 返回 HTTP 418、
  wget/curl UA 可通过 —— conan source() 无法稳定走 web 端点。改用同一官方
  仓库的 REST API 归档端点（python-urllib 实测可达，两次下载 sha256 一致）。
  已做等价性验证：两个归档的文件树完全一致（66 个文件内容 sha256 与可执行位
  逐项相同）；web 归档 sha512 与 Alpine APKBUILD sha512sums 完全一致
  （63c95e4b...6580），证明 API 归档即官方发布内容。
- lua_source（测试期专用）：https://www.lua.org/ftp/lua-5.3.6.tar.gz
  sha256 fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60

## 构建系统
- 上游用 redo + scdoc（man 页）+ 一个 Go 辅助工具；OHOS 均不需要也不可用。
  本包产物是纯 shell 脚本，无编译步骤；conanfile build() 做 shebang 平台适配 +
  测试期工具准备 + 上游套件执行
- shebang 适配（与已合入 abuild 系列配方同方案）：
  - apkbuild-lint/aports-lint/initd-lint 等 `#!/usr/bin/env ash` → `#!/bin/sh`
    （脚本使用 POSIX sh + local 扩展；mksh/busybox ash/dash 兼容）
  - secfixes-check(Lua) `#!/usr/bin/lua5.3` → `#!/bin/sh` + `exec lua5.3 "$0" "$@"`
    trampoline（解释器经 PATH 解析到配方现构建的副本）

## 上游测试接入（核心工作）
- 套件：tests/*.bats 共 5 文件 224 个 @test 用例
  （apkbuild-lint 111 + secfixes-check 100 + bad-version-regex 6 +
  initd-lint 5 + aports-lint 2；注释掉的 XFAIL 不计）
- 上游入口 `redo check -> bats --tap`；OHOS 无 redo/bats/scdoc/lua5.3/unexpand，
  配方逐一低成本补齐：
  1. **bats-shim.sh**（随配方分发）：最小 BATS 兼容驱动。逐行预处理把
     `@test 'name' { ... }` 改写为函数定义（heredoc 内容与整行注释原样保留，
     上游注释掉的 XFAIL 用例自动忽略）；运行时提供 run/skip/status/output/
     ${lines[@]}/$BATS_TMPDIR 内置；每个用例独立子 shell 以 set -e 执行
     （断言失败即失败，与 bats-core 一致）；输出 TAP + BATS_SUMMARY_JSON。
     本机 Git Bash 冒烟（GNU 用户态，仅验证 harness 机制，非真机结论）：
     apkbuild-lint/bad-version-regex/aports-lint/initd-lint 四套件
     discovered=122 executed=122 passed=122 failed=0 skipped=0，
     2 个上游无条件 skip 用例被精确移出执行集（EXCLUDED 留痕）；
     test_package/test.sh 本地演练 4/4 通过且 HMBS 标记合法
  2. **lua5.3 解释器**：secfixes-check 的 100 个用例依赖 Lua 5.3；OHOS 无 Lua
     且制品仓无可用 lua 包。按"低成本补齐"原则从官方 lua-5.3.6 源码在真机现构建
     （clang -O2，32 个 .c，链接 -lm -ldl，秒级完成），产物放 build/tools/bin
     仅测试期 PATH 使用，不打包
  3. **tests-bin/unexpand**：上游 retab() 依赖 GNU unexpand `--first-only -t4`
     把空格缩进 fixture 折叠成 tab；toybox 未提供。提供最小实现（sh wrapper +
     python3 运行时解析，HMBS_PYTHON3 优先），只折叠行首空白
  4. **执行集审计**：2 个用例被上游作者无条件 skip('false positive')
     （'quoted composed pkgname is fine'、'backticks in comments should be
     ignored'），无可执行断言，移出执行集并写入 MANIFEST.yml audit；
     其余 222 个全部真实执行。TRAVIS 条件跳过的用例在预检环境照常执行
- 结果持久化：build() 把汇总 JSON 写入 build/upstream_test_result.json 与
  upstream_test_files.json 并打进包内 res/；test_package 每轮复发
  HMBS_UPSTREAM_TEST_RESULT / HMBS_UPSTREAM_TEST_FILES 标记（缓存命中跳过
  build() 时证据仍可见）。failed/skipped>0 或 executed≠discovered 时 build()
  显式失败

## test_package（消费者视角）
- test.sh 四个真实 lint 用例：TC1 存在可执行；TC2 干净 APKBUILD rc=0 零告警；
  TC3 默认 builddir rc=1 + [AL1]（复刻上游同名断言）；TC4 pkgver=21.0.0
  rc=1 + [AL61]（复刻上游 mesa bad version 断言）→ HMBS_TEST_PACKAGE_RESULT
- L1e 反向验证天然满足：PATH 指向包内 bin/，移除包即失败

## 编译环境
- 构建系统: custom（无编译）
- 编译日期: —（待真机预检）
- 编译器: clang（仅测试期 lua 解释器）
- 状态: pending（待真机预检，通过后由 HMBS 更新为 built）

## 真机风险清单（预检关注点）
- `sort -t: -V`：apkbuild-lint 主管道依赖 version-sort；若 toybox sort 不支持 -V
  会影响所有输出的排序与行序断言（备选方案：tests-bin 提供 sort 包装）
- toybox awk 对脚本中 2 处 awk 调用的兼容性
- mksh 作为 /bin/sh 执行大量后台函数 + wait 的行为
- 若以上任一在真机暴露问题，按最小适配原则补 tests-bin 工具或微调，不动上游逻辑

## 其他
- 无运行期依赖；无 C/C++ 产物；commands.json 已按 R38 在软件级目录声明

## R2 真机预检修复记录（mksh 方言 / 只读 /tmp / files JSON 缺失）
- 真机失败：`bats-shim.sh[115]: syntax error: unexpected operator/operand '=~'`
  → `ConanException: bats-shim produced no output`；另有 preflight 包装层
  `/tmp/sh*.tmp: Read-only file system` 噪声
- 根因：OHOS 没有 GNU bash，PATH 里名为 bash 的是 mksh/toybox 别名；
  bats-shim 原实现用了 bash 独有语法（`[[ =~ ]]`、mapfile、`<<<`、`$'\t'`、
  `for ((;;))`），mksh 解析到第 115 行 `=~` 即语法中止
- 修复 1（bats-shim.sh 全量重写为 mksh/bash/ksh93 公共方言）：
  - 预处理器的正则匹配改为 case/参数展开逐行解析（注释、heredoc 起止、
    `@test 'name' {` 头、块结束 `}`），语义与原 bash 版一致
  - run() 的 $lines 拆行改经 $WORK_DIR/run.out 临时文件 while-read 回读数组
    （printf %s 逐字节保真；不用 heredoc/here-string —— 它们会把捕获输出再过
    一遍展开器且在 mksh 下依赖临时文件）；TAP/汇总输出统一 printf
  - 临时目录链 BATS_TMPDIR → TMPDIR/TMP/TEMP → /tmp 兜底，mktemp -d 显式模板，
    失败时手工 mkdir 兜底；排除名单解析不再依赖 heredoc（NL 变量切分）
- 修复 2（conanfile._resolve_bash → _resolve_shell 能力探针）：
  探针要求 数组+追加+`[[ ]]`+函数内 local 全部通过；候选 CONFIG_SHELL → PATH
  bash → hnp/bash → /bin/sh(OHOS=mksh) → /system/bin/mksh，dash/纯 busybox ash
  类无数组 shell 被显式拒绝并报出已探测清单
- 修复 3（build() 补持久化 upstream_test_files.json）：test_package 显式校验该
  文件但 build() 此前从未写出（潜在下一轮失败点）；现随 per-suite 明细一并写入
  res/，空明细直接判失败
- 修复 4（test_package/test.sh 只读 /tmp）：`mktemp -d` 无模板默认写 /tmp，
  改为 TMPDIR/TMP/TEMP 链下显式模板 + 当前目录兜底；执行器由 conanfile.test()
  按 CONFIG_SHELL → /bin/sh 解析（脚本本体 POSIX sh，无需 bash）
- 本地实证（WSL：dash + GNU bash 5.1 + 真实 mksh R59 二进制）：
  - 探针：dash 拒绝（预期）、bash/mksh 通过
  - mksh R59 接受混合写法 `function f(){}` → AL9 用例 source 夹具不炸
    （dash 下可复现该用例失败，确证其为解释器差异而非逻辑错误）
  - 改写后 shim 在 mksh 下驱动真实上游 4 套件：discovered=122（124−2 审计
    排除）、executed=122、passed=122、failed=0、skipped=0，EXCLUDED 留痕正确
  - 负向对照：注入 2 个必失败用例 → 均 not ok、退出码非 0（harness 抓得住失败）
  - secfixes-check.bats（1411 行/100 用例）以桩 lua5.3 全量跑通预处理与计数：
    discovered=100/executed=100/failed=100（桩预期），无解析崩溃
- 不影响口径：执行集仍为 224 − 2 = 222；数字全部来自驱动真实 TAP 输出

## R3 真机预检修复记录（源码下载停滞 → SIGTERM / 退出码 5）
- 真机失败：conan create 在 `======== Installing packages ========` 后无任何
  后续输出（无 "Sources downloaded"、"Calling source()"、无 build 输出），
  stdout 出现 Conan 自带的 `Received SIGTERM!`，退出码 5。查 Conan 2 源码
  （conan/cli/exit_codes.py、conan/cli/cli.py）：5 = ERROR_SIGTERM，CLI 注册
  的 SIGTERM 处理器打印该消息并 sys.exit(5) —— 即预检 harness 超时杀掉了
  conan create，不是配方代码抛错
- 根因：Installing packages 阶段 conan 首个动作是按 conandata URL 下载主源
  码归档；gitlab.alpinelinux.org 对构建网络存在长时不可达窗口（本轮本地复
  现：官方 API 端点 TLS 握手被切断 SSLEOF/连接停滞；同日上午同一 URL 可正
  常下载且 sha256 一致，属间歇性黑洞而非永久故障）。Conan 默认超时
  (30,60)s + 内层 urllib3 retry=2 + 外层 tools.files.download retry=2，单
  个黑洞 URL 最坏可拖 ~270s+，耗尽 harness 预算被 SIGTERM。上一周期未做任
  何技术改动（provider 故障中止），本周期重新诊断后换路线：不依赖该主机可
  用性
- 措施 1（vendor 兜底副本）：conandata 记录的官方归档为 GitLab 动态生成，
  全网不存在逐字节相同的第三方镜像（gh-proxy/mirror.ghproxy/ghfast/
  ghproxy.net 实测对非 GitHub 目标一律 403；Wayback CDX 查询该 URL 零快照；
  GitHub Ikke/atools 为 git 仓库非归档镜像，tar 字节必不同），故把两次独立
  下载验证过 sha256（32e19ed3...，与 conandata 一致）的官方归档原样放入
  vendor/ 随 exports_sources 分发；source() 在网络全部失败时先对 vendor 副
  本强制 sha256 校验再解压。R39 合规：conandata URL 仍为官方原址，未引入
  不明来源下载地址
- 措施 2（快速失败）：get()/download() 显式 retry=0, retry_wait=0——单个
  坏源一次尝试即切换下一来源/vendor，避免默认 retry=2 在黑洞地址反复重试。
  多 URL 迭代语义已对照 Conan 源码确认（caching_file_downloader.
  _download_from_urls：非末位 URL 失败 → warn + Trying another mirror）
- 措施 3（lua_source 镜像化）：url 改有序列表，aliyun Debian 源码池
  lua5.3_5.3.6.orig.tar.gz 在前（实测下载 sha256 == fc5fd69b... 官方值，
  逐字节相同、下载稳定），www.lua.org 官方原址收尾作回退，共用原 sha256
  未改；同样有 vendor/lua-5.3.6.tar.gz 兜底
- 本地实证（Windows，Python 3.10）：
  - conanfile.py py_compile 通过；conandata.yml YAML 解析通过
  - 归档结构校验：两个 tar.gz 均单一顶层目录（strip_root 安全）
  - _fetch_archive 三分支模拟（网络异常注入）：A 主源码 vendor 兜底解压出
    apkbuild-lint(16580B)；B lua vendor 兜底解压出 src/lua.c；C 缺 vendor
    时显式报错——全部符合预期
- 测试口径不变：上游执行集仍为 224 − 2 = 222，全部真实执行
