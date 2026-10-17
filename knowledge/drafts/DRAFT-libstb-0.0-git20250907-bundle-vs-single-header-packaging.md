# 合集包与单头包并存：libstb 打包口径（草稿）

- **来源**：libstb 0.0-git20250907.fede005（nothings/stb @ fede005）适配，
  本机 conan create 打包内容复核（多出 1 个 .h）
- **日期**：2026-09-15
- **证据**：`archives/l/libstb/0.0-git20250907.fede005/conanfile.py`（STB_FILES
  清单）、conan create 打包日志、本仓 archives/s/stb_image/2.30/conandata.yml

## 坑 1：copy() 通配符跨目录误打包

`copy("stb_*.h", src=源码根)` 首轮打出 **21** 个 .h——比根目录实有的 20 个多 1。
多出的是 `stb_image_resize_test/old_image_resize.h`：conan 的 pattern 走
fnmatch 对相对全路径匹配，fnmatch 的 `*` **可跨 `/`**（与 glob 不同），根目录
模式把子目录文件一并匹配并在包内保留层级。本机实测即被此坑污染
（锚定语义详见 DRAFT-ohos-conan-copy-fnmatch-anchored）。

**修法**：配方维护显式安装清单，逐文件 copy。清单即文档，天然排除
`deprecated/` 与 `tests/` 辅助文件。打包后核对 create 日志
`Packaged N '.h' files` 计数 = 清单长度。

## 坑 2：合集包 vs 单头包，防"重复适配"误判

本仓已有 stb_image/2.30、stb_ds/0.67、stb_sprintf、stb_image_write、
stb_image_resize 五个单头包，与 libstb 同属 nothings/stb。**libstb 不是重复
适配**：单头包每包只装一个头，libstb 是合集包（Alpine 打包口径：一次装全
20 个 `stb_*.h` + `stb_vorbis.c`），面向"一把全拿"的消费者。

**互证手法**：libstb 与 stb_image/2.30 用同一上游 commit fede005，
`conandata.yml` 的 sha256 完全一致（`3c45e9ab...8a42`）——既互相印证源码
完整性，又是 PR 里说明"非重复适配"的现成证据。反向提醒：适配前先查
`grep -rn "上游URL" --include=conandata.yml archives/`，同源已发布时先
弄清"同包重复"还是"同源不同粒度"再动手。

## 打包口径（libstb 实测）

- 装根目录全部 20 个 `stb_*.h` + **`stb_vorbis.c` 照装**（vorbis 的实现文件，
  官方用法就是 `#include "stb_vorbis.c"` 一次）
- **`deprecated/` 不装**（上游已弃用；旧 `stb_image_resize.h` 已由根目录
  `stb_image_resize2.h` 取代）
- `package_type="header-library"`、`package_id()` 清空、`bindirs/libdirs=[]`、
  cmake 目标 `libstb::libstb`

## 验证

本机 conan create（-tf=""）与真机（OHOS aarch64）conan create 双端复核：
包内容恰为 20 .h + stb_vorbis.c + LICENSE，无任何子目录。
