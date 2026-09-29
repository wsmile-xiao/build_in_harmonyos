# metar

METAR 是航空气象例行天气报告（Meteorological Aerodrome Report）。`metar` 是一个小型
命令行工具：按 ICAO 站号从 NOAA 抓取该站最新的 METAR 报文，并可选地把它解码成可读字段。

```console
$ metar -d ehgr
EHGR 271350Z 05003KT 0600 BKN015 M02/M08 Q1023
Station       : EHGR
Day           : 27
Time          : 13:50 UTC
Wind direction: 50 (NE)
Wind speed    : 3 KT
Visibility    : 600 M
Temperature   : -2 C
Dewpoint      : -8 C
Pressure      : 1023 hPa
Clouds        : BKN at 1500 ft
```

## 用法（上游契约）

```
Usage: metar options
Options
   -d        decode metar
   -v        be verbose
   -h        show this help
```

- 无参数或未知选项 → 打印 usage 并以非零码退出；`-h` → 打印 usage 并以 0 退出。
- 取数地址默认 `https://tgftp.nws.noaa.gov/data/observations/metar/stations`，
  可用环境变量 `METARURL` 覆盖（`src/main.c` 的 `download_Metar()`），实际请求
  `<METARURL>/<大写站号>.TXT`。
- 报文头解析只认斜杠日期（`^([0-9/]+ [0-9:]+)`），不匹配时打印
  `METAR pattern not found in NOAA data.`；注意上游 `download_Metar()` 即使
  `curl_easy_perform()` 失败也返回 0，因此**取数失败时退出码仍为 0**，只能靠输出内容判断。

## OHOS 适配

- 构建系统：上游 tarball 自带 GNU autoconf **2.59** 预生成的 `configure` 与 automake 1.8
  的 `Makefile.in`；`VERSION.m4` 定义版本 `20190227.1`。上游 `bootstrap` 需要
  aclocal-1.8/automake-1.8（鸿蒙侧没有），因此**走预生成 configure，不自举**。
- `configure.ac` 无 `AC_CANONICAL_HOST`，tarball 内**既没有 config.guess 也没有
  config.sub** ⇒ 本包不存在鸿蒙三元组识别墙，不需要平台三元组补丁。
- 唯一外部依赖 libcurl（`AC_CHECK_LIB([curl],[curl_easy_init])`，探不到即
  `AC_MSG_ERROR(Unable to find required library libcurl)`）：配方 `requires`
  `curl/8.15.0`，`generate()` 同时出 `AutotoolsToolchain` 与 `AutotoolsDeps`。
- `patches/0001-hmdfs-config-status-umask.patch`：autoconf 2.59 生成的
  `config.status` 用 `umask 077` + `mktemp -d` 建临时目录，HMDFS 上 0700 目录对当前
  进程不可写（`can't create ./confstatXXXXXX/subs.sed: Permission denied`），三个
  Makefile 全部生成失败 —— 按知识库 E011/E114 改 `umask 022`。
- `configure --disable-maintainer-mode`：automake 1.8 的 maintainer 模式默认开启，
  补丁改过 `configure` 后 `make` 会沿 `aclocal → autoconf` 再生成（设备上是 autoconf
  2.72，与 2.59 生成的脚本不同构），关掉即从根上不走再生成链。
- man 页：tar 内 `doc/metar.1` 与 `doc/metar.pod` 的 mtime 完全一致，`pod2man` 规则
  不被触发，直接用上游自带 man 页安装，构建不依赖 perl。
- 上游无任何自动化测试套件；功能验证由 `test_package/test.sh` 承担，且**全程离线**
  （用 `METARURL=file://` 喂 NOAA 报文样本，真实跑完取数→解析→解码）。

## 依赖关系

- 编译/运行依赖：curl/8.15.0（conan 运行环境注入 `libcurl.so` 路径）

## 参考资料

- 上游原版归档（Debian pool 的 pristine `.orig.tar.xz`）：
  https://deb.debian.org/debian/pool/main/m/metar/metar_20190227.1.orig.tar.xz
- 包信息页：https://packages.debian.org/source/sid/metar
- 原上游项目页（alioth，已关停）：http://alioth.debian.org/projects/metar/
