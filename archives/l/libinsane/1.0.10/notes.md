# libinsane 1.0.10 适配笔记

## 编译环境
- 构建系统: meson（上游 `meson.build`，含 `subprojects/libinsane` 与 `subprojects/libinsane-gobject` 两个子项目）
- 编译日期: 2026-09-28（W3 收口轮）；构建机 = B 机（HarmonyOS aarch64），worktree `~/qzy/主理-74-libinsane-1.0.10`
- 编译器: clang（profile `ci/conan/profiles/ohos-aarch64`，os=OHOS / arch=armv8）
- Conan: 2.29.1；`CONAN_HOME=$HOME/tmp/ch/home-qw2-libinsane`（本窗另 `conan remote disable conancenter`）
- 状态: built（`conan-verify` **Verdict=PASS**、G0–G4 全 ✅；`.ci-result.json` `exit_code=0`）

## 编译步骤
1. `source()`：`get()` 官方 tarball（`conandata.yml`：GitLab 归档直链，sha256
   `a9b8daaef03eb3bc4a8e638131e506ff3c2f99f715170da572e7f5ce7ba76467`，`strip_root=True`）。
2. `generate()`：`PkgConfigDeps` 生成依赖 `.pc`；**`_merge_glib_pc_variables()`** 把 glib 包内真
   `glib-2.0.pc` 的 `glib_mkenums` 等 tool/data 变量并进生成件（gnome 模块 `find_program` 要读它，
   缺了会 `Could not get pkg-config variable … glib-2.0`，`src/meson.build:17`）；
   `MesonToolchain` 注入 `-Dwrap_mode=nodownload`、`-Ddefault_library=shared` 与子项目开关
   `libinsane-gobject:{introspection:false, gtk_doc:false}`（必须走 `subproject_options`，
   写进 `project_options` 是硬错；用 bool 不用 feature，因上游 `meson_version >=0.37.1`）。
3. `build()`：`apply_conandata_patches()` → `meson.configure()` → `meson.build()`。
   **默认目标会编出上游全部 CUnit 测试可执行文件**（证明测试面可编译），但 `build()` 不调
   `meson.test()` —— 真跑在 W3 之外单独做，读数见「验证结果」。
4. `package()`：`meson.install()` → 拷 `LICENSE` → `rm *.la` → **`_sign_shared_libs()`**（见下方「遇到的问题与解决方案」第 1 条）。
5. `package_info()`：`libs=["insane","insane_gobject"]`、`includedirs=["include"]`、
   `system_libs=["pthread"]`（仅 Linux/OHOS）。

## 遇到的问题与解决方案

> **问题行（2026-09-28，CI 两次复现 → 按先例修配方）**：
> - **现象**：`../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]`，
>   `Running 'llvm-ar --version' gave "[Errno 2] No such file or directory: 'llvm-ar'"`，
>   → `ERROR: libinsane/1.0.10: Error in build() method, line 169` → `conan create failed`。
> - **根因**：框架 `ci/conan/build_and_test.sh:566/:1320` 把 `AR` 导出成 llvm-* **裸名**，
>   而 `ci/conan/profiles/ohos-aarch64:29` 只声明 `c/cpp` executable、**未声明 `ar`**
>   ⇒ meson 只能去 worker PATH 找裸名；B 机有 `/data/service/hnp/bin/llvm-ar` 故本地一直绿。
> - **修法**：`build()` 里 `Meson.configure()` 之前**弹掉裸名 `AR/AS/STRIP/NM/RANLIB`、
>   改锁 `shutil.which()` 解析出的绝对路径**（优先 `llvm-*`，退回 binutils 同名）——
>   **同 `babl-tools/0.1.126` 与 `at-spi2-core/2.60.5` 的 `generate()` 写法**（两者均 merged 且 `ci=passed`）。
> - **证据**：CI build **#63803**（worker `OpenHarmonyPCDeveloper-CI-009`）与
>   **#63820**（worker **`OpenHarmonyPCDeveloper-CI-011`**）**两次跨 worker 首错逐字相同**；
>   七步均 `worker-prep/git-clone/checkout-pr/conan-setup` ✅ 只挂 `conan-build-test`；
>   同日志 `:134-138 curl` 缺失仅 `[WARN] … will rely on conan's download` **非阻塞**
>   ⇒ 排除"网络/源码下载"与"平台类别=未知"的误诊；**本包 `conanfile.py` 无 `llvm-ar` 字面量**
>   ⇒ 排除配方逻辑缺陷，属**环境变量注入与 meson 探测口径不匹配**。


| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `test()` 报 `Error loading shared library libinsane.so.1: (needed by ./test_libinsane)` → rc=127，`errno` 为空 | OHOS 加载器拒收本包新装出的 `.so`：`.codesign` 段在（4096 B）、`LD_LIBRARY_PATH` 十二个目录全给对了仍拒 | **四臂对照**（见「验证结果」节末的四臂读数）锁定签名失效；按 glib/2.84.0.2 `_sign_shared_libs()` 先例在 `package()` 末尾 `remove-section .codesign` → `binary-sign-tool -selfSign 1` → `chmod`，全仓 1147 个配方同款 |
| 2 | G2 一度红在 `Could not get pkg-config variable and no default provided for PkgConfigDependency glib-2.0`（`src/meson.build:17`） | Conan `PkgConfigDeps` 只按 `package_info` 渲染 `.pc`，glib 自己 `.pc` 里的 `glib_mkenums`/data 变量缺失；而 `PATH` 上的 `/data/service/hnp/bin/glib-mkenums` 是 perl 脚本、shebang `#! /usr/bin/perl` 在本机不存在 ⇒ ninja 期 `FileNotFoundError` | `_merge_glib_pc_variables()` 把依赖包内真 `.pc` 的**缺失键**并进生成件（前缀仍指包目录，不污染缓存）；⛔ 不靠 PATH 找工具 |
| 3 | `glib/2.88.x` 解析不出图：`Version conflict … originates from glib/2.88.3.1` | 2.88.x 拉 `zlib/1.3.2`，与 sane-backends 图里的 `zlib/1.3.1.1` 冲突 | 钉 `glib/2.84.0.2`（与 sane-backends 同图的最新版；`conan install` 探针实证） |
| 4 | 上游 `libinsane-gobject` configure 期 `Dependency "gobject-introspection-1.0" not found`（`src/meson.build:46`），`generate_vapi` 还要 `vapigen` | 上游**没有**对应开关；交叉构建下 host 侧没有 `g-ir-scanner`/`vapigen` | 补丁 0001–0003 给子项目加 `introspection`/`gtk_doc` 两个 bool 选项并在配方里关掉；只影响 typelib/Vala/gtk-doc 这些**构建期产物**，C 库、头文件、`.pc` 照常交付（同族先例：template-glib 3.36.2 / libnotify 0.8.3.1 / libpeas2 2.2.1） |
| 5 | `lis_compare` 七条断言全 FAIL（原断言写 `>0`/`<0`） | **断言前提与上游文档相反**：`include/libinsane/util.h:55-59` 明写 `\retval 1 if values are identical` / `\retval 0 if values are different`，`src/util.c:46-61` 返回 `val1.x == val2.x`，唯一调用方 `src/workarounds/check_capabilities.c:33` 也把它当布尔用 | 按**文档语义**改写同 7 条（相等→1、不等→0，双向覆盖，条数不变），并在测试文件里留注释与三处行号；⛔ 不是改判据换绿，是原断言写错 |

## 源码修改（3 枚补丁，全部只动 `subprojects/libinsane-gobject`）
- `patches/0001-libinsane-gobject-meson_options.txt.patch`：加 `introspection` / `gtk_doc` 两个 bool 选项（上游没有）。
- `patches/0002-libinsane-gobject-src-meson.build.patch`：`gnome.generate_gir()` / `generate_vapi()` 按 `introspection` 选项门控。
- `patches/0003-libinsane-gobject-doc-meson.build.patch`：`gnome.gtkdoc()` 按 `gtk_doc` 选项门控（本机无 gtk-doc 工具链）。
- ⛔ 未改 `subprojects/libinsane`（C 核心）任何源文件；`lis_compare` 的语义差异只在 `test_package` 侧按文档改正断言。

