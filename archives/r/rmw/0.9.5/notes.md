# rmw 0.9.5 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 概述

rmw（ReMove to Waste）是命令行回收站工具：将文件移入可配置的 waste 目录
（支持 FreeDesktop.org Trash 规范），可恢复、可按过期天数清理。纯 C，meson
构建，产出单个可执行文件（内部静态库 librmw / libbsdutilsrm 不对外）。
本包 `package_type = "application"`。

## 适配遇到的问题与解决方案

### 1. pkg-config 依赖解析在 OHOS 上全面失效

上游 meson.build 用 `dependency('curses')`、`dependency('menuw')`、
`dependency('canfigger', fallback: [...])` 解析依赖：

- OHOS ncurses conan 包只导出 `ncursesw.pc` 等文件且 `prefix=/`
  （在真机构建时解析出 `-I/include` 无效路径），也没有 `curses.pc`；
- canfigger conan 包无 .pc，meson 的 wrap-git fallback 需要访问 GitHub
  （不可用）；
- 实测 conan 2.29 的 `PkgConfigDeps` 生成器在此宿主上未产出 .pc 文件，
  meson `dependency()` 报 `canfigger found: NO (tried pkg-config and cmake)`。

**解决**：补丁把三处 `dependency()` 全部改写为
`cc.find_library(name, has_headers: [...])`，配方在 `generate()` 里把每个
依赖包的 `includedirs`/`libdirs`（**相对路径须拼 package_folder 成绝对路径**）
以 `-I`/`-L` 注入 `tc.c_args`/`tc.c_link_args`。

### 2. meson 头文件探测失败（ncursesw/ 子目录不存在）

ncurses 6.6 conan 包的 `include/` 是扁平布局：`curses.h`、`menu.h` 直接在
根目录，没有 `ncursesw/` 子目录，因此 `has_headers: ['ncursesw/curses.h']`
探测失败。改用扁平头 `['curses.h']` / `['menu.h']` 后，config.h 的
`HAVE_CURSES_H`/`HAVE_MENU_H` 被定义，`restore.h` 的 `#if defined` 链走
扁平分支，编译通过。

### 3. musl 无 fts(3)（硬阻塞）

`src/bsdutils/rm.c`（BSD rm_tree 递归删除实现）硬依赖 `fts_open` /
`fts_read` / `fts_set`，musl/OHOS 既无 `fts.h` 也无 `libfts`
（真机 `clang fts_probe.c` 实测 fatal error）。上游 fallback 是
`cc.find_library('fts')`（必失败）。

