# dbskkd-cdb 3 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure、无 install 可用目标）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target aarch64-unknown-linux-ohos）
- 设备: HarmonyOS PC aarch64（os=OHOS 6.0，Conan 2.29.1）
- 状态: built

## 编译步骤

1. 依赖先行核对：`conan install --requires=cdb/20251021 --profile:host=<ohos-aarch64>
   --build=never -of <任务目录>/w0-deps` —— ohpcd 远端存在 OHOS/aarch64 制品，直接下载成功。
2. 原生探索：在任务私有源码副本里用 profile 的 clang 直接跑上游 Makefile
   （`make -j1 CC=<clang> COMPAT="-Wall -O2 -g -I<cdb 包>/include" CDBLIB="<cdb 包>/lib/libcdb.a"`），
   exit 0、零告警；不带词典运行得到 rc=78（`EX_CONFIG`），确认词典路径必须能在运行期指定。
3. 配方构建：`conan create` 由配方用 `GnuToolchain` 的 flags 重跑同一条 make 命令行，
   日志中 `Apply patch (portability)` 1 条、`RUN: make -j1 …` 1 条，随后自动执行 `test_package`。
   完整命令与输出见同目录 `manifest.yaml` 的 `validation.*` 段（权威副本，本节不复制）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备上程序启动即 `rc=78`，无法验证任何查词行为 | 上游把词典路径编译进二进制（`JISYO_FILE` 默认 `/usr/local/share/skk/SKK-JISYO.L.cdb`），而 OHOS 系统目录不存在且只读，包安装到任意 prefix 都无法指定自己的词典 | 补丁 0001：运行期覆盖，优先级 `argv[1]` → `DBSKKD_JISYO` → 编译期默认值；无平台条件编译，默认行为与协议不变 |
| 2 | 上游 Makefile 无法用 Conan 工具链驱动（编译器与 flags 同一变量、库路径硬编码、install 写死 `/usr/local/libexec`） | 手写 Makefile，不区分 CC/CFLAGS，也没有可覆盖的安装前缀变量 | 不改 Makefile：在 make 命令行整体替换 `CC`/`COMPAT`/`CDBLIB`，由 `package()` 显式安装 `bin/` 与 `licenses/` |
| 3 | `conan create` 在 test_package 阶段抛 `TypeError: expected str, bytes or os.PathLike object, not NoneType` | test_package 只声明被测包引用，而 cdb 是被静态链接的传递依赖，Conan 打印 `Skipped binaries cdb/20251021` 后不实例化其 binary，`package_folder` 为 `None` | test_package 的 `requirements()` 显式 `self.requires("cdb/20251021")`（版本与配方一致），再用该包 `bin/` 的绝对路径定位 `cdbmake`/`cdbtest`；已沉淀知识草稿 E577 |
| 4 | 单字符版本无法作为 Conan 制品版本 | `ConanName` 校验 `^[a-z0-9_][a-z0-9_+.-]{1,100}$` 要求版本长度 ≥ 2，`conan create` 导出阶段即报 `Invalid package version '3'`；而 CI L0n 又要求分支名去前缀等于「包目录名-版本目录」 | 目录与分支保留任务卡值 `3`，配方 `set_version()` 把制品版本归一化为上游发布号 `3.00`；`commands.json` 与版本级 manifest 留对应说明 |
| 5 | 本地 PF8 配方闸与单字符版本的归一路径互斥 | PF8 要求 `commands.json` 的 `versions[<版本目录>].ref` 恒等于「包名/版本目录」（即 `dbskkd-cdb/3`），而 `set_version()` 在 Conan `load_named()` 之后**无条件执行**、会覆盖命令行 `--version`（两项均实测：`version = "3"` 导出即 `Invalid package version '3'`；带 `set_version()` 的配方即使传 `--version=3` 也导出为 `3.00`）——同一字段被两条门禁要求成互斥的值 | 按仓库门禁口径把 `versions["3"].ref` 写为 `dbskkd-cdb/3`；同时在 `commands.json` 增加 `version_normalization` 段（含 `artifact_ref`）、版本级 manifest 记 `conan_ref`、README 的「版本号」条与 PR 正文均明确声明**制品仓中的真实引用是 `dbskkd-cdb/3.00`**，查询/消费一律用 3.00。该框架冲突已写入容器层 `feedback/pending/2026-09-11-dbskkd-cdb-3.md` |

## 源码修改

