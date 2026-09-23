# libcacard 2.8.1 适配笔记

## 编译环境

- 构建系统：meson（上游官方构建路径；包内自带 autotools `configure`，本次未使用）
- 适配日期：2026-09-13
- 编译器：clang（真机 /data/service/hnp/bin/clang，由 profile 注入）
- 状态：built（待真机预检回填实测结果）

## 上游源码审计

- 上游仓库：https://gitlab.freedesktop.org/spice/libcacard
- 发布包：https://www.spice-space.org/download/libcacard/libcacard-2.8.1.tar.xz
- 标签：v2.8.1；许可证：LGPL-2.1-or-later
- sha256（已在本机用 certutil 复核，与 Solus/Void 打包元数据一致）：
  `fbbf4de8cb7db5bdff5ecb672ff0dbe6939fb9f344b900d51ba6295329a332e7`
- meson.build 关键事实：
  - `dependency('glib-2.0', version: '>= 2.32')`，
    `dependency('nss', version: '>= 3.12.8')`，
    `dependency('libpcsclite', required: get_option('pcsc'))`
  - 选项：`pcsc`（feature，默认 auto）、`disable_tests`（boolean，默认 false）
  - `library('cacard', ...)` 生成 libcacard.so，头文件装到 `include/cacard/`，
    pkg-config filebase 为 `libcacard`，`vscclient` 工具默认不安装
    （`executable()` 无 `install: true`），因此本包为纯库，无需 commands.json

## 上游测试盘点（来源：tests/meson.build、fuzz/meson.build、tests/*.c）

无条件注册（ disable_tests=false 即构建运行，共 6 个 meson 测试程序）：

| 程序 | 源码 | gtest 用例数 | 说明 |
|------|------|-------------|------|
| libcacard | tests/libcacard.c + common.c | 26 个 `g_test_add_func` | 完整软卡仿真（用自带 tests/db NSS 库） |
| simpletlv | tests/simpletlv.c | 9 个 | SimpleTLV 纯单元测试，无硬件依赖 |
| initialize | tests/initialize.c | 2 个 | 初始化错误路径 |
| fuzz_xfer | fuzz/fuzz_xfer.c | 1（corpus 驱动） | 随附 corpus |
| fuzz_simpletlv | fuzz/fuzz_simpletlv.c | 1（corpus 驱动） | 随附 corpus |
| fuzz_options | fuzz/fuzz_options.c | 1（corpus 驱动） | 随附 corpus |

条件注册（需 pkcs11-tool、p11tool、modutil、openssl、softhsm2-util 五者齐备，
真机大概率缺失，届时 meson 自动不注册，不计为跳过）：

| 程序 | gtest 用例数 | 说明 |
|------|-------------|------|
| hwtests | 13 个 | 需真实智能卡/softhsm 令牌 |
| hwtests_no_raw | 同上（不同 softhsm 配置） | 同上 |

结论：上游存在测试，`disable_tests=false` 保持开启，`meson test` 在
`build()` 内真实执行；hwtests 缺外部工具时属"未注册"而非"跳过"。

## 编译步骤（真机 conan create 实际执行）

1. `get()` 解包官方 tar.xz（strip_root）
2. `PkgConfigDeps` 生成 glib-2.0/nss 的 .pc；`MesonToolchain` 配置
   `wrap_mode=nodownload`、`default_library` 跟随 shared 选项、
   `pcsc=disabled`、`disable_tests=false`
3. native file 注入 ar/ranlib 全路径（llvm-ar 不在 PATH，照搬 pcsc-lite 做法）
4. `meson setup/compile`；OHOS 上先签名测试 ELF 再 `meson test`
   （照搬 libslirp 顺序），解析 meson 输出后打印
   `HMBS_UPSTREAM_TEST_RESULT` 标记，失败即抛异常中断构建
5. `meson install` 后重签 `lib/libcacard.so*`（rpath 重写导致自签失效，
   照搬 pcsc-lite `_sign_elf`）

## 依赖版本（W0）

- glib/2.84.0（2026-09-14 起；与已合入 libslirp/4.9.3 完全相同的成功组合：共享消费者 + 静态 flat glib；llvm-ar 缺失时优雅降级用 PATH 的 binutils ar；transitive_headers/libs；上游要求仅 glib>=2.32，兼容；碰撞钉子见 #12）
- nss/3.118.1 shared（本仓状态 published；静态 .a 仅为聚合存根，必须用 shared 的 libnss3.so 等，见 #16）
- 有意不依赖 pcsc-lite：`pcsc=disabled`，避免引入 libusb/USB 守护进程依赖
- 制品仓存在性最终由真机 `conan download --only-recipe` 复核

