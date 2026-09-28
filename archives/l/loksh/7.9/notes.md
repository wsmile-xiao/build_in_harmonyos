# loksh 7.9 适配笔记

任务分支：`feat/loksh-7.9`（路径 A：仅新增 `archives/l/loksh/`，零补丁文件）
平台任务：contrib-8536（2026-09-26 认领，claimer Sy444）

## W0 依赖检查

| 依赖 | 类型 | 制品仓状态 |
|------|------|-----------|
| ncurses/6.6 | 可选但按必需发布（上游 dependency('ncurses') → 'ncursesw' 回退 → 都没有则 -DSMALL 砍编辑功能） | archives/n/ncurses/6.6（同 6.4/6.5 有多版本先例） |
| lolibc（dimkr/lolibc） | 随源码捆绑（meson subprojects，官方 release tarball 已打包） | 不需制品包（同 tarsnap 捆绑 libcperciva 的口径） |

- **MateBook 第一步**：配置 ohpcd remote 后 `conan download` 复核
  ncurses/6.6 的二进制包真实存在（R35，禁止 conan list 判断）。
- meson 本体：真机/CI PATH 无 meson，远端无可解析工具包 → vendored meson
  1.11.2（conandata `meson_source`），zchunk/1.5.2、astroterm/1.0.9、
  libdvdnav/7.0.0 已在真机验证同一方案。

## W0b 历史经验核验

- 仓库 archives/ 无 loksh 历史归档（首次适配）。注意 `archives/o/oksh`
  是另一个 OpenBSD ksh 移植（不同上游），与本任务无关。
- 复用的历史知识（均已在 main 合入验证）：
  - **vendored meson**（zchunk 1.5.2）：meson 官方源码进包 → `python3 -c`
    进程内 `sys.path.insert + mesonmain.main()`；PkgConfigDeps 生成依赖
    .pc 供 `dependency()` 解析；native file 注入 llvm-ar/llvm-ranlib 绝对
    路径；`meson install --destdir` 用 CLI 标志（环境变量 DESTDIR 到不了
    子进程）。
  - **E074**：并行构建触发 HMDFS jobserver fifo EPERM → `ninja -j1`。
  - **R33**：编译器/ar 从 `tools.build:compiler_executables` conf 获取。
  - meson 交叉：MesonToolchain 生成 conan_meson_native.ini（R32/R33 口径）。

## 构建系统分析

- 上游 7.9 起从 autotools 迁到 **Meson**（meson.build 仅 35 行）：
  - 硬性 `subproject('lolibc')`（第 3 行无条件加载），ksh 静态链
    liblolibc + 其 include 路径 —— GitHub **tag** tarball 不含子模块，
    meson setup 直接失败；**官方 release 资产 loksh-7.9.tar.xz 已打包
    子模块**（实测 33 个 lolibc 文件），故 conandata 钉 release 资产
    URL（R39 合规：上游官方 release 页）。
  - 可选依赖 ncurses → ncursesw → 都没有时 `c_args += ['-DSMALL']`
    （无命令行编辑）。ncurses/6.6 包的 pkg_config_name 是 `ncursesw`，
    PkgConfigDeps 生成 ncursesw.pc，命中上游回退分支；配方在 build()
    解析 build.ninja，发现 -DSMALL 即抛错（防静默降级）。
  - 单一产物：`ksh` 可执行 + man 页（ksh.1/sh.1）+ 文档 → 工具类，
    软件级 commands.json（R38）。
- 无 autotools 面：无 config.guess 三元组问题、无 E114 umask 077 问题。

## 测试分析

- **上游无测试套件**：meson.build 无 `test()`，release tarball 无测试
  目录；上游 GitHub CI（ci.sh/.github/workflows）是容器构建冒烟，不是
  随源码分发的测试框架，不可离线复用 → 按赛事规则说明原因并自补测试。
- 自补消费者测试 `test_package/test_loksh.sh`：12 项断言，全部离线，
  真实执行被适配工具（R34 工具类口径，同 tarsnap 消费者测试模式）：
  1. `ksh -c 'echo ok'` 基本执行
  2. 变量与算术展开 `$((x+1))`
  3. `for` 循环 + `printf` 输出
  4. 管道 `echo | tr`
  5. 退出码传递 `exit 7` → `$?`
  6. 脚本文件执行（临时脚本 `ksh script`）
  7. 位置参数 `$#`
  8. `[ ]` test 内建
  9. 子 shell `( )`
  10. `while read` 循环读 here-doc
  11. 函数定义与调用
  12. `${KSH_VERSION}` 非空
- 报告口径：上游测试 0（无套件，原因已述）；消费者 12 项全部通过为
  100%。

## Windows 阶段已做

- 官方 release 资产下载 + sha256 核验（9cd50a5d…）；tag tarball 与
  release 资产的 lolibc 差异实测比对。
- meson.build / .gitmodules / config.h 静态分析（见上）。
- 配方按 zchunk 1.5.2 vendored meson 模式编写；-DSMALL 守门。

## 留给 MateBook 的验证项

1. `conan download ncurses/6.6` 复核二进制（R35）。
2. `conan create` + `conan test`：vendored meson setup → ninja -j1 →
   install；确认 -DSMALL 守门不触发（ncursesw.pc 解析成功）。
3. 消费者 12 项断言全绿；记录 upstream 0/消费者 12/12 口径。
4. `ohc-run.py finish loksh 7.9 built` → W4 审计（P0/P1 清零）。
5. 注意 ksh 作为交互 shell 的真机表现不在门禁范围（非交互脚本路径
   已覆盖）。
---

**编译结束**: 2026-09-28 10:58
**最终状态**: built