- `patches/0001-dbskkd-cdb.c.patch`（由 `ohc-run.py refresh-patch --auto` 生成，文件名为工具产物名）：
  在 `main()` 中把打开词典用的路径从常量 `JISYO_FILE` 改为按 `argv[1]` → `DBSKKD_JISYO` →
  `JISYO_FILE` 的顺序选取，改动 1 个文件 +18/-1 行，无 `#ifdef` 平台分支、无生成物改动。
  补丁应用结果已用 `patch_ng`（strip=1）在纯净源码树上复现并与验证树逐字节比对一致。

## 依赖版本

- `cdb/20251021`（DJB cdb，含 tinycdb 兼容 `cdb.h` 与自包含 `libcdb.a`；静态链接进制品）
- 运行期仅 `libc.so`（OHOS musl）

## 验证结果

- 上游测试：3.00 不存在可运行的上游测试入口（台账与取数命令见 `test_package/MANIFEST.yml`），
  按可审计口径记 0，既不计 PASS 也不计 SKIP。
- 适配后消费者测试：`TOTAL=31 PASS=31 FAIL=0`（标记行 `dbskkd-cdb test_package summary`），
  其中 26 个为消费者协议/夹具用例、5 个为**鸿蒙特有平台检查**（用例名前缀 `ohos_`，
  `test_package/fixtures/ohos_platform_check.py`：ELF64/AArch64/PIE 目标形态、`.codesign` 签名段、
  NX/RELRO/BIND_NOW 加固基线、可重定位且仅依赖 libc、最小环境运行）；
  命令与输出见 `manifest.yaml` 的 `validation.test_package` 与 `validation.ohos_platform_checks`。
- 可复现性：多轮清缓存构建的 `bin/dbskkd-cdb` sha256 完全相同，各轮日志均含 1 条 `RUN: make`。
- 证据形态：仓库审查规则 19 禁止 PR 携带 `*.log`，故原始日志不随 PR 提交；其关键行区间
  **逐字摘录（非全文）**进 `reports/conan-create-report.md`（采信轮 create/打包/31 用例）
  与 `reports/w3-local-ci-report.md`（W3 各门禁与 Build Summary）。两份报告头部给出原始日志的
  任务私有留存路径、sha256 与复核命令，文末列出摘录区间与未摘录部分。
- 反向验证（L1e）：把包产物换成只打印版本行的桩 ELF 后测试 rc=1（`TOTAL=27 PASS=11 FAIL=16`），
  产物整体移走后 rc=1 且报 `binary missing in package` —— 全部用例（含 5 个平台检查）都从被测包
  `bin/` 取二进制，不接受 PATH 上的同名命令。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/dbskkd-cdb` | 22912 B | SKK 词典服务器（ELF aarch64，PIE + BIND_NOW + RELRO + NX，含 hnp `.codesign` 自签段） |
| `licenses/LICENSE` | 1112 B | 上游 MIT 许可证 |

## 注意事项

- 不要对产物做 strip：`.codesign` 段记录签名时的镜像长度，链接后任何字节改写都会使签名失效、
  内核拒绝 exec。上游本身也不 strip。
- 词典是**使用者自备**的数据文件（SKK-JISYO 文本经 `skktocdbm.sh` + `cdbmake` 转换）；
  本包不打包上游的 `makeskkcdb.sh`/`skktocdbm.sh`（它们依赖 awk 与名为 `cdb` 的包装脚本，
  且写死了 `/usr/local/share/skk` 路径），README 给出了在 OHOS 上可用的等价两步命令。
- 测试夹具 `.cdb` 是二进制，不随 PR 提交：运行期由 `test_package/fixtures/make_dict.py`
  重建，提交的是纯文本 SKK-JISYO 源与 cdbmake 输入 golden。

## 发现与知识

- **E577**（新草稿）：test_package 访问传递依赖提供的可执行工具/数据时必须显式 `requires` 该依赖，
  否则 Conan 先打印 `Skipped binaries` 再让 `package_folder` 为 `None`，
  配方侧 `os.path.join(..., None, "bin")` 抛 `TypeError`。
  草稿位于 `knowledge/drafts/E577-draft-7B7D.kv` 与 `.md`。
- **E563**（既有草稿）：任务卡单数字版本不能直接作为 Conan 版本，目录保任务卡值过 L0n、
  配方用 `set_version()` 归一化制品版本；本包按同一口径取上游发布号 `3.00`。
- 上游把数据文件路径编译进二进制、且目标平台系统目录只读时的通用做法：
  运行期覆盖（命令行 → 环境变量 → 编译期默认）既能保持默认行为又使制品可重定位，
  比平台条件编译更可取（本包补丁 0001 即此形态）。
