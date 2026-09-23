# libm17n-core 1.8.6 — 鸿蒙 PC conan 制品

上游：GNU m17n-lib 1.8.6（多语言文本处理库，M-text），<https://www.nongnu.org/m17n/>。
`os=OHOS, arch=armv8`（= aarch64）的 conan 包，交付非 GUI 库集合：

| 产物 | 说明 |
|---|---|
| `lib/libm17n-core.so.0.4.2` | 核心库（任务交付物）：MSymbol / MPlist / MCharTable / MText / 数据库与断行 |
| `lib/libm17n.so.0.4.2` | shell 层 API（charset / coding / input / language / locale），依赖 core |
| `lib/libm17n-flt.so.0.4.2` | FLT（字体布局表）层，依赖 core |
| `include/{m17n-core.h,m17n-misc.h,m17n.h,m17n-flt.h}` | 公开头文件 |
| `lib/pkgconfig/{m17n-core,m17n-shell,m17n-flt}.pc` | pkg-config 元数据 |

依赖：`libxml2/2.15.3.1`（m17n 数据库为 XML 格式，核心库必需）。
不含 GUI 层（`libm17n-gui` 等需 X11/freetype/fontconfig，OHOS 不具备），
不含上游示例程序与 libtool `.la`。

## 出包（鸿蒙 PC CI）

```bash
conan create . -pr:h=<ohos-aarch64 profile> -pr:b=<同一 profile>
```

> CI 为设备原生构建：`-pr:h` 与 `-pr:b` 均为 `ci/conan/profiles/ohos-aarch64`。
> 源码由 `conandata.yml` 的官方 URL 下载并校验 sha256。

## 消费

```bash
# conan 工程（CMake / pkg-config 两种消费方式均可）
conan install --requires=libm17n-core/1.8.6 -pr:h=<ohos-aarch64 profile>
# CMake:  find_package(libm17n-core) -> libm17n-core::libm17n-core
# pkg-config: pkg-config --cflags --libs m17n-core  (运行期需 libxml2 的 lib 目录在 LD_LIBRARY_PATH)

# 裸程序（部署到 ~/usr/local 后用 dlopen/直接链接）
conan install --requires=libm17n-core/1.8.6 -pr:h=<ohos-aarch64 profile> \
    --deployer-folder=$HOME/usr/local
```

核心 API 不依赖 m17n 数据库；编解码、语言、输入法等完整功能需要另行部署
`m17n-db` 数据包（`M17NDIR`，默认 `<prefix>/share/m17n`）。

## 适配要点

详见同目录 `notes.md`：`--disable-nls` 去掉 libintl（规避设备 `libintl.so.8.proxy`
的 `g_libintl_*` 改名）、绕过制品包中 prefix 写错的 `xml2-config` 以启用 XML 后端、
预置 `ac_cv_func_malloc/realloc_0_nonnull` 规避交叉编译下的 `rpl_malloc` 假阳性、
GUI 产物剔除，并附带两个只做平台可移植性修复的上游补丁：
`patches/0001-config.guess-harmonyos.patch`（config.guess 增加 HarmonyOS 分支，输出
`<machine>-unknown-linux-ohos`，否则设备原生 configure 会因 dummy.c 探测被拒而报
`cannot guess build type`）与 `patches/0002-configure-umask-hmdfs.patch`
（configure 辅助临时目录 umask 077→022，否则 HMDFS 上
`confXXXXXX/subs1.awk: Permission denied` 导致 config.status 失败）。
