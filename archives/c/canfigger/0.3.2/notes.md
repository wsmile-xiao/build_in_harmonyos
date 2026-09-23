# canfigger 0.3.2 适配笔记

## 软件概况

canfigger 是 Andy Alt(andy5995)维护的小型 C 配置文件解析库(MIT):把
`key = value, attr1, attr2` 形式的配置行解析成单链表节点,附带 UTF-8 BOM 跳过、
注释/节头忽略、XDG base-dir 辅助(`canfigger_config_dir` 等)和
`canfigger_path_join`。公开 API 全部是 C 接口,上游用 Meson 构建(≥0.48),
无第三方依赖。

## 编译环境

- 目标:OpenHarmony PC aarch64,`os=OHOS`, `arch=armv8`
- 编译器:HNP clang/LLVM 15.0.4
- 构建系统:Meson 1.11.0(ohpcd 预构建 Conan `tool_requires`)+ Ninja 1.13.1
- Conan:2.29.1(OHOS 适配版)
- 编译日期:2026-09-05
- 状态:built(设备端 `conan create` 与 `test_package` 已通过)

## 依赖版本

- `meson/1.11.0`:`tool_requires`,来自 ohpcd 的预构建构建工具包(W0 已验证:
  `conan download --only-recipe` 成功,`conan install --build=never` 直接命中
  缓存包)。`meson/1.11.0.1` 虽在远端列有 recipe,但 `conan download` 报
  `error:system acceleration policy not enabled`,与 libavtp 适配时
  "有 recipe 无预构建包" 的结论一致,不选用。
- 上游测试无外部框架依赖(assert 自包含),不需要 cmocka 之类 test_requires。

## 配方实现

- `MesonToolchain` 生成 Conan 编译器/构建选项;`default_library` 随
  `shared` 选项;`build_tests`/`build_examples` 随 `tests` 选项(默认开启,
  保证 14 项测试全部编译)。
- `build()`:Meson configure → `meson compile -C <build> -j1`(设备默认串行)→
  `meson test --no-rebuild --print-errorlogs --timeout-multiplier=16`,
  从 meson 汇总行解析 `Ok/Fail/Skipped/Timeout/Not run` 并输出
  `HMBS_UPSTREAM_TEST_RESULT` 硬门禁标记,Fail/Skip/Timeout 非 0 即抛错。
- `package()`:meson install(Conan 助手自动 `--destdir=package_folder`),
  附带 LICENSE;shared 选项下把 `libcanfigger.so.0` / `libcanfigger.so`
  实体化为真实文件(保留链接器签名)。
- `package_info()`:`cpp_info.libs=["canfigger"]`,
  `includedirs=["include/canfigger"]`,与上游 pkg-config 的
  `-I${includedir}/canfigger` 一致,消费者 `#include <canfigger.h>`。
- 无补丁:上游源码与测试在 OHOS 零修改全部通过,`patches_applied: []`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 重签后的 `libcanfigger.so.0` 被本机加载器加载即 SIGSEGV | hnp clang 驱动在链接期已自动内嵌 ad-hoc `.codesign` 签名段(本地 meson 产物与第 1 轮 Conan 包 readelf 均见该段);`binary-sign-tool selfSign` 重签产物则加载崩溃。对照实验:剥离重签产物的 `.codesign` 段后同一二进制立即恢复可加载(40/40 断言通过),锁定崩溃来自二次签名 | 配方不做 `binary-sign-tool` 重签,保留链接器签名;libavtp 的签名流程在其设备环境成立,但本机实测对 hnp clang 产物重签有害 |
| 2 | 首轮 test_package 在 CMake Release 构建下 SIGSEGV | 我的初版消费者测试用 `assert()` 当检查宏,把 `fputs`/`fclose` 副作用写进断言条件;CMake Release 追加 `-DNDEBUG` 把断言整体编译掉 → 配置文件是空文件 → `canfigger_parse_file` 返回 NULL → 解引用崩溃。上游 `tests/test.h` 开头 `#undef NDEBUG` 正是防这个 | 改为自包含 `CHECK` 宏(条件恒求值,失败 `abort()`),副作用调用移出条件;`-O3 -DNDEBUG` 与无 flag 两种模式均 40/40 通过 |
| 3 | `lang-preflight` 把任务判成 `mixed(env_unsupported)` | release tarball 内含上游提交的 doxygen 预生成 `docs/`(36 个 .js/.html 等生成物),被语言统计按扩展名计入 nodejs 主体,占比 71% 触发 mixed;排除生成文档后真实主体是 15 个 .c(100%) | 以排除 `docs/` 的源视图重跑 `lang-preflight --lang c`:task=c/detected=c 通过;两轮证据均留档任务目录 |

