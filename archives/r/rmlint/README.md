# rmlint

`rmlint` 扫描目录树并报告**磁盘垃圾**：内容重复的文件（校验和或尺寸+校验和混合模式）、空目录、
坏软链、未 strip 的二进制、超大/空文件等；输出可选人类可读、CSV、JSON、py/sh 脚本等形式，
并可按 `--types`/`--severity`/排序策略精细控制。上游 <https://github.com/sahib/rmlint>（GPL-3.0-or-later）。

## 功能概述

- `rmlint [options] <path>...` — 单一可执行文件，扫描成功退出码恒为 `0`（2.x 实测，与是否发现垃圾无关；脚本请解析报告文本判定）
- Finder 类型 `-T`：`rf`（重复文件）、`ed`（空目录）、`bf`（坏软链）等；`ns`（未 strip 二进制）需 libelf，本适配未开启
- 输出面：`-o <fmt>`（`pretty`/`json`/`csv`/`py`/`sh` …）与 `-O <file>` 重定向
- 动作型模式（`--reflink`、`--unlinker`、把校验和写进 xattr）依赖硬链接/reflink/fallocate，**在 HarmonyOS PC 的 HMDFS 上受限**（见下）

## 依赖关系

- 编译/运行依赖：`glib/2.84.0.1`（唯一必需，`glib-2.0 >= 2.64`，SConstruct 中 `required=True`）
- 构建工具：`pkgconf/3.0.5`（上游全程经 pkg-config 发现依赖）、SCons 4.10.1（构建沙箱内自举，见下）
- **不依赖 libyaml**：2.10.3 全树零 yaml 引用，配置解析自研于 `lib/cfg.c`（常见认知需纠正）
- 已关闭的可选面：`blkid`、`json-glib`、`libelf`、`gettext`、GUI、glib schemas 编译

## OHOS 适配要点

- **构建系统 SCons 在本平台无外部供给**：设备既无 `scons` 二进制也无 `SCons` python 模块，
  ohpcd 制品仓也没有 SCons 配方（`conan download scons/4.8.1 -r=ohpcd` 报错），
  因此不能走 `tool_requires`。配方沿用仓内 `gpsd/3.26`、`dxx-rebirth/0.6`、`vixl/5.1.0`
  三个已合并配方的既有形态：在 `generate()` 里把 SCons `pip install --target=<build_folder>/_scons_env`
  装进 **Conan 构建目录内的私有前缀**（不写用户/系统 Python 环境），经 `PYTHONPATH` 以
  `python3 -m SCons` 调用；并 patch 掉 `SCons.Platform.posix` 写死的 `SHELL='sh'`
  （OHOS 无 `/bin/sh`，实测存在 `/system/bin/sh`）。
- **SConstruct 会裁剪子进程环境**为 `PATH/TERM/HOME/PKG_CONFIG_PATH` 四项
  ⇒ glib 的发现只能靠 `PKG_CONFIG_PATH`，经 `CFLAGS/LDFLAGS` 注入无效；
  编译器/归档器经 SCons 命令行变量 `CC/AR/RANLIB` 从 conan conf 取值（R33）。
- **pkg-config 接线**：glib 包自带的 `glib-2.0.pc` 里 `prefix=/`（不可直接使用），
  改用 `PkgConfigDeps` 生成的绝对路径版本；`PkgConfigDeps` 不产出 `gio-unix-2.0.pc`，
  该探测在上游是 `required=False`，只影响"非旋转盘"优化（其本身还需已关闭的 blkid）。
- **不用 `scons install` 打包**：`docs/SConscript` 把 sphinx 生成的 man page 同时注册为
  default 与 install 目标，而 sphinx/rst2man 在本平台不存在 ⇒ `package()` 直接
  copy 源根 `./rmlint` 与 `COPYING`/`README.rst`（同 `abr2gbr/1.0.2`、`vamps/0.99.2`）。
- **文件系统能力面实测**：HMDFS 拒绝 `link(2)`（EPERM）、`fallocate` 返回 EACCES、
  Python 侧无 `os.SEEK_HOLE/SEEK_DATA`；但 `symlink(2)` 可用、`user.*` xattr 可写可读、
  inode 语义正常，`sys/xattr.h`/`linux/fs.h`/`linux/fiemap.h`/`sys/ioctl.h` 均在 sysroot。
  ⇒ 本包交付**扫描-报告**能力，不承诺**改写-去重**能力。
- 上游 149 项 pytest 用例本轮**未执行**（本机无 pytest/psutil/xattr，且其硬链接夹具
  `tests/utils.py:create_link()` 依赖被 HMDFS 拒绝的 `link(2)`），已在
  `test_package/MANIFEST.yml` 逐条标 `not_run` + 技术原因；改以 6 个避开硬链接/xattr 写/
  fallocate 的鸿蒙消费者用例实测二进制功能（R34）。

## 参考资料

- 项目主页：<https://github.com/sahib/rmlint>
- 版本级适配笔记：`2.10.3/notes.md`（含实测读数与已试过的失败方案）
