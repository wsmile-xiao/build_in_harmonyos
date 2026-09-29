# ldraw-parts-free 2602 适配笔记

## 上游与来源

- LDraw 零件库（LDraw Parts Library）：LDraw.org 官方 LEGO 风格 CAD 零件库，
  纯文本 `.dat` 几何文件 + PNG 贴图纹理 + LDR 颜色配置，无任何编译产物。
  2602 = 2026-02 官方更新（LDConfig 配置更新标记 2026-01-03）。
- 官方发行 complete.zip 为**滚动 URL**（`library.ldraw.org/updates?latest`），
  无固定 sha256。且库内约 3200 个零件/子零件及 4 个样例模型（car/pyramid）
  仍为 **CC-BY-2.0-only 或双许可（DFSG 非自由）**，不可整体进 Debian main。
  Debian 因此以独立源码包 **ldraw-parts-free 2602+dfsg-1** 重打包（与
  ldraw-parts 2602+ds 的完整库并列）：repack.sh 提取 mklist 工具源码后，
  `gendfsgsrc.py` 按「首个 `0 !LICENSE` 生效行精确匹配 CC BY 4.0」+
  「依赖图祖先剔除」过滤出自由子集。本配方以该 dfsg orig.tar.xz 为钉死
  归档（Debian main 池，USTC 主 + aliyun 备，sha256=2011f947… 实测，
  与 2602+dfsg-1.dsc 记录一致）。

## 2602+dfsg 发行清单（实测计数）

