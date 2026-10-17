# iso-flags-svg 1.0.4 适配笔记

## 概述

把 Linux Mint 的 ISO 3166-1 国家/地区旗帜 SVG 集合适配为 HarmonyOS PC 的
Conan 纯数据包。它是"按两位国家代码取旗帜图标"这类 UI 需求（地区选择器、
语言/国家下拉、IP 归属地展示）的公共数据源。

## 上游形态

上游 `iso-country-flags-svg-collection` 是资源仓库，没有 tag；Debian 的版本号
沿用的是姊妹仓库 `linuxmint/flags` 的 v1.0.4，orig tarball 由 Debian 从
`iso-country-flags-svg-collection` 的对应 commit 手工打出。因此本包采用
**Debian 的 orig tarball** 作为可被 sha256 固定的分发形态。

```
iso-flags-svg/
├── iso-3166-1.csv        248 条索引（Code,Country name,Year,ccTLD,ISO 3166-2,Notes）
├── iso-3166-1.json       同索引的 JSON 形态（{"Results": {…}}，249 个键）
├── svg/country-4x3/      262 个 SVG（260×640x480 + 2×600x400）
├── svg/country-squared/  253 个 SVG（252×512x512 + 1×512x600）
├── build/ examples/ scripts/ Makefile README.md
```

## 安装内容

```
share/iso-flags-svg/country-4x3/*.svg        262 个
share/iso-flags-svg/country-squared/*.svg    253 个
share/iso-flags-svg/iso-3166-1.csv
share/iso-flags-svg/iso-3166-1.json
licenses/COPYRIGHT.txt
```

文件名即小写的 alpha-2 代码：`share/iso-flags-svg/country-4x3/cn.svg` = 中国。
消费方通过 `ISO_FLAGS_SVG_DIR`（buildenv/runenv）或 `cpp_info.resdirs` 定位。
Debian 只安装 `svg/`，本包额外带上 csv/json 索引 —— 索引让包自描述，
也让"索引 ↔ 资源"的一致性可以被测试用例断言（见下）。

## 为什么没有编译步骤

上游是纯资源仓库，`build/` 与 `scripts/` 只是生成其它格式（PNG、方形变体）
的辅助脚本，本包直接交付现成的 SVG。因此配方：

- `package_type = "unknown"`，不声明 `settings`（纯数据包，产物与架构无关）；
- `build()` 只做数据完整性自检，不调用任何编译器/构建系统；
- 不创建 `commands.json`、不伪造二进制测试（E255 的 forbid_1）。

## 上游测试情况

上游没有测试目录、测试框架或 CI 测试阶段；Debian 侧也没有 autopkgtest。
**上游用例数 N = 0。**

## 新增自检（test_package/test_iso_flags.py，36 条断言）

| 断言组 | 条数 | 内容 |
|--------|------|------|
| 文件齐备 | 3 | `share/iso-flags-svg` 目录 + csv + json 存在 |
| csv 索引规范 | 5 | 六列表头；248 行；代码均为两位大写字母；无重复；无被逗号截断的行 |
| json ↔ csv 一致性 | 5 | 顶层含 `Results`；键数 249；键集合 = csv 代码集合 + `EU`；`CN` 的 Name 为 China |
| 旗帜目录（每套 6 条） | 12 | 目录存在；只含 `.svg`；数量 262/253；覆盖全部 248 个代码；非国家富余条目与上游完全一致；无空壳文件 |
| SVG 本体（每套 2 条） | 4 | 全部解析为合法 XML、根元素为 `svg`；根元素尺寸分布与上游一致（`{640x480:260, 600x400:2}` / `{512x512:252, 512x600:1}`） |
| 真实条目抽查 | 3 | `country-4x3/cn.svg` 存在；根元素 640x480；带 `viewBox` |
| 安装纯净性 | 2 | 安装目录只有索引与两套旗帜（无 `Makefile`/`scripts`/`build`/`examples`）；`licenses/COPYRIGHT.txt` 已发布 |

最有价值的两组：

1. **索引 ↔ 资源一致性**：248 个 alpha-2 代码逐一双向核对，两套目录都不得缺项。
   少一面旗 = 下游按代码取图必然失败，而"文件存在"类断言发现不了。
2. **非国家富余条目与上游逐字一致**：上游在两套目录里各带了不同的额外旗帜
   （`country-4x3` 有苏格兰、威尔士、加泰罗尼亚等 14 个；`country-squared`
   只有 5 个）。把这份清单固化成断言，可以识别"换了一份上游 tarball"
   或"目录被裁剪过"。

## 关于长宽比

目录名 `country-4x3` / `country-squared` 是约定而非强制：实测 `country-4x3`
里有 2 个 600x400（3:2）的例外，`country-squared` 里有 1 个 512x600 的例外。
因此测试断言的是**尺寸分布**（逐套的 `{宽x高: 数量}` 映射），而不是
"所有文件都是 4:3"——后者在本数据上并不成立。

## 构建与验证

```bash
conan create archives/i/iso-flags-svg/1.0.4 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
python3 scripts/ohc-run.py conan-verify iso-flags-svg 1.0.4
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/i/iso-flags-svg/iso-flags-svg_1.0.4.orig.tar.gz`
  （官方路径 `https://deb.debian.org/debian/pool/main/i/iso-flags-svg/iso-flags-svg_1.0.4.orig.tar.gz`）
- SHA256: `7a95f0fcb143d059fa5c500c02c8956caa0e3ad4d6055ca0e218688996ced819`
  （与 `iso-flags-svg_1.0.4-1.dsc` 的 `Checksums-Sha256` 一致）
- License: public-domain（上游 orig tarball 无 LICENSE，随包附带 `COPYRIGHT.txt`
  记录 Debian `debian/copyright` 中的公有领域声明）

---

**编译结束**: 2026-09-19
**最终状态**: built