## 依赖版本
- host：`sane-backends/1.2.1`（硬依赖，`transitive_headers+libs`）、`glib/2.84.0.2`（同上；钉版理由见问题 3）、`cunit/2.1.3`（`visible=False`，只在构建/测试期可见）。
- build：`meson/1.11.0`、`ninja/1.12.1`、`pkgconf/3.0.5`。
- 传递可见（`conan-verify` 依赖图实测）：curl/libpng/libtiff/libjpeg-turbo/zstd/webp/LibXml2/libusb 等，全部来自 sane-backends。

## 验证结果
```text
conan-verify：**Verdict: PASS**（reports/conan-verify-report.md:3，Date 见现件 `reports/conan-verify-report.md:6`（**该文件由 finish 每次重写、含时间戳 ⇒ 仓内不写死字面 Date**，以实物为准）），
  G0/G1/G2/G3/G4 全 ✅、L2/L4/L5 按口径
W3（finish step5）：.ci-result.json exit_code=0 —— **字面三元组不在仓内抄录**（含时间戳、
  每次 finish 必变，写死即过期并造成「两套读数」）；复算式 = `integrity_hash =
  sha256(f"{timestamp}:libinsane:1.0.10:0")[:16]`、`log_sha256 = sha256sum
  reports/w3-local-ci.log`；**取值以 .ci-result.json 实物为准**，字面三元组写在 PR 正文。
四臂对照读数（`test()` rc=127 定因；notes:30 与 notes:83 的「四臂读数」即指本段，第 1 轮 P2 补）：
  臂A 原样 `meson setup --buildtype release` + `LD_LIBRARY_PATH` 12 个目录全给 ⇒ rc=127
    `Error loading shared library libinsane.so.1: (needed by ./test_libinsane)`、`errno` 为空
  臂B 补全 `LD_LIBRARY_PATH`（构建机/缓存 12 目录逐个补）⇒ 同样 rc=127 ⇒ 非路径漏配
  臂C 把 `.so` 平铺到与可执行同目录 + `LD_LIBRARY_PATH=.` ⇒ 同样 rc=127 ⇒ 非 RPATH/搜索路径
  臂D 与臂A 同，但先 `binary-sign-tool -selfSign 1` 重签 `.so` ⇒ **rc=0** ⇒ 唯一变量 = 签名有效性
  ⇒ OHOS 加载器拒收签名失效的 `.so`（`.codesign` 段"在但无效"），处置见 §遇到的问题第 1 条
消费者测试：`== assertions: 14 passed, 0 failed ==`（reports/conan-create.log:270）
  ——14 条运行期断言（7 条 lis_compare 按 util.h 相等性语义 + lis_getenv×2 + strdup/lis_free +
  lis_get_version + lis_api_sane vtable + get_device 返 lis_error），另 12 处 `_Static_assert`（实测 12 条：第 29/31/33/35/37/39/41/43/45/48/52/54 行；第 6 行是注释、不计）
  为编译期 ABI 钉死、不计入
上游测试（W3 之外单独真跑 `meson test -C build-release --print-errorlogs`；**日志留在本机 `~/qzy/主理-74-libinsane-1.0.10/archives/l/libinsane/1.0.10/reports/upstream-meson-test.log`**、按 `.gitignore:96` 不入 PR，**关键读数已逐条内嵌本节**）：
  总 24 → **Ok 22 / Fail 1 / Timeout 1**
  · Fail = tests_sane：`WARNING - Suite initialization failed for 'Sane'.`，stderr 第一条真实错误
    `Tests init: Failed to get test device: 0x60000003, The device is offline. …`
    ⇒ **能力面**（无扫描仪、拿不到 SANE 测试设备），非代码缺陷；消费者侧已按真实失败形态断言
  · Timeout = tests_workaround_dedicated_process：`tests_dedicated_process_scan() ...passed`
    后进程不退出，30.06s 被 SIGTERM ⇒ 用例通过、收尾挂住，如实申报
  ⛔ 未删用例、未缩分母、未 `|| true`；因上两例接进 `build()` 会使 `conan create` 恒红，
     故 `upstream_test_in_build: false`（理由同上，逐条披露）
```