| 目录 | 内容 | 计数 | 完整库对照 |
|------|------|------|-----------|
| `parts/` | 平铺零件 .dat（CC-BY-4.0-only，含印刷件 3001p01 等） | 21186 | 23839（剔 2653） |
| `parts/s/` | 子零件 | 8267 | 8813（剔 546） |
| `p/` | 标准图元 | 1741 | 1743（剔 2） |
| `p/8/` | 低分辨率图元 | 127 | 127（一致） |
| `p/48/` | 高分辨率图元 | 920 | 920（一致） |
| `models/` | 更新记录 .txt | 135 | 139（car/pyramid 样例模型被剔） |
| `parts/textures/` | PNG 贴图 | **0（整类不携带）** | 135 |
| 根目录 | Readme + LDConfig 三件 + CA 协议三件 | 7 | 7 |
| mklist 源 | mklist.c + include/*.h（repack 附带） | 4 | 完整库无 |
| **合计** | | **32387**（其中 .dat 32241） | 35723 |

## 自由子集三不变量（独立 Python 全树扫描实证）

1. **许可不变量**：全部 32241 个 .dat 的生效许可行（首个 `0 !LICENSE`
   行）均为精确行 `0 !LICENSE Licensed under CC BY 4.0 : see CAreadme.txt`。
   被注释的历史旧许可行（如 `0 // !LICENSE Redistributable under CCAL
   version 2.0 : see CAreadme.txt`，973pxis01.dat 第 145 行实证）不参与
   判定——与 gendfsgsrc.py 语义一致（它只匹配生效许可行）。
2. **引用自包含**：32241 个 .dat 中 368173 个 type-1 引用（第 15 token）
   全部在库内解析成功（候选集：引用名 / 引用文件所在目录 / `p/` /
   `parts/`），0 缺失——依赖图祖先剔除的推论。
3. **被剔著名件负向锚点**：2412b.dat（Tile 1x2 Grille）、10048.dat
   （Minifig Hair Tousled）、10928.dat（Technic Gear 8 Tooth）、
   models/car.dat、models/pyramid.dat、parts/textures/ 均不得存在。

## 许可证

- 主体：**CC-BY-4.0**（每个 .dat 生效许可行精确一致——这就是 free 子集
  的定义性质；LDraw.org 2012-2026 再授权）。
- 两版法律文本（`CAlicense.txt` = CC BY 2.0 承继文本、`CAlicense4.txt`
  = CC BY 4.0）+ `CAreadme.txt` 再分发协议随包携带并复制到 `licenses/`。
- conan `license` 字段：CC-BY-4.0。

## OHOS 适配

纯数据包，无编译无链接（kicad-demos / ldraw-parts 范式）：

- `build()` 仅做防漂移清单校验：7 根文件在位 + mklist.c/include 随档 +
  6 个目录精确计数 + textures 整类/car/pyramid 负向断言 + 全树 32387
  文件总数断言（排除 conan 生成的 `.sh`/conaninfo.txt）；
- `package()` 整树 `copy("*")` + excludes pattern 列表（`*.sh` /
  conaninfo.txt / mklist.c / include/*）→ `share/ldraw/`，CA 三件另存
  `licenses/`。真机坑：conan 2 目录级 `copy(self, "<目录>", ...)` 是
  空操作（2.29.1 实证包目录只剩根文件），必须文件匹配式整树复制；
  excludes 必须是列表，逗号串整体会当作单个 fnmatch pattern 不生效。
- `package_id` 清空（数据包与 settings 无关）；
- `cpp_info.resdirs` 暴露 `share/ldraw`，`runenv_info` 定义 `LDRAWDIR`
  （LeoCAD/LDView 等 LDraw 消费工具的库定位环境变量）。
- 布局与 Debian 惯例一致：`/usr/share/ldraw/{parts,models,p,LDConfig*.ldr}`
  （Debian rules `execute_after_dh_auto_install` 实证安装清单）；本包额外
  保留 Readme 与 CA 协议三件（官方发行原样）。

## 测试口径

上游为 DFSG 纯数据发行，无测试套件（gendfsgsrc.py/repack.sh 为 Debian
打包工具，非上游测试）。适配后消费者测试执行器
（`test_package/ldraw_parts_free_probe.cpp`，逐例 TEST PASS/FAIL +
TEST SUMMARY + 失败退出码 1）7 个测试用例：

1. 32383 包内清单精确计数（7 根文件 + 6 目录分项 + textures/mklist/
   include 负向 + 递归总数 + 包级 licenses/ 布局）；
2. 代表性内容锚点：3001.dat（2x4 砖，Jessiman 原作）/ 2-4edge.dat /
   p48 `48\1-4cyli.dat` / `s\3001s01.dat` / 3001p01.dat（印刷件）/
   Note2602CA.txt + 被剔著名件负向锚点（2412b/10048/10928/car/pyramid）；
3. **全树 32241 个 .dat 单遍全读**：格式（首行 `0 ` + `0 Name:` 行）+
   生效许可行精确 CC-BY-4.0 校验（历史注释旧许可行不误报），同一遍
   收集 type-1 引用；
4. 368173 个引用全部在库内解析成功（0 缺失）；
5. LDConfig.ldr `0 !COLOUR` 322 条目 + 2602 配置更新标记 + CC 许可证
   双文本 + CAreadme 再分发协议；
6. 截断/坏头/CCAL 许可注入负向用例（写入→校验拒绝→清理，证明执行器
   真实读写包目录）；
7. **消费者端到端：最小 LDraw 渲染管线**——载入 LDConfig 颜色表 →
   解析 3001 装配体 → type-1 引用递归解析至子件与 p/ 图元 → 图元
   几何（2/3/4/5 型行）载入 → 几何颜色索引对照 LDConfig。与
   LeoCAD/LDView 消费本库的最小功能流同构（审查规则要求消费者端到端
   用例，静态检查再多不算跑通功能）。实测装配图 10 文件 / 25 引用 /
   线段 40 / 三角 16 / 四边形 46 / 可选线 16。

本机 MinGW 预测试：`TEST SUMMARY: 7 passed, 0 failed`
（按 package() 布局 1:1 模拟包）。

## 真机验证（鸿蒙侧，2026-09-28）

`python3 scripts/ohc-run.py conan-verify ldraw-parts-free 2602`
（华为 PC 真机，Conan 2.29.1 + ohos-aarch64 profile）：
**八道门禁全过**，判定「配方验证通过，可标记 status: published」。

- G0 ✅（构建系统 unknown，跳过预查询）
- G1 ✅ 配方完整性（name/version/source/build/package/package_info/
  export_sources/补丁应用调用/conandata/test_package/MANIFEST 全项）
- G2 ✅ conan create 干净构建（真机实跑，含 test_package 探针；55.1MB
  dfsg 归档从 USTC 镜像实测下载成功，包 ID da39a3ee…afd80709）
- G3 ✅ 无 bin//lib/ 目录，无系统同名库冲突（R26 通过）
- G4 ✅ 产物完整性（package_id 清空 → 空包 ID，verify 提示「无法找到
  程序包 ID」属预期）
- L2/L4/L5 ✅（纯数据包无 cache 路径，跳过）
- 执行器真机输出：7 用例全部 TEST PASS，`TEST SUMMARY: 7 passed,
  0 failed`（含消费者渲染管线端到端：装配图 10 文件 / 25 引用 /
  三角 16 + 四边形 46，逐项见 reports/conan-create.log）

产物实测：`share/ldraw/` 精确 32383 文件（parts 21186 + s 8267 +
p 1741/127/920 + models 135 + 根 7），`licenses/` 3 文件（CAlicense
双版本 + CAreadme），mklist.c/include 不携带，无多余文件混入。

两轮真机失败实录（均已修复并第三轮复验全绿）：

1. **strip_root 失效**：dpkg-source 生成的 dfsg orig 条目带 `./` 前缀
   （`./ldraw-parts-free-2602/...`），conan `get(strip_root=True)` 的
   commonpath 顶层判定遇 `./` 不剥离 → build() 报 inventory drift
   missing files。修复：`get()` 原样解压 + `_src_root()` 按固定顶层
   目录名显式下钻，不依赖 strip 语义。
2. **目录级 copy 空操作**：conan 2 目录级 `copy(self, "<目录>", ...)`
   是空操作 → 包目录 `share/ldraw/` 只剩 7 根文件，探针目录计数全挂。
   修复：整树 `copy("*")` + excludes pattern 列表（`*.sh`/conaninfo/
   mklist.c/include/*，同 ldraw-parts 先例范式）。

第四轮（同日晚，审查口径整改复验）：test_package 由 6 组检查项重构为
消费者测试执行器（逐例 TEST PASS/FAIL + TEST SUMMARY + 失败退出码 1）
并新增消费者端到端用例（最小 LDraw 渲染管线，与 LeoCAD/LDView 消费流
同构），八门禁复验全绿（G0-G4 PASS，L2/L4/L5 跳过），报告已回填
reports/。

## 参考

- LDraw.org 库: https://library.ldraw.org/
- Debian ldraw-parts-free: https://salsa.debian.org/debian/ldraw-parts-free
- Debian 池（USTC 镜像）: https://mirrors.ustc.edu.cn/debian/pool/main/l/ldraw-parts-free/
- 姊妹包 ldraw-parts 2602（完整库，已合入官方 main，路径 A）