## test_package 设计

- `test_cacard.c`（6 个断言，全部调用真实 API，无需 NSS 初始化与硬件）：
  1. `vcard_emul_options("use_hw=no")` 返回非空
  2. `vcard_emul_options("hw_type=CAC")` 返回非空
  3. `vcard_emul_type_from_string("CAC") == VCARD_EMUL_CAC`
  4. `vcard_emul_type_from_string("cac") == VCARD_EMUL_CAC`（大小写不敏感，
     见 vcard_emul_type.c 的 strcasecmp）
  5. `vcard_emul_type_from_string("BOGUS") == VCARD_EMUL_NONE`
  6. `vcard_emul_options("bogus_garbage_xyz") == NULL`（未知规约被拒绝）
- `test()` 运行真实编译出的二进制，通过后打印
  `HMBS_TEST_PACKAGE_RESULT`（discovered=6/passedCount=6）；失败则标
  `passed:false` 后抛异常
- OHOS 上消费者 ELF 同样先重签再执行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出 main 报 libXext/libxext 大小写冲突致工作树恒脏 | 上游同时存在 `archives/l/libXext` 与 `archives/l/libxext`，Windows 不区分大小写 | `update-index --assume-unchanged` 屏蔽 4 个文件，本 PR 不触碰该路径 |
| 2 | 全量 checkout 超时 | 仓内配方数量大，Windows 落盘慢 | 稀疏检出仅含 docs/knowledge/templates/.gitcode/ci/scripts/archives/l |
| 3 | gitlab.freedesktop.org 被 Anubis 拦截 | 反爬 | 改用 spice-space.org 官方下载站 + cgit/发行列表交叉验证 |
| 4 | 真机预检 compile 阶段 bzip2/1.0.8 构建失败：CMake 报 `System is unknown to cmake`（HarmonyOS）且 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 配置中断，伴随只读 /tmp 报错 | 依赖链为 libcacard -> glib -> pcre2（默认 `with_bzip2=True`/`build_pcre2grep=True`）-> bzip2；pcre2grep 是唯一消费 bzip2 的组件，glib 实际只链接 pcre2-8 库；conancenter bzip2 的 CMakeToolchain 在 OHOS 上无 HarmonyOS 平台支持 | 本配方 `configure()` 置 `pcre2:build_pcre2grep=False`，剪掉 bzip2 边（库 ABI 不变）；`build()` 全程套用可写 TMPDIR（优先 HMBS 注入值）；签名后 `chmod` 按 `HMBS_CAP_CHMOD` 做最小容忍 |
| 5 | 真机预检 compile 阶段 conancenter libffi/3.4.4 的 configure 死于 `configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`（exit 127） | profile buildenv 注入的 CONFIG_SHELL 解释器在本机不可用，属依赖构建上下文问题；本配方无法向依赖构建注入环境，只能改图谱选型 | `requirements()` 加 `libffi/3.5.2` override（glib 允许 `>=3.4.4 <4`，libffi C ABI 稳定）：取仓内已 published 且带 configure-hmdfs-umask 补丁的 3.5.2，其 ohpcd 二进制可跳过坏掉的源码构建 |
| 6 | 真机预检 compile 仍停在 pcre2/10.40 本体 CMake 配置（`System is unknown to cmake` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 中断），即使 `pcre2:build_pcre2grep=False` 已生效；伴随只读 /tmp 与 HMBS `[readonly_tmp]` 诊断 | 上轮剪枝只去掉了 pcre2grep→bzip2 子边（证据：失败点从 bzip2/1.0.8 经 libffi 推进到 pcre2 本体），pcre2-8 库自身的 CMake 编译器校验与可选压缩边无关，消费者选项剪枝对此无效；另 `package()` 的 meson install 与 test_package 的 CMake 构建此前未套用可写 TMPDIR，仍可能命中只读 /tmp | 保留 libffi 3.5.2 override 与 grep 剪枝；`package()` 全程套用 TMPDIR；test_package 新增同源 TMPDIR 覆盖并对齐 errno 级 chmod 容忍；`build()` 打印 TMPDIR/能力位诊断行，下一轮日志可直接区分环境与配方失败 |
| 7 | 策略周期3：上轮（#6）仍红在 pcre2/10.40 本体 CMake configure（`System is unknown to cmake` + clang 中断 + 只读/tmp + `[readonly_tmp]`），证明“修依赖构建”路线无效 | 复盘：#4 的 `pcre2:build_pcre2grep=False` 与 #5 的 `libffi/3.5.2 override` 都会改变依赖 package_id，使原本与 libslirp/4.9.3（同依赖 glib/2.84.0，CI #12131 已绿）完全相同的图谱变成新图谱，ohpcd 已发布二进制无法复用，被迫走源码构建，而 pcre2/bzip2/libffi 的 conancenter 源码构建在 OHOS 上本就不可靠；失败点 bzip2→libffi→pcre2 的“推进”正是每次剪枝制造新 package_id 的证据，而非进展 | 本轮换路线：删除两处图谱变更（`configure()` 不再碰 pcre2 选项，`requirements()` 删除 libffi override），使图谱与已验证的 libslirp 链完全一致，优先复用 ohpcd 二进制，避免任何依赖源码重建；本包自身的 TMPDIR 包裹与签名容忍予以保留（不改变 package_id，无害） |
| 8 | 同一指纹第2次：回退图谱后仍红，失败回到 bzip2/1.0.8 CMake configure（`CMakeLists.txt:2 project()` 处 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 中断 + 只读/tmp + `[readonly_tmp]`），且日志明确 `glib/2.84.0: Main binary missing` + 11 种 cppstd 兼容配置均无匹配 | 前次“复用二进制”假设被证伪：SUMMARY 显示 glib/2.84.0 仅“已编译”而 glib/2.88.0 为“已发布”，2.84.0 二进制根本不在 ohpcd，任何基于 2.84.0 的图谱（无论是否剪枝）都必然回退到 conancenter CMake 链，而该链在 OHOS 上系统性不可构建；与 libslirp 历史 CI 的对比亦失效（当时的二进制/环境已不可复现） | 本轮换路线：`requirements()` 由 `glib/2.84.0` 切换到站内已发布的 `glib/2.88.0`（meson，上游要求仅 glib>=2.32，兼容），nss/3.118.1（已发布）保持；`configure()` 继续不碰任何依赖选项；manifest/notes 同步更新 |
| 9 | 同一指纹第3次：glib/2.88.0 下失败跳到 zlib/1.3.1 CMake configure（`CMakeLists.txt:4 project()` 处 `CMAKE_C_COMPILER` 中断 + 只读/tmp + `[readonly_tmp]`），依赖图变为 glib/2.88.0→pcre2/10.45→zlib/1.3.1 且均为 conancenter recipe 修订 | 三轮证据链：bzip2（2.84.0默认）→pcre2（剪枝后）→bzip2（回退后）→zlib（2.88.0），每次只改变首个失败叶子而CMake指纹完全相同；预检同时启用 conancenter+ohpcd（日志显示conancenter优先命中），而CI的setup.sh明确禁用conancenter只用ohpcd（站内pcre2已发布、bzip2已验证均为非CMake构建）；本轮preflight.sh自身亦报只读/tmp，属harness/环境侧条件，叶配方无法向依赖构建注入环境 | 本轮不再做图谱变更（再改版本/选项只是第4次换叶子，属已失败类别的重复）；保持 glib/2.88.0（已发布，满足R36/L0i）；请求后端核验预检与CI的remote配置一致性，或补齐缺失链的站内发布 |
| 10 | 同一指纹第4次：保持 2.88.0 不再有效——其叶子 pcre2/10.45 与 zlib/1.3.1 在 conancenter 同名且预检优先查询 conancenter，conancenter CMake 修订必然抢占配方解析，与二进制是否存在无关；前四轮“找已发布二进制/调选项/上报环境”的共同错误假设是“配方解析已正确、只差二进制”，证据（均为 conancenter recipe 修订 + 本仓同版本实为 Autotools/Makefile 构建）证伪了该假设 | 新路线（remote 竞争规避，非版本碰运气）：`requirements()` 改为 `glib/2.88.3`，其闭包 pcre2/10.47、libffi/3.5.2、zlib/1.3.2、proxy-libintl/0.5 在 conancenter 无对应版本，ohpcd 修订（Autotools/Makefile/meson，均已 OHOS 适配）必然命中；nss/3.118.1（conancenter 无收录）保持；`configure()` 继续不碰传递依赖；manifest/notes 同步 |
| 11 | 同一指纹第5次：#10 的“2.88.3 闭包无碰撞”假设被本轮预检日志证伪——`pcre2/10.47: Downloaded recipe revision 2603045670141223e54d6ba7cce7e2a5` 与 conan.io 中心数据完全一致，且 conan.io 另有 zlib/1.3.2，bzip2 经中心 pcre2 的 with_bzip2 默认边重返依赖图；glib/2.88.3 自身二进制在站内缺失（11 种兼容配置无命中），故 glib 必从源码构建 | 新路线（override 定点覆盖，非顶层换版）：保留 glib/2.88.3（站内配方，OHOS 适配，必重建故改其 package_id 零额外成本）；新增 `pcre2/10.45.1.1 + zlib/1.3.1.1` 两条 `override=True`，把碰撞叶子钉到 conancenter 结构性缺失的站内后缀版本（10.45.1.1 导出 glib 所需 pcre2-8/16/32 组件，已被合入的 libcleri 消费；1.3.1.1 为 Makefile 静态+PIC，已被合入的 libpng/cairo 改指；中心 pcre2 最大仅 10.47、zlib 虽有 1.3.2 但无后缀版本）；libffi/3.5.2（中心最大 3.4.8）与 proxy-libintl/0.5（本轮日志证明仅站内有）无需覆盖；站内 pcre2 无 bzip2 依赖，bzip2 边随之消除 |
| 12 | 同一指纹第6次：#11 的 override 生效（pcre2/10.45.1.1 与 zlib/1.3.1.1 均从 ohpcd 解析，bzip2 离图，glib/2.88.3 源码下载并生成 meson 工具链），但 glib/2.88.3 自身构建死于 `Invalid configuration: target compiler tool 'ar' is not executable: /data/service/hnp/bin/llvm-ar`——其 `_resolve_llvm_tools()` 在 OHOS 下盲取 compiler_dir/llvm-ar 且 build() 硬校验，而本预检机只有 binutils `ar`、无 `llvm-ar`；配方 bug 在依赖侧，本包无法注入 conf/env 修复 | 新路线（换用容错配方，非再调版本数字）：`requirements()` 改回 `glib/2.84.0`——与已合入 libslirp/4.9.3（CI #12131 绿）完全相同的成功组合（共享消费者 + 静态 flat glib + transitive_headers/libs；`package_info.requires` 同步改为 flat 形式 `glib::glib`）；2.84.0 的 ar 处理优雅降级（llvm-ar 缺失则静默跳过注入，meson 用 PATH 的 ar），zlib 为系统预装（无 conan 边）；保留思想、平移钉子：`pcre2/10.40→10.45.1.1`、`libffi/3.4.4→3.5.2` 两条 override（后者在周期 1 已证明可解析；前者与 #11 同据）；上游仅要求 glib>=2.32，2.84.0 兼容 |
| 13 | 第5策略周期：上轮“换容错 glib + 平移钉子”假设被本轮预检证伪——失败点已推进到本包自身 `meson setup`：`Unknown compiler(s): [['/data/service/hnp/bin/clang']]` + `clang --version: [Errno 2] No such file`；依赖侧 override 实际已生效（无 bzip2/pcre2/zlib 失败），再改 requirements 只是重复同类调参（R43 止损）；profile 的 compiler 路径在本预检 worker 上根本不存在，任何图谱变更都无法修复 | 新路线（修本包工具链解析，非改图谱）：`requirements()` 保持 glib/2.84.0 + nss/3.118.1 + pcre2/10.45.1.1 + libffi/3.5.2 不动；`generate()` 新增 `_repair_meson_compilers()`（仅当 ini 内路径缺失时替换：conf→CC/CXX→PATH clang→HNP→SDK llvm glob，native+cross 双文件，逐项日志），`_inject_ar_ranlib()` 扩展到 cross 文件 + PATH 搜索（libslirp 式），`_build_environment()` 透传 CC/CXX + PATH，test_package 同源 CC/CXX 回退；缺失仍保留原错不掩盖 |
| 14 | 同一指纹第2次：上轮编译器修复生效（本轮失败从 `Unknown compiler` 推进到 `Dependency glib-2.0 ... Pkg-config for machine host machine not found`），证明不再是编译器路径问题，而是 meson 在预检 worker 上找不到 pkg-config 二进制；与依赖版本无关，重复改 requirements 属于已失败路线 | 新路线（补 pkg-config 供给，非改图谱/编译器）：`generate()` 新增 `_inject_pkg_config()`（PATH→HNP→/usr 顺序发现，仅缺失时向 native+cross 的 [binaries] 写入绝对 `pkgconfig`，已有条目不覆盖并日志），`_build_environment()` 前置 pkgconfig 目录 + HNP/bin + PKG_CONFIG_PATH(generators_folder)；找不到则保留原错；test_package 不动 |
| 15 | 同一指纹第3次：上轮“本地注入 pkgconfig 条目 + PATH 前置”后仍报同一 `Pkg-config for machine host machine not found`（build() 行号 142→143 证明新代码已同步生效），证伪“worker 上存在可用二进制只缺注入”假设——worker 上根本无 pkg-config/pkgconf 可发现，PATH 注入无米下锅 | 新路线（用 conan 供给工具，非本地路径修补）：新增 `build_requirements()` 声明 `tool_requires("pkgconf/3.0.5")`（本仓 libmrss/0.19.4、libxklavier/5.4 同款正例），由 conan 经 build context 把 pkg-config 带进 PATH；本地 `_inject_pkg_config` 保留作兜底；host requirements 不动 |
| 16 | 真机 compile 链接 `libcacard.so` 报数十个 NSS 未定义符号（`PK11_*`/`CERT_*`/`SECKEY_*`，`ld.lld: error: undefined symbol`，引用自 `vcard_emul_nss.c.o`），而链接行已含 `libnss.a/libssl.a/libsmime.a/libnssutil.a/libsoftokn.a/libfreebl.a/libnssckfw.a/libnssdbm.a/libsqlite.a` | 根因在依赖侧：nss/3.118.1 的 `test_package` 文档明确静态 `.a` 只是聚合存根，真实符号在完全聚合的共享库（`libnss3.so` 等）中，静态直链必然缺符号；本包此前默认拿到静态 NSS。新路线（链共享 NSS，非改顺序/加分组）：`requirements()` 中 `nss/3.118.1` 加 `options={"shared": True}` + `transitive_headers/libs=True`，使 PkgConfigDeps 生成 `-lnss3/-lssl3/...`；`package_info.requires` 同步为 `["glib::glib", "nss::nss"]` 以便消费者经 CMakeDeps/VirtualRunEnv 拿到运行时 NSS；glib/pcre2/libffi 钉子与工具链修补保持不动 |

