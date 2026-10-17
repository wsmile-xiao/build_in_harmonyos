# pari-galpol

PARI/GP 的 **galpol** 数据包：GALPOL 数据库，定义有理数伽罗华扩张的多项式，
覆盖阶 ≤ 143 的全部 3657 个抽象群、共 7194 个多项式，供 GP 函数 `galoisgetpol`
读取。群按 GAP4 SmallGroups 库编号索引（数据来自 GAP4 / SMALL GROUPS LIBRARY，
属数据归属，不是依赖）。

- 上游主页: https://pari.math.u-bordeaux.fr/galpol
- 官方源:   https://pari.math.u-bordeaux.fr/pub/pari/packages/galpol.tgz
            （= https://pari.math.u-bordeaux.fr/galpol/releases/galpol-4.0.tar.gz，
              sha256 `562af28316ee335ee38c1172c2d5ecccb79f55c368fb9f2c6f40fc0f416bb01b`）
- 许可证:   GPL-2.0-or-later（© 2002-2018 The PARI Group）
- 性质:     **纯数据包**（Debian `Architecture: all`）——无编译、无 configure、
            包内无自动化测试；无任何强制第三方库依赖，仅被 PARI/GP
            （`Suggests: pari-gp`）在运行期消费。

## 版本

| 版本 | 说明 |
|------|------|
| 20180625 | 上游 GALPOL 4.0（发布日 2018-06-25；Debian 源包编码 `4.0`，上传记录 `4.0-1 -- Mon, 25 Jun 2018`） |

## 数据布局

```
res/pari/galpol/
├── README                       # 上游说明（含许可声明）
└── <order>/<index>/             # order = 1..143，index = 1..nb(order)
    ├── real                     #  totally real 伽罗华多项式  [Pol([...]),den]
    ├── complex                  #  非全实（仅部分群有，3537/3657）
    ├── group                    #  抽象群，galoischartable 可读格式
    ├── name                     #  GAP4 StructureDescription 名字串
    └── non-wss                  #  0 字节标记：该群非弱超可解（29 个）
```
共 14681 个文件（数据 28536355 字节），全部为 ASCII GP 文本，未压缩。

## 消费方式

包安装后数据位于 `<package_folder>/res/pari/galpol/`。GP 通过 `datadir` 定位：

```gp
default(datadir, "<package_folder>/res/pari");   \\ 或直接把 galpol/ 放进 gp 的 datadir
galoisgetpol(8, 1, 1)    \\ -> [x^8 - x^7 - 7*x^6 + 6*x^5 + 15*x^4 - 10*x^3 - 10*x^2 + 4*x + 1, 1]
```

配方在 `package_info()` 用 `cpp_info.resdirs=["res"]` 暴露数据根，并设置自定义属性
`pari:galpol_rel`；下游取数：
`os.path.join(self.dependencies["pari-galpol"].package_folder, "res", "pari", "galpol")`。

## 目录

- `manifest.yaml` / `commands.json` — 软件级元数据（数据包无二进制，`binary: false`）
- `20180625/conanfile.py`   — Conan 配方（数据安装，`package_id` 与 profile 无关）
- `20180625/conandata.yml`  — 官方源 URL + sha256 + 三方同一性证明
- `20180625/test_package/`  — 打包内容级校验（32 项）+ 上游测试声明 MANIFEST.yml
- `20180625/notes.md`       — 适配笔记（依赖核验、基线指纹、踩坑根因）
- `20180625/upstream-test-cases.txt` — 7337 条上游功能测试逐用例记录（随包入仓）
- `20180625/upstream-gp-sweep-generator.py` — 上述用例的生成器（枚举被测目录，可复跑）
- `20180625/reports/`       — 本地运行日志（conan create / W3 CI / 验证报告），被
                             仓库 `.gitignore` 排除，不属本 PR
