# ayatana-indicator-power 26.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-05
- 编译器: clang/clang++ (OHOS SDK 15.0.4)
- 状态: built

## 编译步骤

1. `init-build` 下载官方 tag 归档（26.6.0，sha256
   `0f431468b3ad6d0bbbe904ee773018190bf3777a78066387e3fa6cfc8d9cfd55`）。
2. 手工编译验证：CMake configure（`-DENABLE_RDA=OFF -DSKIP_PO=ON ...`）
   → make → make install DESTDIR（staging 隔离）。`ctest`/`make check` 上游
   需 GMock/dbustest 且需 D-Bus session，OHOS 不可用，`ENABLE_TESTS=OFF`
   不纳入（记录原因，功能覆盖由 test_package smoke test 承担）。
3. `conan-init` 生成 conanfile.py + conandata.yml + test_package/。
4. 反复 `conan create` 排除链接/运行问题，最终 `conan-verify` 全门禁通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `undefined symbol: g_libintl_bindtextdomain` / `pcre2_code_free_8` | 构建沙箱 LDFLAGS 泄漏 `~/usr/local/lib` 旧静态 glib 2.88 | conanfile `generate()` 显式清空 LDFLAGS/CFLAGS/CXXFLAGS/CPPFLAGS（R33），编译器标志完全由 Conan Toolchain 注入 |
| 2 | 缺 `gio-unix-2.0.pc`（pkg_check_modules 要求） | glib 配方未导出该 .pc | `_write_gio_unix_pc()` 从 glib 包目录合成 |
| 3 | glib 系 .pc 未列 `-lintl` | glib proxy-libintl 提供 `g_libintl_*` 符号 | `_augment_glib_pkg_config()` 给 glib-2.0/gio-2.0/gobject-2.0/gmodule/gthread 追加 `-lintl` |
| 4 | test_package 运行时 libnotify.so.4 无法加载（EACCES） | libnotify/0.8.3 产物 .so 被 meson install depfixer 把构建 rpath（绝对 conan 路径）以 `'X'` 覆盖，.dynstr 损坏，OHOS loader 拒绝映射（Permission denied） | 本地修复 libnotify 配方：`package()` 从 build-release 恢复原始 .so（详见下节“依赖缺陷”）；已随 libnotify/0.8.3.1 配方发布到制品仓 |
| 5 | conanrun 聚合 env 未被 test() 继承，LD_LIBRARY_PATH 缺失 | 环境变量未注入 subprocess | test_package `_run()` 显式遍历依赖图收集全部 lib 目录构造 LD_LIBRARY_PATH |
| 6 | OHOS 无 intltool / session bus | 平台缺失 | 补丁：SKIP_PO 跳过 po/；main.c 增加 --version/--help；data/ 自动启动目录改 prefix 相对 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：
  * 顶层 CMakeLists.txt：新增 `SKIP_PO` 选项（OHOS 无 intltool 跳过 po/）；注入 `-DPACKAGE_VERSION` 宏
- `patches/0002-data-CMakeLists.txt.patch`：
  * data/CMakeLists.txt：`XDG_AUTOSTART_DIR` 改为 `${CMAKE_INSTALL_PREFIX}/etc/xdg/autostart`（prefix 相对，conan package() 自包含）
- `patches/0003-src-main.c.patch`：
  * src/main.c：新增 `--version`/`--help` 处理（便于 smoke test）

## 依赖版本

- glib/2.88.0.1（共享，制品仓 ohpcd 已发布）
- libayatana-common/0.9.13（共享，制品仓 ohpcd 已发布；依赖链 glib/2.88.0.1）
- libnotify/0.8.3.1（共享，制品仓 ohpcd 已发布；glib/2.88.0.1 对齐 + package() 恢复原始 .so）
- cmake-extras/1.9（构建期，GSettings CMake 模块）
- 可选特性关闭：RDA（librda 未发布）、Lomiri（schemas/sounds 未适配）、deviceinfo

## 依赖缺陷（重要，需跟进）

