# jp2a 1.3.3 OpenHarmony PC 适配说明

## 软件信息

- 名称：jp2a
- 版本：1.3.3
- 上游：https://github.com/Talinx/jp2a
- 源码：https://github.com/Talinx/jp2a/releases/download/v1.3.3/jp2a-1.3.3.tar.bz2
- License：GPL-2.0-or-later

## 构建方式

jp2a 使用 autotools 构建。本适配启用 JPEG/WebP 本地文件转换能力，关闭网络 URL 下载和终端尺寸探测：

```bash
./configure --host=aarch64-linux-ohos --disable-silent-rules --disable-curl --disable-termlib --disable-doxygen-doc --disable-doxygen-html
make
make install
```

## 依赖

- libjpeg-turbo/3.2.0
- libwebp/1.6.0

## 平台适配

- 关闭 `--enable-curl`，避免引入尚未发布为 Conan 包的 curl 依赖；本包仍支持本地图片文件转换。
- 配置时显式传入 `--host=aarch64-linux-ohos`，避免 CI/HMDFS 环境在 configure 阶段尝试运行目标平台 conftest。
- 关闭 `--enable-termlib`，避免依赖 curses/termcap，只保留显式宽高参数和基础输出能力。
- 仓库当前没有可用的 libpng 依赖闭包和 libexif Conan 包；构建时移除 PNG 解码路径，并将 EXIF 方向读取函数替换为默认方向，避免链接未发布依赖。

## 验证

已添加 test_package，执行：

- `jp2a --version`
- `jp2a --help`

完整验证命令：

```bash
python3 -m py_compile archives/j/jp2a/1.3.3/conanfile.py archives/j/jp2a/1.3.3/test_package/conanfile.py
git diff --check -- archives/j/jp2a
bash ci/scripts/preflight_check.sh jp2a/1.3.3
conan create archives/j/jp2a/1.3.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
