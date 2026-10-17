# mpdas 0.4.5 — HarmonyOS PC 构建归档

- 软件：mpdas（MPD「正在播放」状态栏客户端，作者 Henrik Friedrichsen / 50hz）
- 版本：0.4.5
- 构建系统：makefile（上游 Makefile，无 configure）
- 语言：C++（8 个 .cpp + 8 个头文件）
- 许可证：ISC
- 上游主页：<https://50hz.ws/mpdas/>
- 源码包来源：<https://50hz.ws/mpdas/mpdas-0.4.5.tar.gz>
  （sha256 `c9103d7b897e76cd11a669e1c062d74cb73574efc7ba87de3b04304464e8a9ca`，19108 字节；
  上游作者官方站 https 直链发布件。与 Debian 权威存档 pristine `.orig`
  （<https://deb.debian.org/debian/pool/main/m/mpdas/mpdas_0.4.5.orig.tar.gz>，18884 字节，
  sha256 `b52ac99a66bf54318fc98fe09ba81f527906e28e93fba616f905f4c05b0296e1`）实测比对：
  23 个共有文件字节全等，官方件仅多一个 242 字节的 `.gitignore` ⇒ 取上游官方件）
- 依赖：`libmpdclient/2.23`、`libcurl/8.5.0`（**plain name/version 形态**，两者在 ohpcd 制品仓均已发布；`@ohpcd/stable` 形态在本仓实测**不可解析**——`conan graph info --requires=libmpdclient/2.23@ohpcd/stable --build=never` rc=1，与第一轮 create 的 `not resolved` 同源），反证与仓内写法普查见 `notes.md:33-48`

## 构建

```bash
conan create archives/m/mpdas/0.4.5 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

> 说明：上面构建命令里的 `--user=ohpcd --channel=stable` 是给 **mpdas 自己**指定 user/channel（产物引用为 `mpdas/0.4.5@ohpcd/stable`，合法），与**依赖的引用形态**是两件事——`conanfile.py:34-35` 的两条 `self.requires()` 用的是 plain `name/version`（理由见 `notes.md:33-48`）。

配方把上游 Makefile 里用反引号写死的 `pkg-config --cflags/--libs libmpdclient libcurl`
参数化为 `DEPS_CFLAGS` / `DEPS_LIBS`（补丁 0001），改由 Conan 依赖图提供真实的
`-I/-L/-l/-Wl,-rpath` 标志；编译器取自 `tools.build:compiler_executables` 的 `cpp`
（R33），`make -j1`（R9）。安装由配方内 `copy()` 完成——OHOS 无 coreutils `install(1)`，
且上游 `install` 目标写死 `${PREFIX}/bin`。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/mpdas` | 可执行文件（aarch64 ELF） |
| `man/man1/mpdas.1` | 上游手册页 |
| `conf/mpdasrc.example` | 配置样例 |

## 运行

```bash
mpdas -v                     # 版本 + 编译期内置的全局配置路径
mpdas -h                     # 用法
mpdas -c /path/to/mpdasrc    # 指定配置文件（[Last.fm] username/password）
```

详细适配过程与限制见 `notes.md`。