**解决**：vendored [musl-fts 1.2.7](https://github.com/void-linux/musl-fts)
（NetBSD 实现，BSD-3-Clause；fts.c + fts.h 共 1410 行文本文件）随配方分发，
`build()` 时拷入 `src/bsdutils/`，补丁 0003 让 bsdutilsrm 静态库直接编入
`fts.c` 并从本目录取 `fts.h`。musl-fts 的 autotools `config.h` 只需最小集：

```c
#define HAVE_DIRFD 1
```

（musl 有 `dirfd()`；不定义 `HAVE_STRUCT_DIRENT_D_NAMLEN`——musl dirent
无该字段；`HAVE_DECL_MAX` 未定义时代码有自定义 MAX 的兜底分支。）

### 4. NLS/gettext（零补丁）

musl 无 libintl。上游 `src/gettext.h` 在 `ENABLE_NLS` 未定义时自带内联
stub（gettext/ngettext 直通原文），`main.c` 的 `bindtextdomain` 也有
`#ifdef ENABLE_NLS` 守卫，因此 meson 传 `-Dnls=false` 即可，无需改源码。

### 5. btrfs clone（零补丁）

上游仅当 `host_machine.system() == 'linux'` 才探测 statfs/btrfs.h；meson 在
OHOS 上返回 `'harmonyos'`，直接跳过。配方显式传
`-Dwant_btrfs_clone=false` 求确定。

### 6. conan 本地源码下载超时

GitHub release 直连超时（connect timeout）。使用 conan 2.29 backup sources
机制：`global.conf` 设
`core.sources:download_cache=<绝对路径>`（注意：不是
`core.download:download_cache`，后者是包制品缓存，二者并存），tarball 以
内容 sha256 命名放入 `<cache>/s/` 目录。CI 侧由预下载器附加镜像回退，
conandata.yml 仍只写官方 URL（R39）。

### 7. 意外收获：ncurses 静态链接

ncurses conan 包仅含静态库（libncursesw.a / libmenuw.a），rmw 可执行文件
静态链入 curses/menu，运行期不依赖 LD_LIBRARY_PATH，规避了 HMDFS 上
versioned symlink 的加载不确定性（augeas #29 同类问题）。

## 验证结果

- `conan create` rc=0（conan 2.29.1，profile ci/conan/profiles/ohos-aarch64）
- test_package 端到端消费者用例 **11/11 断言全过**：
  `--version` 报 0.9.5、`--help`、`-c` 配置解析、`-o` 孤儿检查、移入
  waste（FreeDesktop `files/` 布局）、`info/*.trashinfo` 生成、
  trashinfo `Path=` 记录原路径、`-z` 恢复、内容一致、info 消费
- 上游 6 个 meson shell 测试未执行（需 root / btrfs 镜像），以
  test_package 端到端用例覆盖核心功能路径

## 可复现命令

```sh
source /data/storage/el2/base/cache/rmw-env.sh   # CONAN_HOME=conan-home-rmw 等
conan create archives/r/rmw/0.9.5 \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 --build=missing
```
---

**编译结束**: 2026-09-29 23:44
**最终状态**: built

## 对话记录

### 对话 #1 [2026-09-29]

- 问题: `conan create` 反复失败，meson 头探测（canfigger.h / curses.h）全 NO，`c_args` 为空
- 操作: 加 DBG 输出逐依赖排查，发现 conanfile.py 根本没有 `requirements()`——依赖图静默为空且无任何报错；随后又发现依赖的 `cpp_info.includedirs/libdirs` 是相对路径，直接注入 `-Iinclude` 无效
- 结果: 补上 `self.requires("canfigger/0.3.2")` 与 `self.requires("ncurses/6.6")`，注入时用 `os.path.join(dep.package_folder, x)` 拼绝对路径，探测全部命中

### 对话 #2 [2026-09-29]

- 问题: `PkgConfigDeps` 在 generate() 阶段静默不产出任何 .pc 文件，meson `dependency()` 查不到 canfigger/ncursesw
- 操作: 读 conan 2.29 `pkgconfigdeps.py` 源码未定位到根因，果断换确定性方案——补丁把 `dependency()` 全部改为 `cc.find_library(name, has_headers:)`，绕开 pkg-config
- 结果: 全部依赖解析成功；经验：OHOS 上 meson 依赖解析优先走 `cc.find_library`，不依赖 pkg-config

### 对话 #3 [2026-09-29]

- 问题: conan 下载源码 tarball 反复超时，`core.download:download_cache` 配置不生效
- 操作: 读 `caching_file_downloader.py` 源码，确认 conan 2.29 的 conf 名是 `core.sources:download_cache`，tarball 按 sha256 命名放 `<cache>/s/`
- 结果: 源码缓存命中，下载零等待；环境脚本 rmw-env.sh 已固化该配置可复用

### 对话 #4 [2026-09-29]

- 问题: test_package 首跑 5 项断言失败，文件未落在预期位置
- 操作: 手动带 `LD_LIBRARY_PATH` 重现 rmw 移动流程，发现 0.9.5 用 FreeDesktop Trash 布局（`<WASTE>/files/` + `<WASTE>/info/`），与旧版平铺布局不同
- 结果: 重写 test_rmw.sh 断言为 FreeDesktop 布局并补 `-z` 恢复链路，11/11 全过

### 对话 #5 [2026-09-29]

- 问题: finish 的 W3 在 L0 失败 `commands_json_r38`
- 操作: 按 hint 参考 `archives/s/strace/commands.json` 与 rt-tests 先例，确认 tool 类源码构建用 `"binary": false`
- 结果: 创建 `archives/r/rmw/commands.json`，W3 复跑通过（Pass rate 100.0%）

### 对话 #6 [2026-09-29]

- 问题: submit 就绪预检 3 项未就绪（test-report.md / packaging/ / .staging-verified）
- 操作: 按 sensorfw/libbfio 先例补 `reports/test-report.md` 与 `packaging/README.md`（v3.0 conan 配方豁免 tar.gz 的占位说明）；`.staging-verified` 创建后 junk_check JC1/JC5 报其为不可入库的运行时标记，改为本地存在、git 不跟踪
- 结果: 预检 4 项全 ✅，junk_check 0 错误，W2 确认 20 文件纯配方变更

### 对话 #7 [2026-10-02]

- 问题: PR #13893 rule4 FAIL——上游实测 N=7 > 声明 N=6 属少报, 且上游用例一个都没测(0/7), 任何理由(平台限制/缺依赖/无环境)均不通过
- 操作: 诊断上游测试构成(3 个 C 单元测试 + 4 个 shell 脚本, meson test 注册 8 项含 bsdutils rm), 逐个真实执行并修平台坑: test_utils SIGABRT(utils.c symlink EACCES)→SELinux 域限制, 补 0004 探测 helper 优雅跳过; meson test 挂起→逐个带 timeout 执行; shell 测试 rc=127→缺 LD_LIBRARY_PATH; id -u 报 bad uid(多用户 uid 20020170)→stat -c %u(0005/0006); /tmp 只读 erofs→/storage/Users 当媒体根(0006, media_root 用例通过); HMDFS 新解压脚本 execve EACCES→0008 经 sh 解释器包装; test_is_dir_f:722 还有 symlink 断言→重构 test_symlink_ok helper(修 double-free)
- 结果: meson test 8/8 全过(Ok: 8, Fail: 0, Skip: 0); 新增补丁 0004-0008; manifest/test-report/pr-body 同步为真实执行口径; 经验: OHOS SELinux 拒未签名进程 symlink(2)/lstat、toybox id 不认多用户 uid、/tmp 只读、HMDFS execve 延迟——上游测试必须真实跑, 平台坑用探测跳过 + 披露, 不能整测跳过

### 对话 #8 [2026-10-02]

- 问题: CI 构建 #66915 在 conan-build-test 失败, meson test Ok: 7 / Fail: 1——test_basic.sh 的「列出未挂载设备 waste 文件夹」断言不匹配: 期望 /mnt/fs/Trash-20020170(补丁 0005 用 stat -c %u .), 实际输出 Trash-20020101
- 操作: 读上游 rmw.testrc 发现 WASTE = /mnt/fs/Trash-$UID, rmw 运行时把 $UID 展开为进程真实 uid(getuid); stat -c %u . 返回的是目录 owner, 本地 conan build 目录由进程自建(owner==uid)碰巧一致所以 8/8, CI worker 上 build 目录 owner(20020170) != 进程 uid(20020101) 就错位
- 结果: 补丁 0005 改为 $(grep '^Uid:' /proc/self/status | cut -f2)——内核提供的进程真实 uid, 不经 toybox id 校验(bad uid 问题一并规避), grep/cut 均为 toybox 核心命令无可用性风险; 在旧构建树原地 sed + meson test 验证 test_basic.sh OK; 经验: 期望值依赖进程身份时取 /proc/self/status 的 Uid 字段, stat 取 owner 只在 config/断言两侧同源自洽时可用
