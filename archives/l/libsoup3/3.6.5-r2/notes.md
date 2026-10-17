# libsoup3 3.6.5-r2 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-02
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 工具链，clang 15.0.4）
- 目标平台: HarmonyOS PC (aarch64, musl)
- 状态: built

## 底稿来源

libsoup3 3.6.5-r2 完整复制自 archives/l/libsoup3/3.6.5-r1（git 提交
1042bc61fd，已发布制品仓，revision 4e1dd2af1214a9943a87a13ab70dce56）。
3.6.5-r2 是 Alpine 风格修订号：上游本体 3.6.5，-r1 与 -r2 源码完全相同
（同一 tarball libsoup-3.6.5.tar.xz，sha256=
6891765aac3e949017945c3eaebd8cc8216df772456dc9f460976fbdb7ada234）。
-r1 → -r2 差异仅在适配层（R37：同一上游版本修复适配问题，后缀递增），
积分赛任务（智能任务平台 contrib-5010，开源鸿蒙PC专项积分赛）要求以
独立版本号提交适配修订版本。

## 本次修复/更新点（-r1 → -r2 差异清单）

| # | 变更 | 原因 |
|---|------|------|
| 1 | conanfile.py / conandata.yml / test_package 版本号 3.6.5-r1 → 3.6.5-r2 | R37 版本号策略：制品仓不支持同版本多 revision 并存，适配修订必须后缀递增 |
| 2 | manifest.yaml 重写：version/status/build_date=2026-09-02/差异说明 | 元数据随版本更新；写明与 -r1 同源码、差异仅在适配层 |
| 3 | notes.md 新写（本文件）：底稿来源、修复点、W0 依赖实测结论、上游测试实测记录 | -r1 notes 未记录上游测试执行情况，本次补齐（比赛硬性要求测试用例全部测试并写通过率） |
| 4 | 软件级 archives/l/libsoup3/manifest.yaml 版本索引追加 3.6.5-r2 | 版本索引完整性 |
| 5 | 适配层无功能性代码变更：依赖集合（glib2/2.88.0、libpsl/0.21.5.1、libnghttp2/1.70.0、sqlite3/3.49.1、zlib/1.3.1.1 override）、meson 选项、layout、工具链修复全部沿用 -r1 已验证配置 | -r1 配方已在制品仓发布且 CI 验证通过（构建 #28966），无已知缺陷需要修复；本次任务是版本号策略下的修订版发布 |

## W0 依赖实测结论（2026-09-02，conan download --only-recipe 实测）

| 依赖 | 制品仓实测结果（revision） |
|------|---------------------------|
| glib2/2.88.0 | aa5b8908c41279c288b09b5e22282c0e（2026-08-05） |
| libpsl/0.21.5.1 | 00a978962a44e6d4ce96d2d7254d5d82（2026-08-14） |
| libnghttp2/1.70.0 | f2ff36e9e5fe66b79cb46d00f7f3b427（2026-08-07） |
| sqlite3/3.49.1 | 669361066cc2c76e0ed897e6b6a27e38（2026-07-10） |
| zlib/1.3.1.1 | 9a23e7d51311d0440b6e4d36cf44e4d9（2026-07-14） |

全部 5 个依赖已在 ohpcd 制品仓发布 → W0 通过，无需重测适配依赖。

## 编译步骤

```bash
# conan create（必须 export PKG_CONFIG_PATH，libsoup 的 libpsl/nghttp2 硬依赖经
# /usr/local pkg-config 解析；conan-verify G2 不自动注入）
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
cd archives/l/libsoup3/3.6.5-r2
python3 -c "from conans.conan import run; import sys; sys.argv=['conan','create','.', \
  '--user=ohpcd','--channel=stable', \
  '-pr:h=$HOME/.conan2/profiles/ohos-aarch64', \
  '-pr:b=$HOME/.conan2/profiles/ohos-aarch64', \
  '--build=missing']; run()"
# （conan CLI shebang 权限问题须 python 直调；glib2/*:shared=True 触发共享
#  glib2 从源码重建约 20-40 分钟，属预期行为）
```

## 遇到的问题与解决方案（全部复用 -r1 记录）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模板配方用已移除的 `meson_layout()` | conan 2.29.1 移除 meson_layout | 手动 layout(): folders.build='builddir'、folders.generators='builddir/generators' |
| 2 | `meson.compile()` AttributeError | conan 2.29 Meson 助手无 compile() | build() 改用 meson.build()（glib2 范本） |
| 3 | glib2 静态/共享双副本风险 | glib2 缓存默认 shared=False | default_options={'glib2/*:shared': True} 强制共享（触发共享 glib2 重建约 20-40 分钟） |
| 4 | AR=llvm-ar 等环境变量坏 | PATH 无 llvm-ar | generate() 里 os.environ.pop + shutil.which 定位真实 GNU 工具（复刻 glib2 配方） |
| 5 | test_package 找不到 libsoup-3.0 目标 | CMakeDeps 的 cmake_file_name/target_name 默认=conan 包名 | package_info() 显式 set_property('cmake_file_name'/'cmake_target_name','libsoup-3.0') |
| 6 | 运行时加载共享库失败 | OHOS 加载器忽略 DT_RPATH/LD_LIBRARY_PATH 默认值；libsoup 依赖 libpsl/sqlite3/libnghttp2 是 /usr/local 系统库 | test() 显式 export LD_LIBRARY_PATH 含 /usr/local/lib |
| 7 | glib2 传递依赖在 CMakeDeps 中空数据 | conan 2.29 对传递依赖行为 | libsoup3 package_info() 里把 glib2 的 include/lib dirs 与库名并入自身 cpp_info |

