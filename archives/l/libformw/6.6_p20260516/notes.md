# libformw 6.6_p20260516 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 任务定位：libformw 是什么

libformw 不是独立上游项目，是 ncurses 源码树 **form/ 子库**的打包名（宽字符版本）：

- 公开头：`form.h`（内部包含 `<eti.h>` 与 `<curses.h>`）
- 产物：`libformw.a`（静态）+ `lib/pkgconfig/formw.pc`
- 源码与已发布 `ncurses/6.6` 为**同一份官方 tarball**（`ncurses-6.6.tar.gz`，
  sha256 `355b4cbb…ff11`，conandata.yml 与 ncurses/6.6、libncursesw/6.6_p20260516 逐字一致）

平台任务版本号 `6.6_p20260516` 是任务批次命名；实际上游源为 ncurses 6.6 官方发布
tarball。此映射与家族既有交付（ncurses/6.6 已发布、libncursesw/6.6_p20260516
PR #10433）保持一致。

## 依赖拓扑决策（W0/W0b 家族核验）

ncurses 家族在本仓库/制品仓/平台任务上的现状（2026-09-19 实测）：

| 对象 | 状态 |
|------|------|
| `ncurses/6.6`（制品仓） | **已发布**（revision 3dcfd3b6d759300e8997800cefe8c61f，2026-08-07），静态全家桶（formw/menuw/panelw/ncursesw），conandata 与本包一致 |
| `libncursesw/6.6_p20260516`（平台任务 13330，Windrel） | PR #10433 **open 未合并**，制品仓**未发布**（conan download 实测失败） |
| `libformw/6.6_p20260516`（本任务 8192） | 制品仓不存在（W0 实测），本任务新建 |
| `libmenuw/6.6_p20260516`（平台任务 8269）、`libpanelw/6.6_p20260516`（8327） | 本人名下待做，与本包同构 |

决策：**本包 `require ncurses/6.6`（headers=True, libs=True, visible=True）**，
不 require `libncursesw/6.6_p20260516`：

1. R36/PF4 硬闸：依赖必须已发布到制品仓。libncursesw/6.6_p20260516 未发布，
   依赖它会被 finish R36 检查与建 PR PF4 闸直接拦截，且不能捎带适配他人任务。
2. ncurses/6.6 是 CI 验证过的已发布包，其 libncursesw.a/curses.h 与本包 form
   对象**同源**（同一 tarball、同一 4 补丁、同构配置），ABI 一致性由构造保证、
   由 test_package 静态链接实跑证实。
3. 下游视角：`libformw/6.6_p20260516` + 父包提供 `-lformw -lncursesw` 完整链接闭包。
   待 libncursesw/6.6_p20260516 发布后，家族可按 R37 版本后缀演进重定向，
   本包现有交付不受影响。

W0 回执：`w0.json` status=pass（`--deps "ncurses/6.6"`，ncurses/6.6: available；
目标配方不存在属预期）。

## 关键适配事实

