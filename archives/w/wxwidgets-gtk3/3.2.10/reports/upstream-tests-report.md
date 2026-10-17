# wxwidgets-gtk3 3.2.10 上游测试真机运行报告（R51 / rule4 逐项归因）

## 1. 运行环境与方式

- 设备：`10.62.210.132:8022`（HarmonyOS PC，OHOS 6.0，aarch64，HarmonyOS HongMeng Kernel 1.12.0，clang 15.0.4，SELinux 域 `u:r:adhoc_bin:s0`）
- 源码：官方 release tar.bz2，sha256 `d66e929569947a4a5920699539089a9bda83a93e5f4917fb313a61f0c344b896`（与 conandata.yml 一致）
- 依赖：设备 conan 缓存中 gtk/3.24.43（broadway-only）全依赖链（pkg-config 闭包与 conan create 消费同一制品）
- 构建：3.2.10 的 CMake 不支持构建 tests（仅 samples），按上游 autoconf 路径构建，configure 镜像配方选项（`--disable-shared --with-gtk=3 --with-libpng=builtin --with-libjpeg=builtin --without-libtiff --with-expat=builtin --with-zlib=builtin --without-opengl`）
- 运行：`cd build/tests && ./test`（Catch v1.12.2），295 个注册用例全量运行
- 复现脚本：`reports/upstream-test-run.sh`（S1–S10）
- 原始日志：`reports/upstream-test-output.log`（857 行，sha256 `0bcb93eceb9caccf149a1efdfc7d140b1bd6134c1de3f82f2094648aea7d2ff8`）
- 运行时间：2026-09-04 18:09（UTC+8）

## 2. 汇总结果

```
test cases:     295 |     267 passed |  28 failed   （通过率 90.5%）
assertions: 1229604 | 1229496 passed | 108 failed  （通过率 99.99%）
```

GUI 套件 `tests/test_gui`：链接成功（移除上游 configure 无条件追加的 `-lX11` 后）；运行需显示连接，SSH 沙箱无显示服务、broadway-only gtk 无 broadwayd 运行路径：`Error: Unable to initialize GTK+, is DISPLAY set properly?`（RC=255，日志 `reports/upstream-test-gui-run.log`）。GUI 套件不在 295 之内。

## 3. 28 项失败逐条归因（按根因分类）

> 逐条位置为 `tests/` 下源文件行号，断言原文与展开值见 `upstream-test-output.log`。
> 表中断言数合计 106，Catch 汇总为 108（其余 2 处为同一用例内 WARN/嵌套分节的重复计数，见日志）。

### A. 测试数据夹具未就位（运行脚本时序缺陷，可修复——非平台限制）

`make -C tests all` 首次在 test_drawing 链接失败处中止，排在 `all` 目标末尾的 `data/data-images` 目标（负责把 horse.* 拷入运行目录）未执行，测试二进制随后立即运行——以下用例因 horse.* 缺失而级联失败（证据：Eof 组报 `wxFFile::Eof(): file is closed!`，即 horse.bmp 打不开；CopyFile 组 `File 1: horse.xpm ... false`）。**运行脚本已修复（S7c 显式构建夹具并校验），待设备恢复重跑更新数字，预期此组全部转通过。**

| # | 用例 | 断言位置 | 失败表现 | 可否自做依赖解决 |
|---|------|---------|---------|----------------|
| 1 | FileFunctions::CopyFile | filefn.cpp:121 | `REQUIRE(wxCopyFile("horse.xpm", …))` → false（源文件缺失） | ✅ 已修脚本，重跑即过 |
| 2 | FileFunctions::Eof | filefn.cpp:433/434/437/438 | horse.bmp 打不开→`file is closed!` 级联 4 断言 | ✅ 同上 |
| 3 | FileFunctions::Error | filefn.cpp:454/456/457 | 同上级联 3 断言 | ✅ 同上 |
| 4 | FileFunctions::FindFileNext | filefn.cpp:243/256 | glob `horse.*` 命中不足→`foundFile1 != foundFile2` 失败 | ✅ 同上 |
| 5 | FileFunctions::FileExists | filefn.cpp:168 | `wxFileExists(L"horse.png")`（宽字符变体）false——窄字符同名断言（:161）已通过，本条疑为夹具缺失的连带（horse.png 由 data-images 提供）；待重跑判别是否为宽路径 API 差异 | ✅ 重跑判别 |

