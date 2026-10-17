# inoticoming

`inoticoming` 是一个监听目录的守护进程：通过 Linux 的 inotify 框架监视一个
"到货目录"，一旦出现名字匹配（`--prefix` / `--suffix` / `--regexp`）的文件，
就执行指定动作（例如调用 reprepro 把上传的 `.changes` 收进仓库）。

监听的事件是 `IN_MOVED_TO`（文件被改名/移动进来）与 `IN_CLOSE_WRITE`
（文件被写入并关闭），因此动作只会在文件"写到完整"之后触发。

```sh
# 监听 /srv/incoming，凡是 *.changes 就交给 reprepro
inoticoming --foreground /srv/incoming \
    --suffix .changes --chdir /srv/incoming \
    /usr/bin/reprepro --basedir /srv/repo incoming {} \;

# 生产模式：后台运行并写日志
inoticoming --pid-file /run/inoticoming.pid --logfile /var/log/inoticoming.log \
    /srv/incoming /usr/bin/reprepro incoming {} \;
```

## OHOS 适配要点

- **构建系统**：上游自带 autotools 生成物（`configure` + `Makefile.in` +
  `ac/` 辅助脚本），不需要 autoreconf/automake（CI worker 无 automake）。
  配方用 Conan 的 `Autotools` 助手执行 `configure` / `make` / `make install`
  （`DESTDIR=<package_folder>`，前缀为 `/`），编译器取自
  `tools.build:compiler_executables`（R33，不依赖 shell 裸变量）。
- **E011（HMDFS + autoconf 临时目录）**：HMDFS 把新建目录映射到 uid
  20001006 且保留 setgid 位，autoconf 的
  `(umask 077 && mktemp -d "./confXXXXXX")` 临时目录因此是 `drwx--S---`，
  构建用户自己也无法写入，`config.status` 直接报
  `can't create ./confXXXXXX/subs1.awk: Permission denied`。
  修复方式：`patches/0001-configure.patch` 把发行包自带 `configure` 里的
  `umask 077` 放宽为 `umask 022`（2 处），由 `conandata.yml` 声明、配方
  `build()` 通过 `apply_conandata_patches()` 施加；`config.status` 由该
  `configure` 生成，随之生效。补丁作用于 source 目录，与 `basic_layout`
  的 `build_folder`（`build-<build_type>`）取值无关 —— 若改为在配方内联
  替换且只扫 `build_folder`，`configure` 会被 `os.path.isfile` 守卫静默
  跳过，症状与"完全没修"一致。
- **inotify 可用性**：OHOS libc 提供 `sys/inotify.h` 与
  `inotify_init`/`inotify_add_watch`/`inotify_rm_watch`，内核侧事件
  （`IN_CLOSE_WRITE`、`IN_MOVED_TO`）实测可正常投递，因此
  `--initialsearch`、前缀/后缀过滤、`{}` 替换等上游功能全部保留，未做
  功能裁剪，也没有平台宏 stub（R8/R40）。
- **syslogd**：OHOS 默认没有 syslogd。守护进程在 `--foreground` 下直接写
  stdout/stderr，生产模式用 `--logfile`，二者都在 test_package 中实测。
- **上游测试**：0 个（见 `0.2.3/test_package/MANIFEST.yml` 审计）。上游
  `Makefile.am` 没有 `TESTS`/`check_PROGRAMS`，automake 生成的
  `make check` 不注册任何用例（实测退出码 0 且无输出），配方仍在
  `build()` 中执行该目标以保留真实测试入口。

## 依赖关系

- 编译依赖：无（仅 libc；inotify 接口由 libc/内核提供）。
- 运行依赖：仅 libc。被调用的动作程序由使用者自行提供。

## 参考资料

- 源码（Debian pool，`make dist` 的原始上游发行包）：
  https://deb.debian.org/debian/pool/main/i/inoticoming/inoticoming_0.2.3.orig.tar.gz
- Debian 源码页：https://sources.debian.org/src/inoticoming/
- 许可证：GPL-2.0-or-later（`COPYING`）
