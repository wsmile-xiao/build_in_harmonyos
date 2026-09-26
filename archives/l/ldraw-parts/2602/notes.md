# ldraw-parts 2602 适配笔记

## 上游与来源

- LDraw 零件库（LDraw Parts Library）：LDraw.org 官方 LEGO 风格 CAD 零件库，
  纯文本 `.dat` 几何文件 + PNG 贴图纹理 + LDR 颜色配置，无任何编译产物。
  2602 = 2026-02 官方更新（LDConfig 配置更新标记 2026-01-03）。
- 官方发行 complete.zip 为**滚动 URL**（`library.ldraw.org/updates?latest`，
  随每次更新覆写），无固定 sha256，不可作为 conan 源钉死。本配方以 Debian
  `ldraw-parts 2602+ds-1` 重打包 orig.tar.xz 为钉死归档（Ubuntu multiverse
  池，USTC/aliyun 镜像，sha256=192284b4… 实测，与 2602+ds-1.dsc 记录一致）。
- **+ds 口径**（`debian/watch` + `debian/copyright` Files-Excluded 实证）：
  重打包 = 官方 complete.zip 仅剔除 4 个 mklist 工具文件（`mklist.exe` /
  `mklist1_4.zip` / `mklist1_6.zip` / `mklist-c.zip`），其余内容与官方
  complete.zip 逐字节一致。原包内无 `parts.lst`（官方 complete.zip 本身
  不含；Debian 打包期以 ldraw-mklist 生成，本包按官方发行原样不带）。

## 2602 发行清单（实测计数）

| 目录 | 内容 | 计数 |
|------|------|------|
| `parts/` | 平铺零件 .dat（含印刷件 3001p01 等） | 23839 |
| `parts/s/` | 子零件 | 8813 |
| `parts/textures/` | PNG 贴图纹理 | 135 |
| `p/` | 标准图元 | 1743 |
| `p/8/` | 低分辨率图元 | 127 |
| `p/48/` | 高分辨率图元 | 920 |
| `models/` | 更新记录 + 样例模型 | 139（135 txt + car/pyramid 各 dat+ldr） |
| 根目录 | Readme + LDConfig 三件 + CA 协议三件 | 7 |
| **合计** | | **35723**（其中 .dat 35444） |

## 许可证

- 主体：**CC-BY-4.0**（LDraw.org 2012-2026，Debian copyright `Files: *`）。
- CA 文件承继 **CC-BY-2.0**（部分文件为 CC-BY-2.0 原始许可 + CC-BY-4.0
  转换授权，Debian copyright 分列三个文件组）。
- 两版法律文本（`CAlicense.txt` = CC BY 2.0、`CAlicense4.txt` = CC BY 4.0）
  + `CAreadme.txt` 再分发协议随包携带并复制到 `licenses/`。
- conan `license` 字段：CC-BY-4.0。

## OHOS 适配

纯数据包，无编译无链接（kicad-demos 范式）：

- `build()` 仅做防漂移清单校验：7 根文件在位 + 7 个目录精确计数 +
  全树 35723 文件总数断言（排除 conan 生成的 `.sh`/conaninfo.txt）；
- `package()` 整树复制到 `share/ldraw/`，许可证另存 `licenses/`；
- `package_id` 清空（数据包与 settings 无关）；
- `cpp_info.resdirs` 暴露 `share/ldraw`，`runenv_info` 定义 `LDRAWDIR`
  （LeoCAD/LDView 等 LDraw 消费工具的库定位环境变量）。
- 布局与 Debian 惯例一致：`/usr/share/ldraw/{parts,models,p,LDConfig*.ldr}`
  （Debian rules `execute_after_dh_auto_install` 实证安装清单）；本包额外
  保留 Readme 与 CA 协议三件（官方发行原样）。

## 测试口径

上游 complete.zip 无测试套件（纯数据发行）。Debian autopkgtest 仅为
leocad 能否找到库的冒烟测试（下游打包测试，不属上游范围）。适配后
消费者探针（`test_package/ldraw_parts_probe.cpp`）5 组断言：

1. 35723 全库清单精确计数（7 根文件 + 7 目录分项 + 递归总数）；
2. 代表性内容锚点：3001.dat（2x4 砖）/ 2-4edge.dat / p48 `48\1-4cyli.dat` /
   `s\003238s1.dat` / 3001p01.dat（印刷件）/ car/pyramid 样例 / Note2602CA.txt；
3. **全树 35444 个 .dat 逐个格式校验**（首行 `0 ` 注释 + `0 Name:` 行）+
   135 个 PNG 魔数校验；
4. LDConfig.ldr `0 !COLOUR` 322 条目 + 2602 配置更新标记 + CC 许可证双文本；
5. 截断/坏头注入负向用例（写入→校验拒绝→清理，证明探针真实读写包目录）。

## 真机验证（鸿蒙侧，2026-09-25）

`python3 scripts/ohc-run.py conan-verify ldraw-parts 2602`
（华为 PC 真机，Conan 2.29.1 + ohos-aarch64 profile）：
**八道门禁全过**，判定「配方验证通过，可标记 status: published」。

- G0 ✅（构建系统 unknown，跳过预查询）
- G1 ✅ 配方完整性（name/version/source/build/package/package_info/export_sources/补丁应用调用/conandata/test_package/MANIFEST 全项）
- G2 ✅ conan create 干净构建（真机实跑，含 test_package 探针；94MB 源归档从 USTC 镜像实测下载成功）
- G3 ✅ 无 bin//lib/ 目录，无系统同名库冲突（R26 通过）
- G4 ✅ 产物完整性（package_id 清空 → 空包 ID，verify 提示「无法找到程序包 ID」属预期）
- L2/L4/L5 ✅（纯数据包无 cache 路径，跳过）
- 探针真机输出：`ldraw_parts_probe: all assertions passed`（5 组断言全过，逐项 [OK] 见 reports/conan-create.log）

产物实测：`share/ldraw/` 精确 35723 文件（parts 23839 + s 8813 + textures 135 + p 1743/127/920 + models 139 + 根 7），`licenses/` 3 文件（CAlicense 双版本 + CAreadme），无多余文件混入。

配方层要点（真机实证）：
- 源归档 94MB（conan 报告下载量 98.7MB）在真机 get() 实测从 USTC 下载成功，aliyun 为备用镜像；
- basic_layout 排除清单（`*.sh`/conaninfo.txt）沿用 inform6-library 实证结论；
- verify 的 G2 走 `--user=ohpcd --channel=stable` 引用，裸 create（无 channel）为独立 cache 槽，两次均干净构建，防漂移计数两次均过。

## 参考

- LDraw.org 库: https://library.ldraw.org/
- Debian ldraw-parts: https://salsa.debian.org/debian/ldraw-parts
- Ubuntu 池（USTC 镜像）: https://mirrors.ustc.edu.cn/ubuntu/pool/multiverse/l/ldraw-parts/