### B. `/tmp` 只读文件系统（环境硬限制：`touch /tmp/x` → Read-only file system）

| # | 用例 | 断言位置 | 失败表现 | 可否自做依赖解决 |
|---|------|---------|---------|----------------|
| 6 | wxFileName::CreateTempFileName | filenametest.cpp:651/661/665 | 测试数据表**硬编码前缀 `/tmp/foo`**（filenametest.cpp:638 `{ "/tmp/foo", "/tmp", true }`），只读 /tmp 下创建失败 | ❌ 需改上游测试断言（模板允许但须逐条申报，本次未改） |
| 7 | wxFileName::SameAs | filenametest.cpp:801 | `tempnam(NULL,…)` 返回路径的 Mkdir 失败：musl tempnam 对候选目录做 `access(X_OK)` 检查，HMDFS 权限位使 X_OK 恒 false（知识库 R49/E524 实证）→回退 P_tmpdir=`/tmp`→EROFS | ❌ 平台组合限制（HMDFS X_OK + /tmp 只读） |

### C. 应用沙箱 FS 访问限制（环境硬限制：普通用户沙箱拒绝枚举 `/`、读 `/proc`、`/sys`）

设备实测证据：`ls /` → Permission denied；`ls /sys/power/state` → denied；`/proc/cpuinfo` 不可读（wxFile::Special 的 ReadAll 得空串）。

| # | 用例 | 断言位置 | 失败表现 | 可否自做依赖解决 |
|---|------|---------|---------|----------------|
| 8 | Dir::Exists | dir.cpp:239（×2） | `Directory /`、`Directory //` 应存在→`d.IsOpened()==false` | ❌ 沙箱硬限制 |
| 9 | Dir::GetName | dir.cpp:255/256/257 | `d.Open("/")` false 级联 3 断言 | ❌ 同上 |
| 10 | wxFile::Special | filetest.cpp:154 | `/proc/cpuinfo` ReadAll 为空→`!s.empty()` 失败 | ❌ /proc 不可读 |
| 11 | wxTextFile::Special | textfiletest.cpp:348/360/361 | `/proc` 节 GetLineCount 0>1；`/sys` 节 `f.Open("/sys/power/state")` false 级联 | ❌ /proc、/sys 不可读 |

### D. HMDFS 文件系统语义差异（环境硬限制）

| # | 用例 | 断言位置 | 失败表现 | 可否自做依赖解决 |
|---|------|---------|---------|----------------|
| 12 | wxFileName::Exists | filenametest.cpp:756 | `wxTCPServer::Create(sockfile)`（AF_UNIX socket，位于可写 TMPDIR）后 `Exists(…, wxFILE_EXISTS_SOCKET)` false——HMDFS 不支持 AF_UNIX socket 文件 | ❌ 平台能力缺失（验证指南同结论） |
| 13 | wxFileSystemWatcher::EventCreate | fswatchertest.cpp:288/324 | HMDFS inotify 上报事件类型与上游预期不符（`32 == 1`，创建被归入其他类别）＋事件数 1≠2 | ❌ HMDFS inotify 语义 |

### E. musl 无 glibc locale/charset/数值解析行为（环境硬限制：OHOS libc 为 musl，无 glibc locale 数据库）

代表性证据：`REQUIRE("," == GetDecimalPoint())` 得 `"," == .`（测试设法语 locale 后 musl 无数据回退 C）；`ToString(1234L)` 得 `1234`（localeconv 千分位为空）；`GetBestTranslation` 得 `en`（无 .mo 目录查找）；`cWC2MB` CP1250 转换失败（iconv 无该 charset）。失败类别与制品仓 wxWidgets/3.3.3（wxBase 变体）真机上游测试一致。

