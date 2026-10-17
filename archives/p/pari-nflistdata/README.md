# pari-nflistdata

PARI/GP 的 **nflistdata** 数据包：按指定伽罗华群列出数域的数据库，供 GP 函数
`nflist` 读取。上游 README 自述 *"This is the nflistdata package for PARI/GP, to be
used by the 'nflist' function"*。内容三类：

- **A5 数域表**（度 5，群 5T4 = A5；亦服务 6T4 = A5(6)）
  * Jones & Roberts 表（<https://hobbes.la.asu.edu/NFDB/>）：r2=0 完备到
    `disc ≤ 524286^2 ≈ 2.7*10^11`，r2=2 完备到 `disc ≤ 10^8`；
  * Allombert & Page 表：按"具有对应二十面体投影像的 2 维 Artin 表示的极小
    conductor"排序，两种签名均完备到 conductor 10^6。
- **Q(T) 上正则扩张表**：Klüners–Malle（见 Malle–Matzat, *Inverse Galois Theory*,
  Springer 1999）与 Dokchitser 的计算，覆盖 n ≤ 15 的大部分传递子群，
  由 `nflist(G, 't)` 读取（度 8 及以上）。

- 上游主页: https://pari.math.u-bordeaux.fr/packages.html#nflistdata
- 官方源:   https://pari.math.u-bordeaux.fr/pub/pari/packages/nflistdata.tgz
            （sha256 `2c19a3e02afd3bba2af3071a7faa80924a75b00bb9713286c886b7fb460944bc`，
            3623252 B，Last-Modified 2022-07-29 —— 与 Debian
            `pari-nflistdata_0.20220729-2.orig.tar.gz` 字节同一）
- 许可证:   GPL-2.0-or-later（© 2022 The PARI Group, Bordeaux）
- 上游要求: **PARI/GP 2.14.0 及以上**（官方包页原文 "Require PARI/GP 2.14.0."）
- 性质:     **纯数据包**（Debian `Architecture: all`）——无编译、无 configure、
            包内无自动化测试；无任何强制第三方库依赖，仅被 PARI/GP
            （`Suggests: pari-gp`）在运行期消费。

## 版本

| 版本 | 说明 |
|------|------|
| 20220729 | 上游发布日 2022-07-29（Debian 源包编码 `0.20220729`，`0.20220729-1 -- Sat, 30 Jul 2022`）；与同族 pari-galpol/20180625、pari-seadate-big/20170418 的日期式版本口径一致 |

## 数据布局（打包产物）

```
res/pari/nflistdata/
├── README                       # 上游说明（含完备性边界与 GPL 声明）
├── <degree>/<index>/QT          # 650 个正则扩张表，单行 GP list 字面量
│                                 #   度分布 2:1 3:2 4:5 5:5 6:16 7:7 8:50 9:34
│                                 #       10:45 11:8 12:301 13:9 14:63 15:104
└── 5/4/...                      # 27 个 A5 分片
    ├── 0/0 … 0/5                #   Jones–Roberts, r2=0，末片以 [0,0] 哨兵结尾
    ├── 0cond/0 … 0cond/9        #   Allombert–Page, r2=0（按 conductor 排序）
    ├── 2/0                      #   Jones–Roberts, r2=2，末行 [0,0] 哨兵
    └── 2cond/0 … 2cond/9        #   Allombert–Page, r2=2
```

上游 678 个文件 / 8845045 字节**按原层级、未压缩**安装（Debian 那步
`gzip --no-name --best` 未沿用：PARI 可直读未压缩表，省掉构建期 gzip 依赖）。

## 依赖

| 层级 | 内容 |
|------|------|
| conan requires | **无**（纯数据包，与同族 pari-galdata / pari-galpol / pari-seadata 一致） |
| Debian 运行期 | `Depends: ${misc:Depends}`（解析为空）、`Suggests: pari-gp` |
| Debian 构建期 | `Build-Depends: debhelper-compat (= 13)`（仅 Debian 打包，conan 路线不需要） |
| 运行期消费者 | `pari/2.17.4.1`（提供 `gp` 的 `nflist`；本包适配期用它实跑上游测试）。pari 自身的依赖链为 gmp/6.3.0.1 ← readline/8.3 → ncurses/6.6，均已在制品仓可消费 |

## 下游接线

gp 通过 `default(datadir, …)` 定位数据（libpari 内路径模板实证为
`%s/nflistdata/%ld/%ld/QT`）。使用本包时把 datadir 指到本包 `res/pari`：

```gp
default(datadir, "<pari-nflistdata 包目录>/res/pari");
nflist("A5")                 /* A5 (5T4) 数域 */
nflist([8,1], 't)            /* 8T1 在 Q(T) 上的正则扩张 */
```

## 验证

- 上游功能入口实跑：685 项断言（650 QT round-trip + 8 A5 语义 + 27 A5 分文件归因），
  665 PASS / 0 FAIL / 20 SKIP（SKIP 为 conductor 排序表在 pari/2.17.4.1 下无 gp 可见
  入口，见 `20220729/test_package/MANIFEST.yml` 的 skip_explanation）；
  逐用例记录：`20220729/upstream-test-cases.txt`。
- 打包内容级校验（test_package）：81 项字节/结构/语法断言，含整体与 6 个分类的
  拼接 sha256、14 个单文件 sha256、JR 表哨兵边界值；故障注入实测可拦截。
