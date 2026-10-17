# simple-tiles

Image generation library for spatial data（将矢量/栅格空间数据渲染为地图瓦片）。

- **Homepage**: https://github.com/propublica/simple-tiles
- **License**: MIT

## 版本

| 版本 | 说明 |
|------|------|
| 0.6.2 | 上游稳定版；构建方式参考 Homebrew formula |

## 依赖

- cairo
- pango（pangocairo）
- gdal
- glib / harfbuzz（经 pango）

详见 `0.6.2/notes.md`。

## 构建

```bash
cd archives/s/simple-tiles/0.6.2
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
