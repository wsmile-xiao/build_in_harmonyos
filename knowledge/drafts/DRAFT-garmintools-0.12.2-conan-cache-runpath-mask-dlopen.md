# DRAFT-garmintools-0.12.2-conan-cache-runpath-mask-dlopen — Conan create 安装产物 .so 的 DT_RUNPATH 被 X 掩码 → musl dlopen Permission denied，配方静态化 + 显式 includedirs 双保险

> **Contributor**: junshi_liu | **Status**: DRAFT | **Updated**: 2026-09-21
> **Severity**: warning (2) | **Category**: conan / meson / hmdfs / linking / runtime / packaging
> **Audience**: 所有在 OHOS 上用 Conan 2 + meson 适配、产物同时含 .so 与 CLI 工具的配方作者

## 触发（trigger）

garmintools 0.12.2 OHOS aarch64 适配（meson 构建，依赖 libusb/1.0.27）：

- conan-verify G2 `conan create` 主包构建与打包全部成功，test_package 运行时却报
  `Error loading shared library libgarmintools.so.6: Permission denied` + `symbol not found`
- 同一构建的 build-tree 产物 `b/build-release/src/libgarmintools.so.6.2.0` 用 dlopen 探针可正常加载，
  cache 安装产物 `p/lib/libgarmintools.so.6.2.0`（内容经 `cat`/`cp` 拷贝到任意目录）一律
  `dlopen FAIL: Permission denied`

## 症状（symptom）

```
garmintools/0.12.2@ohpcd/stable (test package): RUN: ./test_garmintools
Error loading shared library libgarmintools.so.6: (needed by ./test_garmintools)
Error relocating ./test_garmintools: garmin_lpid: symbol not found
ERROR: garmintools/0.12.2@ohpcd/stable (test package): Error in test() method
```

- test_package 编译链接正常（`-I`、`-L`、`-l` 均正确），失败仅发生在运行时 dlopen
- 现场编译的 mini .so（同目录、同权限 770）dlopen 正常 → 排除目录/权限因素
- 说明：本设备（HMDFS + musl aarch64 loader）对 cache 安装产物的加载限制是设备语义，
  与 CI 干净环境行为可能不同；但配方级静态化在任何环境都稳。

## 根因（root cause）

1. **主根因（本候选新增差异）**：`conan create` 把构建产物安装进 cache `p/lib` 时，
   对 .so 的 `DT_RUNPATH` 绝对路径字符串做了 X 掩码 scrub（等长 `X` 替换，.dynstr 中
   runpath 字符串变成 `XXXXXXXXXXXXXXXX...`，且 p/lib 产物不再有 DT_RUNPATH 动态条目）。
   掩码后的安装产物在本 OHOS 设备 musl loader 触发 dlopen EACCES（Permission denied），
   而 build-tree 产物（runpath 完整）可正常加载。
2. **次根因**：`package_type=application` 时 cpp_info 默认 includedirs 为空，
   CMakeDeps 生成 `xxx_INCLUDE_DIRS_RELEASE` 为空 → test_package 编译报头文件 not found
   （本案例用显式 `includedirs=["include"]` 修复）。
3. 附带：codeload `/tar.gz/refs/tags/<tag>` URL 末段无 `.tar.gz` 扩展名 → conan get()
   误选 zip 解码器报 BadZipFile（既有 E276/E392/E483 已覆盖，配方用显式 filename 修复）。

## 证据（evidence）

- 差分定位：`cmp -l p/lib/libgarmintools.so.6.2.0 b/build-release/src/libgarmintools.so.6.2.0`
  → 160 字节差异；`dd bs=1 skip=8016 | od -c` 显示 p/lib 侧为 `XXXXXXXXXXXXXXXX...`，
  b/src 侧为 `/storage/Users/currentUser/.conan2/p/libus04e54d4f229a5/p/lib`；
  `llvm-readelf -d` 显示 b/src 有 `RUNPATH` 条目，p/lib 无。
- dlopen 探针（clang 编译，RTLD_NOW）：p/lib 副本 → Permission denied；b/src 副本 → OK
  （`garmin_lpid=0x... garmin_load=0x...`）；mini.so 同目录 → OK。
- 掩码复现实验：把 b/src 的 runpath 字符串同样 X 掩码后 dlopen → 复现 Permission denied，
  证明掩码字符串是触发因素。
- 修复后：conan-verify G0-G4 全过；test_package 静态链接，5/5 断言 PASS
  （garmin_lpid/garmin_gpid 协议映射 + garmin_load 错误路径，验证真实公开 API）。

## 方案（rec_approach）：conan-recipe-static-plus-explicit-includes

1. **配方静态化**：`build()` 中 meson setup 加 `-Ddefault_library=static`，
   CLI 工具与 test_package 消费者测试静态链接 libgarmintools.a，彻底规避运行时
   dlopen 安装产物（同时规避 HMDFS 符号链接同族问题，呼应 E073 configure-static-only）。
2. **显式 includedirs**：`package_info()` 显式 `self.cpp_info.includedirs=["include"]`，
   规避 application 默认空 includedirs 导致 CMakeDeps 空 INCLUDE_DIRS。
3. **显式 filename**（既有知识复现）：conandata.yml `sources.filename="<name>-<ver>.tar.gz"`。
4. 定位方法：优先用 `cmp -l` + `readelf -d` + `dd` 差分确认"安装产物被 scrub 而非损坏"，
   避免误判为平台无解而止损。

## 适用边界 / 反例

- 适用：OHOS + Conan 2 + meson/autotools/cmake 混合包（.so + CLI），test_package 需要
  运行时 dlopen 或编译引用头文件的场景；或设备 loader 对 cache 产物加载受限的环境。
- 反例：纯库无 CLI、且依赖库运行时可经 LD_LIBRARY_PATH 找到时，不一定需要静态化
  （可先试 rpath/LD_LIBRARY_PATH 注入）；CI 干净环境通常无此掩码问题，本地 W3 与
  CI 行为差异需在 notes/PR 中说明。
- 静态化副作用：产物只有 .a，若下游需要动态链接 .so 需权衡（本案例 CLI 工具生态
  可接受静态）。

## 查重（dedup 摘要）

- 完整重复：无（E073 符号链接/E488 owner 权限/E212 hmmac 标签/E537 DT_NEEDED 绝对路径
  均相邻但根因/方案不同；本候选差异 = DT_RUNPATH 字符串 X 掩码 + 差分定位法 + 配方级
  静态化+显式 includedirs 组合）。
- 关系：similar_to=E073,E488,E212,E537,E276,E392,E483；caused_by=无；prerequisite_of=无；
  conflicts_with=无。
- 七轴与台账：archives/g/garmintools/0.12.2/reports/knowledge-candidate-ledger.md