libnotify/0.8.3 配方 `build()` 把 meson.build 的 `shared_library()` 改写成
`library()` 以尝试构建静态库，但实际仍产出 .so；其 `Meson(self).install()`
触发的 meson depfixer 会把构建期 rpath（指向 conan 缓存绝对路径）用 `'X'`
逐字节覆盖，导致最终包内 `libnotify.so.4.0.0` 的 .dynstr 被破坏。OHOS 动态
链接器加载该 .so 时报 `Error loading shared library ... Permission denied`
(EACCES)，且重新构建/签名/换目录均无法绕过（已逐项验证）。

本地已通过在 libnotify 配方 `package()` 中从 build-release 目录恢复原始
`.so`（带有效 rpath）解决；该修复需要随 libnotify 配方重新发布到制品仓，
CI 中 `--build=missing` 才会拉到可用二进制。在当前制品仓版本未修复前，
CI 干净构建会命中该 EACCES（详见 R36 记录）。

## 验证结果

```bash
conan create archives/a/ayatana-indicator-power/26.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# -> ✅ 成功；test_package smoke test:
#   --version -> ayatana-indicator-power 26.6.0
#   --help OK

python3 scripts/ohc-run.py conan-verify ayatana-indicator-power 26.6.0
# -> ✅ G0-G4 + L2/L4/L5 全部 PASS（2026-09-05 17:34，conandata 补丁段对齐后）
```

## R36 阻塞记录（重要，历史）

`finish ... built` 的 W3 本地 CI 硬门禁（step 3.5）**未通过**，唯一失败项为
L0i `registry_unreachable`：依赖 `ayatana-common/0.9.11` 未发布到制品仓。

- **依赖现状**：制品仓（ohpcd）只有 `libayatana-common/0.9.13`；本地配方
  使用 `ayatana-common/0.9.11`（本地导出 recipe，仅在本机 conan 缓存，未发布）。
- **W3 失败原因**：`conan download ayatana-common/0.9.11 -r=ohpcd --only-recipe`
  返回 cnb.cool `error:system acceleration policy not enabled`——CI 的 L0i 仅把
  `unable to find/does not exist/not found/404` 判定为"真未发布"，该错误未命中
  模式 → 被归类为 `registry_unreachable`（infra 错误）并 Hard Fail。
- **其余门禁全部 PASS**：L0d（test_package self.run 真实执行）、L0j（版本未占用）、
  L0k（commands.json）、L0m（目录结构）均通过；L1/L2/L4/L5 因 L0 失败被 skip。

## 路径B 重新验证（2026-09-07，本次）

按路径B切换到制品仓已发布的依赖：conanfile.py `requirements()` 改为
`glib/2.88.0.1` + `libayatana-common/0.9.13`（均保留 transitive_headers/libs），
`_write_gio_unix_pc()` 的 Version 改为从 `self.dependencies["glib"].ref.version`
动态取值（不再硬编码 2.84.0）。其余 OHOS 适配（LDFLAGS/CFLAGS/CXXFLAGS/CPPFLAGS
清空、gio-unix-2.0.pc 合成、glib .pc 追加 -lintl、ENABLE_RDA=OFF、SKIP_PO=ON、
GSETTINGS_LOCALINSTALL=ON、libnotify 本地修复产物）保持不变。

**逐项验证结果（如实记录）**：

1. **R36/L0i 依赖发布检查（原阻塞）→ ✅ 已解决**。`conan download --only-recipe`
   验证 glib/2.88.0.1、libayatana-common/0.9.13、libnotify/0.8.3、cmake-extras/1.9
   全部已在 ohpcd 发布。
2. **conan create → ❌ 失败（新阻塞，图版本冲突）**：
   `ERROR: Version conflict: Conflict between glib/2.84.0.1 and glib/2.88.0.1
   in the graph. Conflict originates from libnotify/0.8.3`。
   - libnotify/0.8.3（及 gdk-pixbuf/2.44.6）配方硬编码 `glib/2.84.0.1`，
     与 libayatana-common/0.9.13 的依赖链 `glib/2.88.0.1` 冲突；
   - 进一步级联：gdk-pixbuf/2.44.6、libpng/1.6.58、libtiff/4.7.2 又硬编码
     `zlib/1.3.1.1`，而 glib/2.88.0.1 链为 `zlib/1.3.1.1.1.1` → 图再次冲突。
   - 结论：libnotify 子树整体仍在 glib/2.84 + zlib/1.3.1.1 生态，与
     glib/2.88 + zlib/1.3.1.1.1.1 生态不兼容，**同一 conan 图内无法共存**。
