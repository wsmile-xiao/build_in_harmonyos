# vcdimager — GNU (Super)VideoCD 制作工具集

> 把 MPEG 节目流打包成可烧录的 VCD 1.1/2.0、SVCD 光盘镜像（BIN/CUE），并可生成与回读 XML 光盘描述。

## 简介

GNU VCDImager 是 (Super)VideoCD 的「制作 / 拆取 / 分析」命令行方案（上游 README 自述：
*the GNU (Super)VideoCD authoring solution for mastering, extracting and analyzing Video CDs and
Super Video CDs*）。包的核心是私有库 `libvcd` 与公开库 `libvcdinfo`，命令行前端只是它们的一套
用户接口，因此各前端共享同一份光盘描述与 MPEG 流解析逻辑。

产出的镜像为 BIN/CUE 形态，交给识别该格式的刻录程序（例如 cdrdao）写入 CD-R。
支持的盘制式为 Video CD 1.1 / 2.0 与 Super Video CD。

## 功能概述

随包安装的命令行程序 7 枚。实据：`frontends/cli/Makefile.am:18` 的
`bin_PROGRAMS = vcdimager cdxa2mpeg vcd-info`，`frontends/xml/Makefile.am:19` 的
`bin_PROGRAMS = vcdxbuild vcdxgen vcdxrip vcdxminfo`；逐条职责取自上游手册
`docs/vcdimager.texi` 的 "Supplied Tools" 节。

| 命令 | 职责 |
|------|------|
| `vcdimager` | 经典前端：不经中间 XML 描述，直接用命令行参数生成基本 VCD/SVCD 光盘镜像 |
| `vcd-info` | 选择性显示一张 Video CD 的结构细节 |
| `cdxa2mpeg` | 剥掉 CD-XA 格式轨道上的 RIFF 头，取出其中的 MPEG 流 |
| `vcdxgen` | 生成 XML 光盘描述，命令行风格与 `vcdimager` 相近 |
| `vcdxbuild` | 按给定的 XML 描述及其引用的 MPEG 节目流构建 VCD/SVCD 镜像 |
| `vcdxrip` | 把 VCD/SVCD 光盘拆成 XML 描述 + 包内 MPEG 节目流 |
| `vcdxminfo` | 调试工具：显示 `libvcd`/`libvcdinfo` 眼中的 MPEG 属性 |

## OHOS 适配

### 适配路径与源码补丁

- 归档走路径 B（Conan 配方 + 一处随包源码补丁）；版本特定的编译配置在 `2.0.1/conanfile.py`，
  编译过程记录在 `2.0.1/notes.md`，本节只记软件层面的事实。
- 唯一源码补丁 `2.0.1/patches/0001-vcd-xml-common-libxml2-2.15-enc-handler-union.patch`：
  libxml2 2.15 把 `xmlCharEncodingHandler` 的 `input`/`output` 改成了匿名 union，
  上游 `frontends/xml/vcd_xml_common.c` 里 2018 年那处直调在 C 中不再合法；而只按旧式 4 参成员
  改到「能编译」会在运行期参数错位、被 SIGSEGV 打死。补丁的正解是改走带方向上下文的新式
  `func(...)` 调用（判空守卫语义不变，union 两成员同址）。机制与取证见随包知识草稿。

### 平台差异（配方侧处理，不改源码）

- 构建文件系统上的限制：构建树取 `getcwd()` 被拒、在新建目录里写文件被拦 ⇒ 配方预置 `PWD` 与
  临时目录，并把 configure 的临时件指向预建目录。
- `/usr/bin/diff` 在 OHOS 是 toybox 软链，上游回归比对用的 `-w --unified` 会被它判 EINVAL ⇒
  配方用上游本就支持的 `DIFF` 变量覆盖为依赖图里的 GNU diffutils 绝对路径
  （`diffutils/3.12`，`tool_requires`）。

### 已知限制

- 上游 `make check` 的 8 项里 `testvcd` 需要物理 CD-ROM 中有一张 (S)VCD；无介质的构建/CI 环境
  下它自行返回 77 记为 SKIP，属环境跳过而非平台缺陷。同理 `vcdxrip`、`vcd-info` 的读盘功能要有
  真实介质才能跑全。
- 经典前端 `vcdimager` 不产出 PBC（0.7.x 之后的行为变更，上游 README 明写）；要菜单、播放列表、
  附加入口点等高级特性必须走 XML 那组前端（`vcdxgen` + `vcdxbuild`）。

## 依赖关系

编译与运行依赖（版本级 `conanfile.py` 的 `requirements()`）：

| 依赖 | 用途 | 缺失时上游 configure 的行为 |
|------|------|------------------------------|
| `libcdio/2.3.0` | 光盘与镜像访问（该归档是 libcdio + libiso9660 的合集） | `configure.ac:296`/`:301` 直接 `AC_MSG_ERROR` |
| `popt/1.16` | 命令行参数解析 | `configure.ac:175` 静默把 CLI 与 XML 两个前端都置 no |
| `libxml2/2.15.3.1` | XML 光盘描述的解析与产生（要求 >= 2.3.8） | `configure.ac:179` 静默关掉 XML 前端 |

构建期工具依赖：`diffutils/3.12`（`tool_requires`，上游回归比对需要 GNU diff）。

包内自带、不需外部提供的部分：私有 `libvcd` 与公开 `libvcdinfo`（`libvcdinfo.pc.in` 随源码）。
正因缺依赖会「编得过但功能被静默裁掉」，配方按完整功能集声明依赖，不使用 `--disable-*` 绕过。

## 参考资料

- 官网：<https://www.gnu.org/software/vcdimager/>
- 源码发布目录：<https://ftp.gnu.org/gnu/vcdimager/>
- 上游手册（随源码发布）：`docs/vcdimager.texi`、`docs/vcd-info.texi`、`docs/vcdxrip.texi`
- 许可证：GPL-2.0-or-later
