# libloc-database 0-20260628-0345 适配笔记

## 1. 软件与版本

| 项 | 值 |
|---|---|
| 包名 | `libloc-database` |
| 版本（本仓） | `0-20260628-0345` |
| 上游发布物 | `location-2026-06-28-03:45.db.xz`（5,396,292 B，2026-06-28 04:38 发布） |
| Debian orig 版本 | `0~20260628~0345`（`-`↔`~` 仅为 Debian 归一化，同一版本） |
| 上游数据仓 | https://git.ipfire.org/?p=location/location-database.git |
| 上游打包仓 | https://git.ipfire.org/?p=location/debian/libloc-database.git（mirror of salsa.debian.org） |
| 上游官方下载源 | location.ipfire.org/databases/1/archive/（**CI Worker 不可达**，见第 4 节问题 5） |
| 本配方实际源码 | Debian 官方源码包 `libloc-database_0~20260628~0345.orig.tar.xz`（经权威镜像 `mirrors.tuna.tsinghua.edu.cn` 主 / `mirrors.ustc.edu.cn` 备），内含与上游发布物逐字节一致的 `location.db` |
| 许可 | CC BY-NC-SA 4.0（数据，见上游 README） |

## 2. 软件性质：纯数据包

`libloc-database` 不是源码库，而是 **IPFire Location Database 的编译产物**：上游把
地理位置数据编译成二进制 DB（`location.db`）后单独发布，供 `libloc` 库查询使用。

- 无构建系统（上游仓根树只有 `README.md` / `COPYING` / `countries.txt` / `database.txt` / `overrides/`）
- 无编译产物、无 CLI 工具 → 不需要 `commands.json`（R38 不适用）
- 无第三方依赖：`debian/control` 的 `Build-Depends` 仅 `debhelper-compat (= 14)`，
  官方二进制包 `control` 无 `Depends` 字段，`Architecture: all`
- 无上游自动化测试（详见第 5 节）

## 3. 构建/安装过程（本仓）

```bash
# 本包无编译步骤：conan create 只执行 source() → build()（空实现，仅应用补丁）→ package()
#   source():  download() 取上游 .db.xz（sha256 校验）
#   package(): lzma 流式解压 → share/libloc-location/location.db，再做 size+SHA256 校验
conan create archives/l/libloc-database/0-20260628-0345 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

构建步骤与退出码、原始输出见 `reports/`。

## 4. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 用 `get(self, **self.conan_data["sources"])` 拉取上游发布物会抛 `BadZipFile` | conan 的 `get()` = `download()` + `unzip()`；`unzip()` 只识别 tar 归档（`.tar.gz/.tgz/.tar.bz2/.tar/.tar.xz/.txz`）与 zip，裸 `.xz`（压缩的是单个文件而非 tar 目录）会落到 `zipfile` 分支 | 改用 `download(url, sha256, filename)` + Python `lzma.open()` 手工流式解压（48 MB 数据不驻留内存） |
| 2 | 上游文件名含冒号 `location-2026-06-28-03:45.db.xz` | 上游 `debian/watch` 的版本化命名（`Uversion-Mangle` 也把冒号转成 `~`） | conandata.yml 增加 `filename: "location.db.xz"`，归一化落盘名，规避冒号在路径/正则中的风险 |
| 3 | 上游仓无法 `git clone`（https 404 / git:// 连接拒绝） | git.ipfire.org 不提供匿名 clone | 用 gitweb `blob_plain` API 逐个核验文件，并用 gitweb snapshot（`a=snapshot;sf=tgz`）拉取完整树（8 MB）做全量核验 |
| 4 | `conan-verify` G4 只报 `⚠️ 无法找到程序包 ID`，并未真正检查产物 | G4 先跑 `conan list <ref>:* --format=json`，再取 `listing["Local Cache"][self.software]`；该 JSON 的键是**完整引用**（`libloc-database/0-20260628-0345@ohpcd/stable`），而 `self.software` 只是包名 → `KeyError` → 提前 `return passed=True`。存量 116 份 `conan-verify-report.md` 中 104 份都是这一分支，0 份出现"无任何产物" | 属框架侧解析缺陷（对任何包都早退），不在本配方内修（W2 原子性：框架修复须独立 PR）；本包的产物真实性改由 `package()` 内的 size+SHA256 校验与 `test_package` 6 项断言承担，见第 6 节 |
| 5 | CI 构建 `#48346`/`#48351` 失败：`源码下载超时 (https://location.ipfire.org/databases/1/archive/location-2026-06-28-03:45.db.xz...)` | CI Worker 网络受限，无法访问 `location.ipfire.org`（该域名仅解析到 IPv6 `haj.ipfire.org`；`mirror.`/`download.ipfire.org` 均不存在），且 CI 的镜像回退白名单（`ci/conan/build_and_test.sh:1023-1028`）不含该域，无镜像可回退；GitHub 上亦无官方数据镜像仓 | 改用 Debian 官方源码包 `libloc-database_0~20260628~0345.orig.tar.xz` 的**权威镜像源**（主 TUNA、备 USTC，`url` 列表由 conan 逐个尝试），其内含 `location.db` 与上游发布物解压结果、Debian 官方 deb 内文件三方 `cmp IDENTICAL`；`package()` 仍以固定 size+SHA256 校验产物身份。换源后 `conan create` EXIT=0、`test_package` 6/6 复验通过 |

