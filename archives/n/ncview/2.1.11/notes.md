# ncview 2.1.11 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，CI 无需 autoreconf）
- 编译日期: 2026-09-09
- 编译器: clang 15（/data/service/hnp/bin/clang）
- 状态: built（conan create + test_package 全部通过）

## 方案总览

ncview 是 X11/Athena widget 的 netCDF 可视化浏览器。适配核心难点不在 ncview
本身，而在它的 5 个"消失的依赖"：远端制品仓没有 libxaw/libxmu/udunits，
libxext/libxpm 的远端包钉死了与 libxt 冲突的 libx11/6.4.0。方案：

1. **vendored 静态编译** libXext-1.3.7 / libXmu-1.2.1 / libXpm-3.5.17 /
   libXaw-1.0.16 / udunits-2.2.28 到 build 目录私有 prefix（R49），链接进
   ncview 可执行文件，均不打包。全静态 → 无 .so 软链（绕 HMDFS 坑）、
   无 libtool .la 依赖解析（绕陈旧路径坑）。
2. **configure 区块 strip**：ncview 的 configure 里 7 个检测宏
   （AC_PATH_NETCDF / AC_PATH_X / AC_PATH_XTRA / Xaw 检测 / X11 检测 /
   AC_PATH_UDUNITS2 / AC_PATH_PNG）整段替换为直接赋值，依赖路径以字面量
   烤入（agg 2.7.0.r145 同款手法，build() 内字符串替换，不用 conandata.yml）。
3. **E007 平台识别**：Python 移植 patch-autotools-ohos.pl 打全部
   config.guess/config.sub（含 5 个 vendored 树），并额外处理了知识库脚本
   没覆盖的两个老脚本坑（见下）。

## 链接关系（最终）

- 静态进二进制：libXaw7.a、libXmu.a、libXpm.a、libXext.a、libudunits2.a
- 动态（conan 管理）：libnetcdf.so.22、libX11.so.6、libXt.so.6、
  libpng16.so.16、libexpat.so、libc.so
