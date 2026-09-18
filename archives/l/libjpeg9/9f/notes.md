# libjpeg9 9f 适配笔记

## 基本信息
- 上游：IJG（Independent JPEG Group）参考实现，https://www.ijg.org/files/jpegsrc.v9f.tar.gz
- 版本：9f（2024-01-14 发布，JPEG_LIB_VERSION = 90）
- 构建系统：autotools（源码包自带 configure / Makefile.in，无需 autoreconf）
- 依赖：无（纯 C，仅依赖 libc）

## 配方要点
- `--enable-static --disable-shared`：产物 `libjpeg.a` 与系统 libjpeg 同名（R26）。仅产出静态库，
  避免动态库落到系统库搜索路径造成覆盖，同时规避 HMDFS 下动态库加载问题。
- `build()` 在 `make` 之后执行 `make check`，直接复用上游 `Makefile.am` 的 `check-local`。
- `package()` 额外拷贝 `README`（IJG 许可证正文）到 `licenses/`。
- 产物：`libjpeg.a`，头文件 `jpeglib.h`/`jconfig.h`/`jerror.h`/`jmorecfg.h`，
  可执行文件 `cjpeg`/`djpeg`/`jpegtran`/`rdjpgcom`/`wrjpgcom`（软件级 `commands.json`，R38）。

## 补丁

### 0001-config.guess.patch（E007 平台识别）
源码包自带的 `config.guess`（timestamp 2021-06-03，较 libjpeg/10 的 2024-07-27 旧）按 `uname -s` 分派，
鸿蒙上 `UNAME_SYSTEM=HarmonyOS` 不落入任何分支，configure 报 `cannot guess build type`。
补丁新增 `*:HarmonyOS:*:*` 分支（9f 锚点在 case 起始行，与 10 的行号不同需重做），
按 `uname -m` 归一化后输出 `aarch64-unknown-linux-ohos`。

### 0002-config.sub.patch（9f 特有）
9f 自带的 `config.sub`（timestamp 2021-08-14）未内置 ohos 三元组（libjpeg/10 的 2024-05-27 版已内置，
无需补丁）。补丁两处：合法 OS case 列表（`... | zephyr*)` 行）追加 `ohos*`；
kernel-OS 组合 case（`linux-musl*` 一带）追加 `linux-ohos*`。缺任一处，
`config.sub aarch64-unknown-linux-ohos` 报 `Invalid configuration`。

### 0003-configure.patch（E011 HMDFS umask）
`configure` 用 `umask 077 && mktemp -d` 创建临时目录，HMDFS 上 700 权限目录内无法再创建文件，
`config.status` 报 `can not create ./confXXX/subs1.awk: Permission denied`。补丁把两处 `umask 077` 改为 `umask 022`
（9f 中位于 L15583/L15588，与 libjpeg/10 的 L16444 一带偏移不同）。

## 测试

### 上游测试（已集成进 build()）
`make check` → `check-local`：`djpeg` 解码 `testorig.jpg`（ppm/gif/bmp 三种输出）、`cjpeg` 编码 `testimg.ppm`
（基线 + 渐进）、`jpegtran` 无损转换 `testprog.jpg`，随后 7 条 `cmp` 与参考图像逐字节比对，
任一不一致即 make 失败。

### test_package（消费者视角）
`test.c` 与 libjpeg/10 相同：`jpeg_mem_dest` 将 64x48 RGB 渐变图以质量 90 编码进内存，校验 SOI 标记（0xFFD8）
与输出长度；再用 `jpeg_mem_src` + `jpeg_read_header` + `jpeg_read_scanlines` 解回，校验尺寸与分量数，
并对每行全部像素与原图逐字节比对（有损编码，阈值 16）。`JPEG_LIB_VERSION` 为 90（测试仅打印该值，不做断言）。

## 状态
- status: built（配方实现完成，构建与上游测试由权威 CI 在鸿蒙 worker 上验证）