## 5. 上游测试情况（如实申报）

**上游没有自动化测试入口** —— 不是"未执行"，而是"不存在"：

1. 上游数据仓 `location/location-database.git`（master `d4542bf`）全量 snapshot 只有
   12 个路径：`.gitignore`、`COPYING`、`README.md`、`countries.txt`、`database.txt`、
   `overrides/`（6 个 override 文件）。无 `Makefile`/`CMakeLists.txt`/`configure`/
   `meson.build`/`setup.py`，无 `tests/`、`t/` 目录（逐个 HTTP 探测均为 404）。
2. Debian 打包仓 `debian/` 目录仅 8 项（changelog/control/copyright/gbp.conf/
   `libloc-database.install`/rules/source/watch），**无 `debian/tests`** → 无 autopkgtest 入口。
3. 上游 README 明确：本仓"**仅供审计**……数据不是机器友好格式，不应被任何应用解析"，
   官方只发布编译好的 DB，配套解析/校验工具在上游 `libloc` 项目中（本包不消费）。

因此 `test_package` 的 6 项消费侧断言**不能替代上游测试统计**，只作为消费侧回归。
上游发布物的正确性用"与官方发布物/Debian 官方二进制包逐字节一致"来核验：

```
$ sha256sum location-2026-06-28-03:45.db.xz
7661df8ea10a0eab2769949ec423106bb4bbff9d876a3d2278114cd080920a51
$ xzcat ... | sha256sum
819748dd33a18aecbbce624bc10b0b685cb292e95377bb2b434665b5afc69ffd  (48,930,795 B)
$ sha256sum <deb 内 usr/share/libloc-location/location.db>
819748dd33a18aecbbce624bc10b0b685cb292e95377bb2b434665b5afc69ffd
$ cmp <本地解压> <deb 内提取>   → IDENTICAL (rc=0)
```

> 断言独立性说明：`test_package` 的"字节数/SHA256"两项断言与配方 `package()` 的完整性校验
> 共用同一组上游锚定常量（`DB_SIZE_BYTES`/`DB_SHA256`），其权威来源是上面两条外部证据
> （conandata 的源码 sha256、Debian 官方 deb 内 `location.db` 的逐字节比对），
> 因此不构成"自己证明自己"的闭环。

> 源一致性证据（换源后补测）：上游发布物 `location-2026-06-28-03:45.db.xz` 的解压产物、
> Debian 官方源码包 `libloc-database_0~20260628~0345.orig.tar.xz`（sha256
> `f4f6d75d73761792fe47bf9390f3c80cbe5904c8258d8ccb0c47ac1643ebd969`，5,427,568 B）内的
> `location.db`、以及 Debian 官方二进制包内的 `usr/share/libloc-location/location.db`，
> **三者 `cmp` 均 IDENTICAL（rc=0）**；镜像 TUNA 与 USTC 的该文件 Content-Length 一致
> （5,427,568 B）。日志：`logs/40_alt_source_verify2.log`、`39_alt_source_verify.log`。

## 6. conan-verify 门禁实际执行情况（如实记录）