- ncview_LDADD 链接顺序：XAW_LIBS(-lXaw7 -lXmu -lXpm -lXt -lXext) →
  X_LIBS(-L...) → X11_LIBS(-lX11) → NETCDF_LDFLAGS(-L... -lnetcdf) →
  UDUNITS2_LDFLAGS(-L... -ludunits2 -L... -lexpat) → -lpng → -lm

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 远端 libxext/libxpm 钉死 libx11/6.4.0，与 libxt 需要的 libx11/1.8.13 冲突 | 远端这批包按 6.4.0 版本线适配 | vendored libXext-1.3.7 / libXpm-3.5.17 |
| 2 | udunits2 标称可选但 utCalendar2_cal.c 无条件 include udunits2.h、引用 ut_* 符号 | 上游 configure 的"可选"是假象，链接必炸 | vendored udunits-2.2.28，UDUNITS2_LDFLAGS 始终注入；HAVE_UDUNITS2 保持不定义（udu.c 走上游默认 stub，时间轴转换功能真实可用） |
| 3 | config.guess: cannot guess build type（uname -s = HarmonyOS） | E007 老问题 | 移植 patch-autotools-ohos.pl 为 Python（CI 无 skill 环境，必须自包含） |
| 4 | libXmu 2013 版 config.guess 打了 HarmonyOS 补丁仍报 unable to guess | 老脚本主 case 是 echo+exit 风格，GUESS 赋值风格的补丁块赋值后被丢弃，落进尾部编译 fallback | 补丁块风格自适应：检测脚本是否 `echo $GUESS`，老脚本输出 echo+exit 分支 |
| 5 | 老版 config.guess 临时目录 umask 077 && mktemp -d → HMDFS 拒绝在 700 目录写 dummy.c | mktemp -d 恒建 700 目录（umask 无效），HMDFS 特性 | 把 mktemp 分支替换为 umask 022 的 mkdir+echo；其余 (umask 077 && mkdir 同步放宽为 022 |
| 6 | 2013 版 config.sub 拒绝 aarch64-unknown-linux-ohos | 老三元组表无 ohos | 老式脚本改输出 linux-gnu 三元组（CC 来自环境，行为无差） |
| 7 | 新版 config.sub (2024) 拒绝 linux-ohos：Kernel 'linux' not known to work with OS 'ohos' | 新增 kernel-OS 一致性校验段，老锚点（linux-uclibc*) 匹配不上 | 追加锚点：`linux-gnu* | linux-dietlibc*` → 追加 `\| linux-ohos*`；注意守卫不能被前序补丁的副产物（ohos-linux 三元组）短路 |
| 8 | libXmu CCLD 报 libtool: error: '.../libX11.la' is not a valid libtool archive | conan X 系包安装的 .la dependency_libs 带陈旧绝对缓存路径（原构建机 ~/.cache/conan2），libtool 解析 -l 标志时读取 | XMU/XMUU/XPM/SXPM/XAW7/XEXT 覆盖变量全部改传显式 .so/.a 绝对路径——libtool 原样透传，零 .la 查找 |
| 9 | libXmu 编译缺 X11/Xauth.h、X11/SM/SMlib.h | security.h→Xauth(libxau)；Shell.h→SMlib(libsm)→ICE(libice) | _x_incs 加入 libxau/libsm/libice 的 include（均为图内传递依赖） |
| 10 | Xmu configure: No package 'x11' found (XMUU) | libXmuu 子库有独立的 pkg-config 模块 | 补 XMUU_CFLAGS/XMUUU_LIBS 覆盖；顺带 SXPM_*（libXpm 的 sxpm 工具） |
| 11 | sxpm 链接 undefined XShapeCombineMask | sxpm 工具用 XShape | SXPM_LIBS 加 vendor libXext.a |
| 12 | udunits make/install: makeinfo: command not found (Error 127) | automake 想重建 udunits2.info；vti 规则刷新 version.texi 后 .info 显旧 | make 与 install 都加 MAKEINFO=true，构建后重 touch 三个 texi 时间戳；预置 .info 从 tarball 原样安装 |
| 13 | ncview 最终链接 undefined XML_* symbols (from libudunits2.a) | 静态 libudunits2 依赖 expat，ncview 链接行没有它 | UDUNITS2_LDFLAGS 追加 -L<expat>/lib -lexpat |
| 14 | 测试预期错误：以为 ncview 会先报文件错误，实际先报 Can't open display | ncview 在参数处理阶段就初始化 X toolkit | smoke test 改为断言：非零退出 + 版本 banner + Xt 显示诊断（headless 环境下 GUI 工具的合理冒烟） |
| 15 | CI Worker 源码下载超时（cirrus.ucsd.edu 不可达） | CI Worker 网络受限白名单制；cirrus.ucsd.edu 无仓库先例 | 源 URL 改列表（conan get 按序尝试）：ncview→distfiles.macports.org、udunits→mirrors.ustc.edu.cn/freebsd-ports/distfiles（两处镜像均字节一致、sha256 已核对，域名均为仓内已合并配方验证过的可达域） |

## 运行时说明

- 二进制自带编译进静态库的 Athena widget 集，运行时依赖仅
  libnetcdf/libX11/libXt/libpng16/libexpat/libc，全部由 conan 管理。
- udunits XML 数据库已随包安装到 <package>/share/udunits/。ncview 的
  时间轴转换（utCalendar2_cal）在无显示依赖下即可工作；如需完整 udunits
  单位格式化路径，运行时 export UDUNITS2_XML_PATH=<pkg>/share/udunits/udunits2.xml。
- ncview 无 make check / 测试框架；test_package 用二进制冒烟（版本 banner +
  X11 诊断 + 非零退出 + 动态依赖全加载），R34 合规。

## 版本选择依据

- libXext 1.3.7：仓库 archives/l/libXext/1.3.7 同版本（零补丁），上游 x.org 官方
- libXmu 1.2.1 / libXpm 3.5.17 / libXaw 1.0.16：x.org 官方最新，与主流发行版组合一致
- udunits 2.2.28：上游最新（仓库手工时代记录同版本）
- libpng 1.6.58：其 zlib 钉死 1.6.58.2→zlib/1.3.2 与 netcdf 链冲突，1.6.58→zlib/1.3.1.1 匹配

---

**编译结束**: 2026-09-09 02:12
**最终状态**: built（conan create EXIT=0 + test_package 通过）
