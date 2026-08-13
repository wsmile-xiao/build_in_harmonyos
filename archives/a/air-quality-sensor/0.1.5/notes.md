# air-quality-sensor 0.1.5 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am，单二进制 `air-quality-sensor`)
- 编译日期: 2026-08-12
- 编译器: clang/clang++
- 状态: built（真机预检待跑，通过后由 HMBS 统一提交）

## 编译步骤

```bash
# 源码包: Debian orig tarball（0.1.5 无 GitHub tag，tags 止于 0.1.4.2；
#         作者站点 thinserv2.at-inet.de 403，PureOS/deb.debian.org 镜像同源）
# conan create 流程:
#   1. autoreconf --install  (tarball 未预生成 configure，仅 configure.ac + aux 文件)
#   2. ./configure  (PKG_CHECK_MODULES([libusb-1.0]) 经 PkgConfigDeps/AutotoolsDeps 注入)
#   3. make -j1
#   4. make install DESTDIR=<package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 0.1.5 无 GitHub tag、作者站点 403 | 0.1.5 仅以 Debian orig tarball 形式发布 | conandata.yml 用 PureOS + deb.debian.org 双镜像（字节一致，sha256 固定） |
| 2 | tarball 无预生成 configure | 发布包是源码快照，configure 是 autoreconf 产物 | tool_requires automake/1.18 + libtool/2.5.4，build() 中 autoreconf --install（E178 同款） |
| 3 | help2man 在 OHOS 不可用 | src/Makefile.am 用 $(HELP2MAN) 再生 manpage | patch 移除再生规则，tarball 内置的 air-quality-sensor.1 直接安装 |
| 4 | config.status 临时目录不可写 | E114: autoconf 以 umask 077 建临时目录，HMDFS 沙箱不可写 | build() 中把生成的 configure 里 umask 077 改为 umask 000 |
| 5 | configure 找不到 pkg.m4 | PKG_CHECK_MODULES 宏在 pkg-config 安装目录 | generate() 注入 ACLOCAL_PATH（/data/service/hnp/*/*/share/aclocal glob + build() 动态探测） |
| 6 | 依赖 libusb-1.0 | configure.ac 用 PKG_CHECK_MODULES([LIBUSB1_0], [libusb-1.0]) | requires libusb/1.0.27（仓库已归档），PkgConfigDeps + AutotoolsDeps 生成 .pc 与 flags |
| 7 | 首轮真机预检 configure 失败：`working directory cannot be determined`（前置报错 `can't create temporary file /tmp/shrip4n6.tmp: Read-only file system`） | 两个独立平台问题：E002（/tmp 只读，[readonly_tmp]）+ HMDFS getcwd 向上遍历失败（[shell_getcwd]） | 第一轮先注入可写 TMPDIR/TMP/TEMP（E002，保留） |
| 8 | 第二轮预检仍失败：configure `_AC_INIT_DIRCHECK` 的 `ac_pwd=\`pwd\`` 在 HMDFS 上 getcwd 失败（bash shell-init/job-working-directory 报错 + `pwd: error retrieving current directory`），TMPDIR 修复无效 | [shell_getcwd] HMDFS 文件系统".."向上遍历失败（getcwd 挂），但向前路径解析正常；autoconf 该探测硬性依赖 pwd | 按 nspr/4.37 + analog/homebrew 通过先例：① build() 中 `os.environ["PWD"]=self.build_folder`（bash/mksh pwd 信任有效 $PWD 而不调 getcwd）；② `os.chdir(self.build_folder)`；③ 把 configure 的 `ac_pwd=\`pwd\` && test -n "$ac_pwd" &&` 改为 `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"` 兜底（模式未命中时告警） |
| 9 | 第三轮预检（PWD 修复已生效）：configure 越过目录探测，新失败于 `checking whether we are cross compiling... cannot run C compiled programs`（错误信息提示 "If you meant to cross compile, use '--host'"） | [run_conftest] 构建沙箱内新编译的 conftest 无法执行（加载器/执行限制）；autoconf 在 cross_compiling=no 时 conftest 运行失败即硬错误 | 按 autoconf `_AC_INIT_PARSE_ARGS` 机制（`--host` 单独给出 → cross_compiling=maybe → 运行失败转 yes，跳过运行期探测；相同 `--build/--host` 反而不触发）+ a52dec/nspr 三元组先例：generate() 为 OHOS 加 `--host=aarch64-unknown-linux-gnu`（不配相同 --build），build() 预置 `ac_cv_build` 跳过 config.guess |

## 源码修改

- `patches/0001-src-makefile-am-drop-help2man.patch`：删除 src/Makefile.am 的
  `air-quality-sensor.1: $(air_quality_sensor_SOURCES) $(man_include)` 规则
  （help2man 不可用；manpage 随 tarball 发布，man_MANS 照常安装）。

## 依赖版本

- libusb/1.0.27（conan，仓库 archives/l/libusb/1.0.27）
- 构建工具: automake/1.18, libtool/2.5.4（tool_requires）

## 验证结果

```bash
# 真机预检（HarmonyOS aarch64，hmbs 统一调度）通过后由 HMBS 更新此节；
# test_package 执行:
#   air-quality-sensor --version   → 输出含 0.1.5 版本行
#   air-quality-sensor --help      → 输出 Usage: 用法
#   air-quality-sensor（裸运行）    → 按上游 main() 语义 exit(ret?EXIT_FAILURE:EXIT_SUCCESS)：
#                                     无匹配传感器且 USB 总线可读 → rc=0 干净退出；
#                                     受限环境读不到 USB 描述符（libusb 错误累加进 ret）→ rc=1。
#                                     两者均属正常退出路径（崩溃才判失败）。
```

## 注意事项

- 上游 0.1.5 无任何测试套件（已审计：无 tests/ 目录、Makefile.am 无 check 目标、
  无 TESTS 变量），MANIFEST.yml 已写 `upstream_tests_exist: false` + 审计结论；
  test_package 输出 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`。
- 该工具运行时依赖 USB 传感器硬件；无硬件时按上游语义退出：USB 总线可读 → rc=0，
  受限环境读不到 USB 描述符 → rc=1（src/air10.c 的 exit(ret ? EXIT_FAILURE : EXIT_SUCCESS)）。
- `--version` 输出版本串为 0.1.5.0（configure.ac 的 AC_INIT 原样），打包版本为 0.1.5。