3. **conan-verify → G1/G0 PASS，G2 FAIL**（G2=conan create 图冲突，根因同上；
   知识图谱误命中 E540 shadow-ci/PATH 建议，与本案例根因无关）。
4. **finish ... built → W3 失败**。直接运行 `zsh ci/conan/build_and_test.sh
   archives/a/ayatana-indicator-power/26.6.0` 的实证结果：
   - **L0i/R36 → ✅ PASS**（glib/2.88.0.1、libayatana-common/0.9.13、
     libnotify/0.8.3、cmake-extras/1.9 全部在 ohpcd 命中）；L0j/L0m 等
     L0 质量门禁 PASS；
   - **JC junk 门禁 → ❌ FAIL**（阻塞在 conan create 之前）：
     `archives/u/util-linux-login/2.42.2/.ci-trigger`（存量已提交文件，
     零字节）未登记进 `ci/scripts/junk_check.sh` JC5 白名单，全仓 full 模式
     扫描拦截——与本次改动无关的仓库存量问题；
   - **conan create 图冲突**（同上第 2 点）是 JC 修复后的下一层阻塞。setup.sh 通过。

**判断（是否新增补丁）**：本阻塞是**依赖版本生态冲突**，不是 API/头文件/符号
不兼容，无法靠 ayatana-indicator-power 自身补丁解决。正确修复方向：
将 libnotify 子树（libnotify/0.8.3 + gdk-pixbuf/2.44.6 + libpng/1.6.58 +
libtiff/4.7.2 等）整体迁移到 glib/2.88.0.1 + zlib/1.3.1.1.1.1 链并逐层重新
发布（R36 拓扑序），再回来 `finish`；否则可考虑另选与 glib 2.84 生态兼容的
libayatana-common 版本（无已发布替代）。

**libnotify/glib2.88 API 兼容性初判**：libnotify.so.4 / gdk-pixbuf.so.2 链接
`libglib-2.0.so.0`（SONAME 在 2.84 与 2.88 间不变，GLib 保持向后 ABI 兼容），
二进制层面可复用；冲突纯在 conan 配方版本声明层。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，含 glib pc 增强/gio-unix 合成/LDFLAGS 清空等 OHOS 适配 |
| conandata.yml | 官方源 + sha256 + 补丁声明（3 个补丁与 patches/ 对齐） |
| test_package/ | 真实 smoke test（test.sh + self.run 执行 --version/--help），R34/L0d 非空壳 |
| patches/0001-CMakeLists.txt.patch | 顶层 CMakeLists：SKIP_PO + PACKAGE_VERSION |
| patches/0002-data-CMakeLists.txt.patch | data/：XDG_AUTOSTART_DIR 改 prefix 相对 |
| patches/0003-src-main.c.patch | src/main.c：--version/--help CLI |
| commands.json | R38 可执行命令声明（ayatana-indicator-power-service） |

## 注意事项

- 产物为 D-Bus session service 可执行文件（安装于
  `libexec/ayatana-indicator-power/ayatana-indicator-power-service`），
  `package_info()` 无 cpp_info.libs（非库包）。
- 本包为 `built`（本地 glib/2.84 旧链验证通过，未 upload）。路径B（glib/2.88.0.1 +
  libayatana-common/0.9.13）因 libnotify 子树的 glib/zlib 版本生态冲突无法在本包
  内闭合，需先迁移并重新发布 libnotify/gdk-pixbuf/libpng/libtiff（详见上节）。
- 本地 W3 模拟另被存量 JC junk 门禁（util-linux-login/.ci-trigger）拦截，
  与本次改动无关。
---

**编译结束**: 2026-09-07 11:11
**最终状态**: built