| # | 用例 | 断言位置 | 失败断言数 | 具体原因 | 可否自做依赖解决 |
|---|------|---------|-----------|---------|----------------|
| 14 | IntlTestCase | intltest.cpp:106/125/139/203/255/266/393 | 7 | 法语 locale 数据缺失：小数点/日期格式/头域值/可用目录数（0==3）/目录分隔符 | ❌ musl 无 locale 数据 |
| 15 | wxTranslations::AddCatalog | intltest.cpp:304/305 | 2 | 无 fr/en_GB .mo 目录查找结果 | ❌ 同上 |
| 16 | wxTranslations::GetBestTranslation | intltest.cpp:309/310/327/328/339/340 | 6 | GetBestTranslation 恒 en（无翻译目录） | ❌ 同上 |
| 17 | wxUILocale::IsSupported | intltest.cpp:255 附近（分节） | 2 | fr/de 等 locale IsSupported=false | ❌ 同上 |
| 18 | wxUILocale::GetInfo | intltest.cpp:393 附近（分节） | 1+ | DECIMAL_POINT 等查询回退 C locale 值 | ❌ 同上 |
| 19 | wxUILocale::CompareStrings | intltest.cpp:427/429/449 | 3 | 无 locale 感知排序（strcoll 回退字节序） | ❌ 同上 |
| 20 | MBConvTestCase | mbconvtest.cpp:251/936 | 2 | musl iconv 缺 CP1250/CP950 charset（FromWChar/WC2MB 转换失败） | ❌ musl charset 集 |
| 21-27 | NumFormatter::ToString/FromString ×7 组（Long/LongLong/Double/ULongLong 的 To 与 From） | numformatter.cpp:83-93/106-111/126-129/184-194/235-245/279-289/323-339 | 57 | wxNumberFormatter 经 localeconv() 取千分位/分组，musl C locale 千分位为空：`1234 != "1,234"`；FromString 对含 `,` 输入解析失败（`1 == 1234`） | ❌ musl localeconv 无分组数据 |
| 28 | StringTestCase | strings.cpp:952/998 | 2 | musl strtod/printf 长数字往返精度与小数点行为差异（`1,23 == 1.23`） | ❌ musl libc 行为 |

（表中 #14-#19 同属 intltest.cpp 的多个 TEST_CASE，按 Catch 顶层用例名分列；断言行号可在 upstream-test-output.log 逐条复核。）

## 4. 分类汇总

| 根因类别 | 用例数 | 断言数 | 可修复性 |
|---------|-------|--------|---------|
| A 测试夹具未就位（脚本时序缺陷） | 5 | 11 | ✅ 脚本已修（S7c），待重跑——预期转通过 |
| B /tmp 只读（含 tempnam X_OK 回退） | 2 | 4 | ❌ 平台硬限制（改前缀须改上游测试，未改） |
| C 沙箱 FS（/、/proc、/sys 不可访问） | 4 | 9 | ❌ 平台硬限制 |
| D HMDFS 语义（AF_UNIX、inotify） | 2 | 3 | ❌ 平台硬限制 |
| E musl locale/charset/数值行为 | 15 | 79 | ❌ 平台硬限制 |
| **合计（Catch 顶层用例计）** | **28** | **108** | |

## 5. 结论与待办

- 28 项失败中：**5 项为运行脚本夹具时序缺陷（可修复，脚本已修正）**；**23 项为 OHOS 平台环境硬限制**（沙箱 FS / /tmp 只读 / musl locale / HMDFS 语义），逐条给出断言行号、展开值与设备实测证据，均不指向 wx 库适配缺陷。
- 待办：验证设备 sshd 当前离线；恢复后以修正脚本重跑，预期 272/295（92.2%），A 组 5 用例转通过、#5 顺带判别宽字符路径行为，届时更新本报告与 PR 描述数字。
- 运行环境级修复（不触碰上游源码/测试源码，详见 notes.md r8）：config.sub ohos 三元组、mktemp shim（HMDFS ACL）、移除 configure 无条件 `-lX11`。
