# ploticus 2.42 — OpenHarmony PC (aarch64) 适配

## 上游信息

| 项 | 值 |
|----|----|
| 上游工程 | Ploticus data display engine（作者 Stephen C. Grubb） |
| 官网/发布 | https://ploticus.sourceforge.net/ （SourceForge project `ploticus`） |
| 版本 | 2.42（2013-05，上游最终版本） |
| 源码 | `ploticus242_src.tar.gz`（535755 字节）<br/>sha256 `3f29e4b9f405203a93efec900e5816d9e1b4381821881e241c08cab7dd66e0b0` |
| 许可 | GPL（`src/Copyright` / `src/GPL.txt`） |
| 构建系统 | **手写 GNU Makefile**（`src/Makefile`，无 configure / CMake / autotools） |

> 本机直连 SourceForge 被 Cloudflare 522 阻断（与知识库 E421 一致）。本次采用
> **pkgsrc distfiles 镜像中的上游原始 tarball**，并用 pkgsrc `graphics/ploticus/distinfo`
> 的 SHA512/Size 交叉核对（完全一致）确认与官方发布同字节；`conandata.yml` 仍写官方
> URL + 上游 sha256，CI 侧照常从官方源下载校验。

## 交付面（包内容）

| 路径 | 说明 |
|------|------|
| `bin/pl` | 主程序：PS / EPS / SVG / SVGZ / PNG 出图（bundled GD16 光栅器） |
| `lib/libploticus.a` | 嵌入 API 静态库（上游 `libploticus-static` 目标） |
| `include/libploticus.h` | 嵌入 API 头文件 |
| `share/ploticus/prefabs/` | 上游 prefab 库（`pl -prefab ...` 用；配方通过 runenv 设置 `PLOTICUS_PREFABS`） |
| `licenses/` | 上游 Copyright / GPL.txt |

构建配置即上游默认：`exetarget: plpng`（bundled GD16）+ `-DNOX11 -DNOSWF`。
X11 关闭既是上游默认，也符合 HarmonyOS PC 无 X11 服务的现实；PNG/SVGZ 需要
libpng + zlib。

## OpenHarmony 适配改动

### `patches/0001-src-preliminaries.c.patch`

**问题**：上游把编译期宏 `TMPDIR`（`/tmp`）直接拷进 `TDH_tmpdir`，运行期完全不看环境变量。
HarmonyOS PC 将 `/tmp` 挂载为**只读**，于是所有需要临时文件的代码路径全部失败，例如：

```
pl proc drawcommands: error 522: Cannot open draw commands file (/tmp/ploqa1dQrRua_Z)
```

受影响的功能：`proc drawcommands`（内联命令会被写入临时文件）、`proc processdata`、
cgi 诊断文件。失败是静默降级（进程仍返回 0，但图元缺失）。

**修复**：改为运行期选择临时目录——`$TMPDIR`（可用时）→ 编译期默认目录（可用时）→
当前工作目录；可用性通过**在候选目录内实际创建一个探测文件**判定（`access()` 在
HMDFS 上不可靠，见 R49）。补丁不含任何平台宏（R8）。

**实测对照**（同一样例脚本，`TMPDIR=/tmp`）：

| 二进制 | 输出 |
|--------|------|
| 未打补丁 | `pl proc drawcommands: error 522: Cannot open draw commands file (/tmp/ploqa1e12Nze_Z)`（drawcommands 内容丢失） |
| 打补丁 | 无 error 行，出图正常 |

## 测试

| 面 | 结果 | 日志 |
|----|------|------|
| 上游套件（逐用例） | 46 例：**44 通过**，2 例为上游自身缺陷（见下） | `reports/test-report.md` |
| test_package（L1 消费者测试） | **7/7 通过**（含 3 个鸿蒙特有用例） | `reports/test-report.md` |
| `conan create` | 见 version manifest `test_results.conan_create` | `reports/` |

上游 2 项非通过用例均为上游自身问题，与适配无关：

1. `pltestsuite/run_all_scripts` 引用 **不存在的** `windbarbs.pl`（同目录只有 `windbarbs.htm`）；
2. `pltestsuite/testpf_compare` 是空壳脚本（只打印 “the 'compare' prefab is no longer available.”）。

## 使用

```bash
conan install --requires=ploticus/2.42 -g VirtualRunEnv --build=missing
source conanrun.sh          # 提供 LD_LIBRARY_PATH（libpng）与 PLOTICUS_PREFABS
pl -png mychart.pl          # 或 pl -svg / -eps / -svgz
```