1. **form/*.c 依赖内部头 `config.h` 与 ncursesw 内部符号**：无法绕过 configure
   只挑 form/ 目录编译——必须完整 configure 后随树构建，再在 package 阶段裁剪。
   与 libgmpxx/6.3.0（cxx 子库同源打包）同一模式。
2. **构建机制沿用 ncurses/6.6 已发布配方契约**（同源同配置，非遗框架修改）：
   OHOS 私有 build root `/data/storage/el2/base/.conan-build-libformw-*`、
   hnp bash 作 CONFIG_SHELL、`make -j1`（HMDFS 禁止 make 4.4 jobserver mkfifo）、
   86 项上游测试程序清单核验、`make check`、staging install。
3. **配置与 ncurses/6.6 完全同构**：`--disable-shared --enable-static
   --without-shared --with-normal --without-debug --with-trace --without-ada
   --without-manpages --enable-widec --enable-overwrite --enable-pc-files`
   （OHOS 追加 `--prefix=/ --with-pkg-config-libdir=/lib/pkgconfig`）。
   config.h 同源 ⇒ form 对象引用的 ncursesw 符号与父包 ABI 一致。
4. **补丁复用**：4 个可移植性补丁与 ncurses/6.6 逐字节相同（sha256 在
   conandata.yml 中核对一致：toybox expr、lib_mvcur 静态链接、头文件安装 shell、
   config.guess 识别 OHOS）。补丁无 `__OHOS__` 平台宏（PF5/R8 口径）。
5. **静态专用**：`shared=True` 在 configure() 即抛 ConanInvalidConfiguration
   （父包 ncurses/6.6 仅静态 libncursesw.a，无可用 libformw.so 链接路径）。
   与家族"避免遮蔽系统 libncursesw.so.6"契约一致（E028）。
6. **package 裁剪**：只保留 `include/form.h`、`include/eti.h`、
   `lib/libformw.a`、`lib/pkgconfig/formw.pc`；删除 libncursesw.a/menuw/panelw、
   curses.h/term.h 等父包产物、terminfo、bin 脚本。出现父包/兄弟产物即
   _validate_package 报错（防双份符号）。formw.pc 做 `${pcfiledir}` 重定位
   （与 ncurses/6.6 的 pkgconfig 重定位同法）。
7. **可见依赖**：`requires(..., visible=True)`——form.h 公开包含 `<curses.h>`，
   Conan 2 CMakeDeps 需 visible 传递依赖才生成 include 目录（libgmpxx 同法）。
   **且 package_info 必须声明 `cpp_info.requires = ["ncurses::ncurses"]`**：
   CMakeDeps 只凭 requires 图不会把父包 include/lib 挂进 formw::formw target
   （首轮 W3 test_package 实测 `curses.h not found`，libgmpxx 配方同款声明可证）；
   消费者 CMake 同时 find+link 两个 target（顺序 formw 在前满足静态链接序）。

## 上游测试（R51 三步法）

1. **清点**：上游 ncurses 测试套件入口 `test/programs` 清单共 **86 项测试程序**
   （配方 `_verify_upstream_programs` 强制清单一致性，缺一即失败）。
2. **实跑口径（关键事实，2026-09-19 W3 日志实证）**：上游 `make check` 对
   `test/` 程序**仅做构建核验并输出 "The test-programs are interactive"**——
   这 86 项是交互式演示程序，上游设计上就不在 make check 中 headless 执行；
   check 实跑内容为 include/ncurses/progs/panel/menu/form 各子目录自检 +
   全部 86 程序的编译与存在性。此口径与已合并 ncurses/6.6（PR #4453，86/86
   同义）一致。本平台 headless 终端初始化（initscr 全屏路径）实测段错误，
   交互程序同样不可 headless 运行，故按上游口径不执行。
3. **回填**：N=86（清单程序数，构建核验 86/86 + make check 全过）；
   test_package 另有 13 断言的 form API 全链路实跑（1/1 通过，实跑方式见下）。

## test_package 屏幕上下文实测记录（2026-09-19）

宽字符 form 库的缓冲/表单对象绑定 SCREEN，无屏幕时行为实测：

- `set_field_buffer`/`field_buffer` 经由内部 pad（newpad 无 SCREEN 返回 NULL），
  无屏幕时 set 返回 E_OK 但读回空串（静默失败，易误判库损坏）。
- `new_form` 要求 `IsValidScreen`（frm_def.c），无屏幕返回 NULL；
  其 `Connect_Fields` 遍历调用方传入的字段数组——**必须传 NULL 结尾数组**，
  传标量地址在无屏幕时不暴露、有屏幕时段错误（ncurses API 契约）。
- 本平台 initscr 全屏初始化路径段错误（TERM=dumb 与 xterm-256color 均复现，
  dbg9 逐步定位）；newterm + dumb 正常。test_package 采用
  `newterm("dumb") + 强制 TERM=dumb`（TERMINFO 由父包 conanrun 环境提供，
  实测无 TERMINFO 时干净报错），设备实测 13/13 断言通过（rc=0）。

## 与既有条目的实测差异（路径 B 备忘）

- E028（ncurses 共享库系统冲突）：本包继承静态专用契约，无新增事实。
- E033（宽字符 cchar_t）：本包不直接暴露 curses API，未触发。
- libgmpxx 先例（同源子库打包模式）可复用为知识条目参考，form 侧新增事实：
  form.h 链式包含 eti.h/curses.h 的可见依赖需求。

## 源码 URL 修正（2026-09-19 W3 首轮失败实测）

- 首轮 W3 `conan create` source() 失败：conandata 原引
  `invisible-mirror.net/archives/ncurses/ncurses-6.6.tar.gz`，实测该镜像当前
  下发 **7299 字节错误页**（curl 实测 sha256 `489d126e…`，conan 下载实测
  `aaaba365…`，内容不稳定），与家族基线哈希 `355b4cbb…` 不符。
- 官方源站 `invisible-island.net/archives/ncurses/ncurses-6.6.tar.gz` 实测
  3791150 字节、sha256 **与家族基线 `355b4cbb…` 完全一致**（ncurses/6.6 发布时
  与本包 conandata 同值）。故 URL 改为官方源站，sha256 保持不变。
- 该镜像故障影响整个 ncurses 家族基线（已发布 ncurses/6.6 走二进制缓存不受影响，
  但任何重新 source() 的构建都会失败）；已记入本地 feedback 待办。

## L5 基线重立说明（2026-09-19）

同源码第二轮验证时 L5 产物基线对比报 `lib/libformw.a` 差异：每轮验证使用
随机命名的私有 CONAN_HOME，ELF 静态归档内嵌构建路径/build-id 逐轮变化。
按验证器指引删除 `reports/baseline.json` 重立基线（语义等同首轮），源码、
配方、补丁与配置均无变更。
