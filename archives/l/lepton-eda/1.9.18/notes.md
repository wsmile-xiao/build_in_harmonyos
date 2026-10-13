# lepton-eda 1.9.18 适配笔记

## 编译环境
- 构建系统: autotools（Conan 驱动，conanfile.py 模式 B 收尾）
- 编译日期: 2026-10-03
- 编译器: clang/clang++ (OHOS SDK llvm 15)
- 状态: published
- Profile: ci/conan/profiles/ohos-aarch64（aarch64-linux-ohos, OHOS 6.0）

## 编译步骤

1. W0 依赖预检：gtk/3.24.38、guile/2.2.7.1、gc/8.2.12、gmp/6.3.0、
   libffi/3.4.4、libunistring/1.0 全部已发布于 ohpcd，`--build=missing`
   无需重编依赖。
2. 探索期原生 configure/make/make install 通过（configure 选项见
   manifest.yaml）。
3. 生成 3 个补丁 + 随包文件（libguile.h、sxml-match.ss），`git apply`
   在纯净树上验证通过。
4. `conan create` 全量验证通过（29 个依赖 + lepton-eda），随后
   `conan test` 端到端冒烟通过（3 项测试全部 PASS，见 reports/）。
5. `ohc-run.py conan-verify lepton-eda 1.9.18` 通过（G1/L2/L4/L5）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 aarch64-unknown-linux-ohos | 2022 年的 config.{guess,sub} 太旧 | 0001 补丁加入 HarmonyOS case，输出 `aarch64-unknown-linux-ohos` |
| 2 | docs/ 子目录构建失败 | 需要 texinfo 等目标设备不可用工具 | 0002 补丁从顶层 SUBDIRS 中移除 docs |
| 3 | lepton ffi 调 `add-config-callback!` 时段错误 | Guile 的 libffi closures 在 OHOS 不可用 | 0003 补丁使 `add-config-callback!` 恒返 #f（add-config-event!/remove-config-event! 随之变 no-op，仅禁通知，配置读写不受影响） |
| 4 | `libguile.h` 找不到 | 发布的 guile/2.2.7.x 二进制包含 `libguile/*` 但缺汇总头 | recipe 随包导出上游 2.2.7 umbrella 头（同 libctl 4.5.1 先例） |
| 5 | install-sh 相对路径解析失败（`../.././build-tools/install-sh`） | configure 以相对路径调用时 am_aux_dir 为相对路径 | recipe 用绝对路径调用 configure |
| 6 | HMDFS setgid 目录下 config.status 0700 临时目录不可写 | HMDFS 语义 | `_make_configure_tmp_writable`：umask 077→007、mktemp→mkdir（任务本地组可写） |
| 7 | netlist 运行期 `dynamic-link "liblepton"` file not found | **OHOS dlopen 只接受 `.so` 结尾或无扩展名，拒绝 `.so.N`**；guile 的 dynamic-link 不补后缀 | 设 runenv `LIBLEPTON/LIBLEPTONGUI` 指向 `lib/*.so`（无版本号文件）；lepton ffi 模块原生支持这两个覆盖变量 |
| 8 | netlist 期 `(sxml match)` 模块缺失 | 发布 guile 包缺 sxml/sxml-match.ss | 随包导出该文件：build 期进 GUILE_LOAD_PATH，package 期装到 share/lepton-eda/scheme/sxml/ |
| 9 | 装出的 lepton-* 脚本内嵌构建期 guile 与 prefix 绝对路径 | autotools 标准 bake 行为 | package() 正则重写：`exec "${GUILE:-guile}"` + scheme/ccache 路径改为相对脚本位置（dirname 为 guile core 函数，已验证）；C 侧系统数据目录经 `XDG_DATA_DIRS=<pkg>/share` runenv 定位（eda_get_system_data_dirs 走 g_get_system_data_dirs） |
| 10 | `--prefix=/` + DESTDIR 安装后 m4.scm 中的 GTK soname | 上游用 ldconfig -p 生成 | configure precious 变量 `USE_LDCONFIG=<fake 脚本>`（上游正式接口），fake 输出 libglib/gobject/gtk-3 sonames |
| 11 | 上游测试运行环境的平台差异 | 见下方「上游测试真实执行」专节 | 纯运行时环境手段（LD_PRELOAD 垫片 ×3、guile 包补装漏装文件、构建树内符号链接），未改上游测试/源码 |

## 上游测试真实执行（make check，最终轮全量）

- 在 conan 构建树内原样运行上游 `make check`（automake 并行测试协议）：507 个测试文件，**2814 条测试结果 = PASS 2655（94.35%）/ FAIL 156（5.54%）/ XFAIL 3**（上游预期失败）。
- 分套件：C 单测 17/17；Scheme 单测 1619/1641；顶层集成测试 archive 12、cli 26/29、config 340/357、embed 12、export 56、netlist 20、shell 40/153、symcheck 58、tragesym 12、upcfg 12、update 26/27；netlist golden 回归 405/408（3 XFAIL）。
- 156 项失败全部归因（无未解释失败）：
  1. 116 项（shell 113 + cli 3）：conan guile 包缺 `(ice-9 readline)` 模块（依赖包内容缺口）；
  2. 17 项（lepton-config 9 + geda-config 8）：0004 补丁禁用 libffi closures（回调注册 no-op）；
  3. 17 项（tests/config）：HMDFS `chmod #o000` 无效，无法构造不可读文件场景；
  4. 4 项（library-source-library 3 + update 1）：HMDFS 元数据可见性延迟，隔离复跑全部 PASS；
  5. 2 项（object-bounds/object-copy）：OHOS Guile 对立即数不抛 wrong-type-arg，负向断言不触发。
- 环境垫片（均为运行时手段，非上游测试/源码修改）：
  1. `tmpnam` 垫片：`/tmp` 只读 erofs → 重定向 Guile tmpnam 到可写 TMPDIR；
  2. uid/gid 垫片：HMDFS 属主与进程 uid 不匹配 → getuid 族返回构建树属主、setuid 族 no-op；
  3. `file` 垫片：toybox file 不识别 SVG/PS/EPS 魔数 → 内容嗅探补齐（configure 烧死的 `FILE=/system/bin/file` 在构建树 Makefile 内改为指向垫片）；
  4. guile 包目录补装漏装的 `sxml/sxml-match.ss`；构建树内 LIBLEPTON/LIBLEPTONGUI 符号链接（绕开 OHOS dlopen 拒绝 `.so.N`）。

## 源码修改

- 补丁：patches/0001~0003（见 manifest.yaml），基于上游 1.9.18 tarball。
- 随包文件：patches/libguile.h（guile 2.2.7 上游）、patches/sxml-match.ss
  （lepton 上游 module/sxml/，guile 包漏装）。

## 运行时注意事项（消费者）

- 消费者的 runenv 会自动获得 PATH/LD_LIBRARY_PATH/GUILE_LOAD_PATH/
  LIBLEPTON/LIBLEPTONGUI/XDG_DATA_DIRS/GUILE_AUTO_COMPILE=0
  （Conan runenv 传递，test_package 已验证）。
- GUI Warning "Failed to find PT_GNU_RELRO" 为 Guile GC 已知无害告警。
- 图形程序（lepton-schematic 等）依赖 GTK3 运行环境（显示服务），
  冒烟覆盖 CLI/批量工具路径；图形路径未在无显示环境的目标机上验证。
---

**编译结束**: 2026-10-10 23:10
**最终状态**: built（上游测试 make check 真实执行完成：2655 PASS / 156 FAIL / 3 XFAIL）