## 验证结果

设备端执行(`$HOME/tmp/canfigger-0.3.2` 留有全部日志):

1. 原生探索(`$HOME/tmp/canfigger-0.3.2/native-build`):meson 1.12.0 + ninja 1.13.1,
   `meson setup && ninja -j1` 一次通过;`meson test` **14/14 Ok / 0 Fail**。
2. `conan create`(清包缓存后干净构建,profile ohos-aarch64 双侧):
   构建成功;包内 `meson test` **14/14**(12 单元测试 + 2 example 条目),
   `HMBS_UPSTREAM_TEST_RESULT` status=passed;test_package 编译运行,
   `CANFIGGER_CONSUMER_TEST PASS assertions=40`。
3. 包产物核验:`include/canfigger/{canfigger.h,canfigger_version.h}`、
   `lib/libcanfigger.so{,.0,.0.3.2}`(实体文件,链接器 `.codesign` 保留)、
   `lib/pkgconfig/canfigger.pc`、`licenses/LICENSE`。
4. 动态加载:消费者以包内 .so 链接运行通过(NDEBUG/默认两种编译模式)。

## 测试计数口径

- 上游统计单位:meson test 条目(`tests/meson.build` foreach 注册 12 个 +
  顶层 `meson.build` 在 `build_tests`+`build_examples` 时注册 2 个 example 条目)。
- 取数命令:`meson test -C <build-folder> --print-errorlogs`,读汇总
  `Ok:/Fail:`(meson-logs/testlog.txt)。
- 上游 14 = 14(全部执行,无 skip、无默认未编译分组);适配后新增
  test_package 消费者 1 个(40 断言),单列不计入上游用例数。

## 归档信息

- 上游源码:`https://github.com/andy5995/canfigger/releases/download/v0.3.2/canfigger-0.3.2.tar.xz`
  (官方 release 发布物;SHA-256 与官方 git tag 归档逐文件 diff 完全一致)
- Meson 工具:ohpcd `meson/1.11.0`(Conan `tool_requires`,预构建包)
- 测试清单:`test_package/MANIFEST.yml`

## 发现与知识