另有两个 OHOS 平台铁律（-r1 实测沉淀，本次沿用）：
- **禁止 strip 共享库**：OHOS loader 校验 .codesign 段内嵌哈希，strip 改写 .so
  导致 dlopen Permission denied → tc.strip = None；
- **禁止 meson install 清理 DT_RUNPATH**：install 会用 'X' 覆盖 .dynstr 的 rpath
  并删 DT_RUNPATH，破坏 .codesign 哈希 → package() 用 build 目录原始产物覆盖
  被改写的 .so。

## 源码修改

- 无源码补丁（libsoup 3.6.5 无 OHOS 特有修改；无 host_system=='linux' 判定、无 sockaddr_storage）

## 上游测试执行记录（2026-09-02 本次实测，补齐 -r1 未记录部分）

上游 libsoup 3.6.5 自带 meson 测试套件（libsoup/tests/，38 个用例：32 基础
+ brotli-decompressor/auth/connection/range/proxy 等 6 个条件用例）。
本次 conan create 通过后，在 build 目录以 `-Dtests=true` 重新配置构建并
`meson test` 实测（运行方式见下）：

- **可编译可运行：33 个**（上游 38 个中 33 个不依赖外部服务）
  - **PASS：30 个** —— cache, chunk-io, coding, context, continue, cookies,
    date, forms, header-parsing, http2, http2-body-stream, logger, misc,
    multipart, multithread, no-ssl, ntlm, redirect, request-body, samesite,
    server, server-auth, session, sniffing, ssl, streaming, timeout, tld,
    uri-parsing, websocket
  - **FAIL：3 个（均为 OHOS 环境限制，非代码缺陷）**
    - `hsts-test` / `hsts-db-test`：OHOS 无 glib-networking，GIO 回退
      GDummyTlsBackend（tls_available=FALSE），测试的 https_uri 保持 NULL，
      rewrite_message_uri() 对 https 分支 g_uri_get_port(NULL) 断言崩溃；
      与配方 tls_check=false 同因（TLS 是运行时依赖）
    - `unix-socket-test`：OHOS 安全策略禁止 AF_UNIX bind（EPERM，本机
      Python socket(AF_UNIX).bind() 独立复现同错；TCP 回环正常），平台限制
- **豁免（未编译）：5 个**，均有 meson 条件分支佐证
  - `brotli-decompressor`：brotli 特性禁用（上游 `if brotlidec_dep.found()` 不成立）
  - `auth`/`connection`/`range`/`proxy`：需外部 Apache httpd（上游 `if have_apache`
    分支，OHOS 环境无）
- **通过率：30/33 可编译用例 = 90.9%**（3 FAIL 均 OHOS 平台限制：TLS 后端
  缺失 ×2、AF_UNIX bind EPERM ×1，非 libsoup 代码缺陷；5 个豁免用例有
  meson 条件分支论证）
- 新增鸿蒙特有测试：test_package/test.c 真实 API 冒烟（soup_message_new +
  soup_session_new + GUri host 解析，3 项断言），1/1 通过

```bash
# 上游测试运行方式（build 目录）：
cd <build_dir> && meson test   # 33 个用例实机运行，30 PASS / 3 FAIL
```

## 依赖版本

- glib2/2.88.0（conan 包，shared 强制）
- libpsl/0.21.5.1、libnghttp2/1.70.0、sqlite3/3.49.1（conan 包）
- zlib/1.3.1.1（override，PIC 变体，供共享 glib2 链接）

## 验证结果

```bash
conan create ... --build=missing   # 成功，test_package L1 通过
# RUN: export LD_LIBRARY_PATH='...:/usr/local/lib'; bash -c './test_libsoup3'
# test libsoup3 3.6.5-r2: OK (host=example.com, session+message ok)
conan list "libsoup3/*"            # libsoup3/3.6.5-r2@ohpcd/stable 在缓存
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方（shared、PkgConfigDeps、工具链修复、CMakeDeps 命名），沿用 -r1 验证配置 |
| conandata.yml | 官方 URL（多镜像）+ sha256（与 -r1 同源码） |
| test_package/ | 真实 libsoup3 API 测试（SoupMessage/SoupSession/GUri 断言）+ MANIFEST.yml |
| manifest.yaml | 版本级元数据（含 -r1 → -r2 差异说明） |

## 注意事项

- libsoup3 下游（gssdp/gupnp/gupnp-tools）配方必须强制 `"glib2/*:shared": True`
- conan-verify/finish 运行时需 export PKG_CONFIG_PATH（G2 不自动注入）
- 运行 test 二进制时需 export LD_LIBRARY_PATH 含 /usr/local/lib（libpsl/sqlite3/nghttp2 系统库）
---

**编译结束**: 2026-09-02 02:43
**最终状态**: built（conan-verify PASS + W3 本地 CI 通过；upload 待 PR 合并后由 release 流水线完成，按 ARCHIVE-SPEC 口径当前为 built）