| 17 | 真机 compile 在 meson [36/36] 成功后死于 signing 门禁 | 本包只认硬编码 /data/service/hnp/bin 三元组；改为 compiler_dir→约定路径→PATH 多路径发现（signer 另认 user.ohos:sign_tool/OHOS_SIGN_TOOL），缺失报错带具体缺谁，命中打印 HMBS sign tools 行；找不到仍抛错不跳过测试 |
| 18 | meson test exit=13 PermissionError fuzz/fuzz_options, discovered=0, HMBS readonly_tmp + CAP_CHMOD=0 | Signed files lost +x: _chmod_if_supported early-returned on CAP_CHMOD=0 and os.replace swapped in 0644 signer inode; hard-coded 7-name walk missed build-tree lib. Fix: always attempt chmod (tolerate EPERM/EACCES/EROFS/ENOTSUP), write signed bytes back into original inode to preserve mode, sign via introspect --tests + walk (known names + libcacard.so* + any X_OK ELF). No test skipped. |
| 19 | evidence incomplete: HMBS_TEST_PACKAGE_RESULT 6/6 present but HMBS_UPSTREAM_TEST_RESULT missing (discovered/executed 0) | build() stdout marker is skipped on `conan create --build=missing` cache hits while test_package still runs. Fix (dual-channel persist + re-emit, ceni/courier-unicode pattern): _run_upstream_tests writes marker JSON to build folder, package() ships it under share/libcacard/, test_package re-emits verbatim every run (incl. cross path); missing file warns only, never fabricates. |

## 验证结果

待真机预检回填（conan create 日志中的 meson test 明细与
test_package 运行输出）。

## 交付物

无（本轮仅工作树，不提交）。

## 注意事项

- `vscclient` 不安装，本包无 bin/ 产物，不建 commands.json
- 若真机发现 hwtests 被注册（如五工具齐备），以实测输出为准更新通过率，
  不得视为失败
- 本地 Windows 无 Python/meson/conan，不在本机运行任何构建验证，
  一切以真机预检为准
