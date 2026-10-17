# swe-data 4.0-20221111 适配记录

## 上游与交付契约

- **上游**：Swiss Ephemeris（Astrodienst AG）静态数据文件集；平台任务名 `swe-data`、
  版本 `4.0-20221111`，对应 Debian 源包 `swe-data` 的
  `swe-data_4.0-20221111.orig.tar.gz`（sha256 `4efb50197…68369bc`，走清华 TUNA 镜像，
  与 deb.debian.org 同一份文件）。源码是**纯数据**：没有代码、没有编译步骤。
- **交付布局**（与 Debian 二进制包 `swe-basic/standard/extra/sat-data` 合并安装后完全同形）：
  - `share/libswe/ephe/*.se1`、`share/libswe/ephe/*.txt` —— 150 个星历文件 + 6 个文本表
  - `share/libswe/ephe/sat/sepm*.se1` —— 32 个行星卫星/行星本体中心文件
  - `licenses/LICENSE` + `share/doc/swe-data/{copyright,README}`
- **消费方式**：`libswe`/`swetest` 通过 `swe_set_ephe_path()` 或 `SE_EPHE_PATH` 环境变量
  找数据目录；`package_info()` 用 `cpp_info.resdirs` 发布 `share/libswe/ephe`，
  并把 `SE_EPHE_PATH` 注入 Conan 运行环境（`runenv_info`）。纯数据包无编译、
  无库、无头文件，默认 `libs/bin/include/lib` 目录已清空以免 CMakeDeps 生成幻影路径。

## 载荷指纹（build() 中强校验）

| 项 | 值 |
|---|---|
| 文件数 | 188（182 个 `*.se1` + 6 个文本表） |
| `*.se1` | basic 3 + standard 51 + extra 96 + sat 32 = 182 |
| 总字节 | 314 404 679 |
| 清单摘要 | sha256(`<name> <size>\n` 排序清单) = `0a4fcc50…f4938f` |

## 文件命名与时间覆盖（从各文件头部实测）

- `sepl_NN.se1` / `semo_` / `seas_`：覆盖 `NN*100 年 .. +600 年`；
  `seplmNN.se1` 等（`m` 系）：覆盖 `-NN*100 .. -NN*100+600` 年。
- 实测整集覆盖 **公元前 13000 年 ~ 公元 16800 年**，600 年一档、相邻文件重叠、无缝隙：
  basic 目录 1800–2399 CE（与 Debian 承诺一致）、standard 起止 5401 BCE–5399 CE
  （与 Debian 承诺一致）、extra 到 16800 CE（与 Debian 承诺一致）。
  注意：`seplm/seasm/semom` 只到 **132**（公元前 13000 年），没有 138..162 的文件，
  因此公元前侧的实际下限是约 -12999 年（Debian 对 swe-extra-data 写的
  "13000 BCE" 正是这个上限，而"16200 BCE"并不存在——不要照抄文件编号推断）。
- 上游 `*132` 一组的头部窗口相对文件名整体偏移约 **201 年**
  （`seplm132` 实际是 [-12999, -12400] 而不是 [-13200, -12600]，semom/seasm 同样），
  与相邻的 126 组重叠 200 年，因此覆盖仍然连续；该偏移已在自检中按 300 年容差记录。
- `sepm<P><MM>.se1`：`<P>` 为母行星代码（94 火星 / 95 木星 / 96 土星 / 97 天王星 /
  98 海王星 / 99 冥王星），`MM`=01..08 卫星号，`99` 表示"行星本体中心（COB）"。

## 消费者用例（平台 rule12）

`test_package/consumer_ephe.py` 不是断言集合，而是把 `.se1` 格式按 libswe 2.10.03
`sweph.c` 的 `read_const()` / `get_new_segment()` / `rot_back()` / `swi_echeb()` 逐段移植：

1. 头部解析（3 行文本，行星卫星文件为 4 行 + 30 字节名称域；用 **CRC 必须匹配**判定
   布局，因此头部解析自校验）+ 声明长度 == 实际长度 + DE 编号 + 行星表；
2. 段读取：`iseg = (tjd - tfstart)/dseg` → 3 字节文件偏移 → 解包 4/3/2/1 字节与
   半/四分之一字节打包系数（含 `rmax` 归一化，卫星/COB 文件另有 1e6 量级）；
3. `rot_back`：等分点变量旋转 + （月球）参考椭圆与 J2000 赤道面转换；
4. `swi_echeb` 求值 → J2000 赤道直角坐标矢量；
5. 行星日心化：带 `SEI_FLG_HELIO` 的记录即为日心；不带的（质心记录）加
   `barycentric_sun = barycentric_earth - heliocentric_earth`（同一 `sepl` 文件内的
   0 号与 10 号槽位——正是 sweph.c 注释里给出的用法）；月球记录为地心。

**逐项比对上游参考实现**（libswe 2.10.03 `swetest -j2000 -true`，配本数据包）：
11 个历元 × 8 行星日心距 + 月球地心距（容差 1e-6 AU，实测最大偏差 ~1e-7 AU）、
J2000.0 位置矢量组件级比对、主小行星 6 槽位 3 个历元、32 个行星卫星
到中心体距离 vs JPL 文档半长轴（实测比值 0.891~1.027，Nereid 因 e=0.75 单列宽带）、
文本表（闰秒表、小行星编号表 616690 条、恒星表 1347 条 ICRS 记录、虚拟行星轨道根数）。
实测 **172/172 通过**。

## 实测到的、对使用方有价值的事实

1. **`seas_*.se1` 的槽位顺序**是 Chiron/Pholus/Ceres/Pallas/Juno/Vesta，而文件内
   `ipl` 表写的是生成器内部编号 **12..17**（与 libswe 的 `SE_CHIRON..SE_VESTA`
   15..20 相差 3）；libswe 按**位置**取用。消费者用例按位置比对，与 `swetest`
   的 `-pD/-pE/-pF/-pG/-pH/-pI` 完全一致（≤2e-6 AU）。
2. **行星卫星记录是"相对母行星系统质心"的**：冥卫一 Charon 实测 17464 km 而文档
   半长轴 19591 km，比值 0.891 恰为冥王星系统质心因子（M_Pluto/(M_Pluto+M_Charon)
   ≈ 0.889）；`…99.se1` 文件则是行星本体中心相对系统质心的偏移（实测 32~2135 km）。
3. `swetest` 对主小行星另有**自身上限**限制（Chiron 报
   `restricted to JD 1967601.5 - JD 3419437.5`），因此小行星比对只取 1000/2000/3000 CE
   三个历元；其余（含公元前 `seasm*`）走结构 + CRC + 段求值校验。
4. `.se1` 内嵌的 CRC 是 **CRC-32/BZIP2**（多项式 0x04C11DB7、非反射），不是 zlib 的
   IEEE CRC-32；用 zlib 校验会全表失败。
5. 上游 `.orig.tar.gz` 里的 `Makefile` / `README.txt` 是指向 Debian 打包目录的**落链**
   符号链接（目标不在 tarball 内），没有载荷，因此不入包。

## 本地验证

- `python3 scripts/ohc-run.py conan-verify swe-data 4.0-20221111` → Verdict PASS
  （消费者用例 172/172 + 适配自检 16/16）
- `python3 scripts/ohc/preflight.py . main HEAD` → 全部通过