- ✅ hnp clang 链接期自动内嵌 ad-hoc `.codesign` 签名段;`binary-sign-tool selfSign` 重签产物在本机 musl 加载器 SIGSEGV,剥离该段后恢复可加载——本地/Conan 构建链的共享库不应二次签名(问题 #1,已写入 manifest knowledge_gained 并形成知识草稿)。
- ✅ Conan 消费者测试/上游 assert 类测试在 Release(`-DNDEBUG`)构建下,断言条件会被整体编译掉,副作用绝不能写进断言条件;上游 test.h 用 `#undef NDEBUG`、本包消费者测试改用自包含 CHECK 宏(问题 #2)。
- ✅ `lang-preflight` 的扩展名统计会把 release tarball 内预生成 doxygen `docs/` 计入 nodejs 主体触发 mixed 误判;排除生成文档目录后按真实 .c 主体重跑即得正确判定,两轮证据留档(问题 #3)。
- ✅ Meson 库项目配方复用 ohpcd 预构建 `meson/1.11.0` tool_requires 与 conan.tools.meson 助手即可完成完整构建+测试+安装(与 libavtp/0.2.0 一致)。

## 收尾门禁记录

### 轮 1(SHA ad4fcf79):conan-verify

- G1/G0/G2/G3 PASS(G2 前已 `conan remove "canfigger/*" -c`,干净构建);
  L2/L4/L5 工具因 cache 路径解析跳过,已手工补测:L2=消费者 40/40 断言
  (reports/conan-create.log),L4=GNU_STACK NX + GNU_RELRO + BIND_NOW
  (Full RELRO),L5=三个 .so 别名 sha256 一致 57cacb3c… 且 .codesign 保留。

### 轮 2(SHA 949273ea):finish(状态 built)

- Step4 conan-verify PASS;Step5 W3 本地 CI 模拟通过
  (reports/w3-local-ci.log);Step7 W5 doc↔kv 完整、知识完整性通过
  (notes 4/4,manifest 5 条 0 未引用);Step9 W2 框架变更告警为已知
  基线漂移误报,以 upstream/main 三点 diff(pr.diff,仅本软件目录+知识草稿)为准。
- 已知工具限制如实记录:Step3 clean-verify 报"找不到原始 tarball"
  (工具按固定路径定位 orig=None);等价清洁构建证据 = G2 conan create
  每轮 fresh 下载源码且缓存已清 + W3 通过。Step10 submit 遗留预检
  (test-report.md/packaging//.staging-verified/release、debug tar.gz)属
  ARCHIVE-SPEC v3.0 已废弃项,不伪造,按 submit-only 预检记录。
- finish 副作用逐项处置:SUMMARY.md 重建截断已还原(2622 行);
  conandata.yml 镜像列表改写先按 astroterm 先例保留,后经 W4 审计
  依 R39/PF7 实跑闸门判定为违规,轮 4 已还原为官方单 URL(见轮 4);
  notes footer 保留;.build-cache/ 与 conandata.yml.ghfast-bak 垃圾已删除。

### 轮 3(SHA 9b07b9d6):conan-verify + finish 复跑

- 定稿 SHA 9b07b9d6 复跑:conan-verify PASS、finish W3 本地 CI 模拟通过;
  finish 副作用同轮 2 处置(SUMMARY 还原、footer 还原至已提交版本,
  HEAD 保持 9b07b9d6 不变)。

### 轮 4(W4 审计与修复)

- W4 独立审计(独立上下文,实跑 preflight.py PF1/PF2/PF3/PF5/PF7/PF8/PF9):
  verdict=fail,P1×2 + P3×2,欺骗检测/配方质量/W2 原子性全过。
- P1-1(R39/PF7):conandata.yml 手写 gh-proxy.com 镜像前缀违规 →
  还原为官方单 URL(CI 预下载器自动附加镜像回退),注释同步更正。
- P1-2(PF9):软件级 README.md 触发 PF9"缺版本目录层"fail-closed 硬发现 →
  删除软件级 README.md(与最新合并先例 libavtp/0.2.0 一致,内容在
  notes.md 与 PR 正文覆盖;ARCHIVE-SPEC 的 README"必须"要求与现行
  PF9 闸门存在冲突,按闸门优先处置并在此留痕)。
- P3-1/2:知识草稿改名 DRAFT-canfigger-resign-crash(避开 main 上
  E429 双草稿同 id 冲突),id 字段同步,补 authors/source_commit。
- 教训留痕:首次修复提交因 `git add` 路径参数报错整体中止而内容不完整
  (b7691fea 只含 README 删除与改名),已重做完整内容修复提交;轮 5 对
  新 SHA 复跑 conan-verify + finish,并重新生成审计输入进行复审。

---

**编译结束**: 2026-09-05 14:13
**最终状态**: built