## 交付物
| 文件 | 说明 |
|------|------|
| `bin/` | 无（纯库包） |
| `lib/libinsane.so.1.0.10` + SONAME 别名 | 核心 C API |
| `lib/libinsane_gobject.so.1.0.10` + SONAME 别名 | GObject 包装 |
| `include/libinsane/**`、`include/libinsane-gobject/**` | 头文件 |
| `lib/pkgconfig/libinsane*.pc` | pkg-config |
| `licenses/LICENSE` | 上游许可证 |

## 注意事项（交付口径，⛔ 勿外推）
1. **签名必须在 `package()` 里做**：本包 `.so` 装出后 `.codesign` 已失效，不重签则消费者
   `test()` 直接 rc=127（四臂读数见「验证结果」节）。同仓 `glib/2.84.0.2` 的 `_sign_shared_libs()` 是同款处置。
2. **无扫描仪主机上 `tests_sane` 必红**：`get_device` 拿不到设备是预期形态，消费者断言的是
   "必须返 `lis_error`"，不是"必须找到设备"。
3. **`glib` 版本是图约束**：升到 2.88.x 会与 sane-backends 的 zlib 图冲突，别随手放开。
4. `introspection`/`gtk_doc` 关闭 ⇒ **无 typelib、无 Vala binding、无 gtk-doc HTML**；C 库、头、`.pc` 完整。

## 路径 B 声明（3+2）
- 适配路径：路径 A（Meson 配方 + 依赖图钉版 + 子项目开关裁剪）+ 路径 B（知识库扩展，B判定=create）
- 使用知识库（**第 1 轮 P2/P3 合并更正：三处编号原先不同源，现分三段写清**）：
  ①**本包申报的知识条目 = `E135`**（OHOS 动态链接器要求 `.so` 必须签名、签名失效即拒载），
    载于 `manifest.yaml:45` `knowledge_gained: - "E135"` 与成对草稿 `E135-kv`，**B 判定与正文以它为准**；
  ②随包 `reports/conan-verify-report.md:9` 的 `**Knowledge hit**: E490` 是**框架按其内部检索自填的字段**，
    且同一文件 `:11` 自标 `⚠️ 已知风险 E490 未在配方中处理` ⇒ **与本包处置无对应关系，不作申报依据**；
  ③原 notes 写的 **E444**（`.init_array` 构造器与类型系统初始化）**与本机制无关**，属早期误并列，**现撤**；
    原文中并列提及处一律改指 E135。重签处置照 `archives/g/glib/2.84.0.2/conanfile.py` 的 `_sign_shared_libs()`；
  重签处置照 glib/2.84.0.2 `_sign_shared_libs()` 与全仓 1147 个配方先例（实测：`grep -rl binary-sign-tool archives/*/*/*/conanfile.py | wc -l`）；`lis_compare` 语义以
  `include/libinsane/util.h:55-59` 原文为准
- 知识库扩展：**B判定=create** —— 查重（`knowledge/graph|doc|drafts` 对 `remove-section .codesign` /
  `Error loading shared library` / `selfSign` / `re-sign` 全量 grep）命中 E077/E135/E452/E517/E481/E489，
  但**症状签名与适用面均不同**（E077=strip 后 exec `Operation not permitted` rc=126；E135=签名缺失且点名
  libintl.so.8、修法是手动 `sign-elf`；E452=消费侧**任务私有目录里的副本**；E517=`dlopen` 报
  `Permission denied`）⇒ 属 §6.2「组合型知识不判重」：新增路径是"**生产者在 `package()` 里对自己刚
  install 出的 .so 重签**（`.codesign` 在、路径与 LD_LIBRARY_PATH 全对、**errno 为空**仍 rc=127）"，
  成对草稿待随本 PR 的 `knowledge/drafts/` 落盘
- 关联 Issue：#3549（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3549 ）

---

**编译结束**: 2026-09-28 12:51
**最终状态**: built