`conan-verify libloc-database 0-20260628-0345` 退出码 **0**，报告 `Verdict: PASS`，
但逐门禁看，实际执行与跳过如下：

| 门禁 | 报告结果 | 实际是否执行 | 依据 |
|---|---|---|---|
| G0 预构建风险评估 | PASS | 未识别构建系统，非阻塞 | `conan-verify-report.md` |
| G1 配方完整性 | PASS | ✅ 真执行（8 个字面量 + conandata + test_package/MANIFEST.yml 全部命中） | 同上 |
| G2 conan create | PASS | ✅ 真执行（干净源码重建：下载→解压→打包→test_package） | `reports/conan-create.log` |
| G3 系统同名库隔离 | PASS | 部分（无 `lib/`，无冲突可言） | 同上 |
| G4 产物完整性 | 报告 PASS | ❌ **未执行**：`⚠️ 无法找到程序包 ID`（`KeyError` 早退） | `scripts/ohc/conan_verify.py` G4 取 `listing["Local Cache"][self.software]`，而 JSON 键是完整引用 `libloc-database/0-20260628-0345@ohpcd/stable` |
| L2 / L4 / L5 | 报告 PASS | ❌ 全部跳过（`⏭️ 跳过（无 cache 路径）`，因 G4 未设置 cache 路径） | 同上 |

存量统计（本仓 `archives/*/*/*/reports/conan-verify-report.md`，116 份）：
**104 份**含 `无法找到程序包 ID`，**0 份**含 `无任何产物`，**0 份**含 `G4: ❌`。
复现命令（只读）：
```bash
ls archives/*/*/*/reports/conan-verify-report.md | wc -l
grep -rl '无法找到程序包 ID' archives/*/*/*/reports/conan-verify-report.md | wc -l
grep -rl '无任何产物' archives/*/*/*/reports/conan-verify-report.md | wc -l
```
即 G4 在 conan-verify（`@ohpcd/stable` 引用）路径下对所有包都提前 PASS，
**因此本次 PASS 不能作为"产物完整性已验证"的证据**。

框架修复（G4 的 JSON 键解析 + 资源包豁免）属于框架文件改动，按 W2 原子性必须单独提
"框架修复类 PR"，不与本配方混合提交。

产物真实性的替代证据（本 PR 用它们承担）：
1. `package()` 内解压后校验 `size == 48930795` 且 `sha256 == 819748dd…9ffd`，不符直接
   抛 `ConanException`（构建期失败，不可绕过）；
2. `test_package/test_database.py` 6 项消费侧断言（路径/字节数/SHA256/魔数/头部时间戳/尾部可读），
   conan create 实测 **6/6 通过**；
3. 与 Debian 官方二进制包内的 `location.db` 逐字节比对 `cmp` → `IDENTICAL (rc=0)`。

CI 侧（`ci/conan/build_and_test.sh`）对数据包的判定（源码级核验）：
L2=skip（无 `bin/`）、L4=pass: no patches、L5=warn（无 `bin`/`lib`/`include` 不 fail）、
L1e=skip（无 `bin`/`lib`/`include` 可供破坏）——即 CI 可绿。

## 7. 产物清单

| 路径 | 说明 |
|---|---|
| `share/libloc-location/location.db` | 上游 2026-06-28 版数据库，48,930,795 B，sha256 `819748dd…9ffd` |

## 8. 编译结束

本地适配结束（2026-09-15，含 CI 反馈后的换源修复）：conan create 通过（EXIT=0）、
test_package 6/6 通过、上游无自动化测试（已核验并申报）、`conan-verify` 退出码 0
（但 G4/L2/L4/L5 未真正执行，见第 6 节）、W3 本地 CI 通过（`reports/w3-local-ci.log`）。
换源修复（详见第 4 节问题 5、第 5 节源一致性证据）：CI Worker 无法访问上游
`location.ipfire.org`（构建 #48346/#48351 实测下载超时），改用 Debian 官方源码包的
权威镜像源（主 TUNA、备 USTC），产物 `location.db` 与上游/Debian 官方文件三方 `cmp` 一致。
未执行任何远端写操作（commit/push/PR/制品上传）。
---

**编译结束**: 2026-09-16 00:04
**最终状态**: built
