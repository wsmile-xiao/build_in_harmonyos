# libpsml 2.1.0 适配笔记

## 编译环境

- 构建系统：cmake（上游 CMakeLists.txt + CTest，LANGUAGES Fortran）
- 编译日期：2026-10-01
- 编译器：flang-ohos/20.1.0（Fortran）+ OHOS SDK clang（C 链接驱动）
- 状态：built（工作树已完成，待真机预检回填实测证据）

## 上游信息

- 上游仓库：https://gitlab.com/siesta-project/libraries/libpsml
- 上游版本：2.1.0（2024-05-27，tag 508cffb9）
- 源码包：libpsml-2.1.0.tar.gz（866,614 字节）
- sha256：2977d4a83c06cb4c1bbe870d192ab1efd335e5bb78ee8f5ac3d51ce2cd2c0c60（Windows certutil 实测）
- 许可证：BSD-3-Clause（COPYING 全文为三条款 BSD）
- 源码结构：src/（13 个 .F90/.f90/.inc，m_psml 对外模块）、examples/（getz/getz_stat/show_psml/normalize + .psml 数据）、config/cmake（LibpsmlFindPackage 等）

## 编译步骤

1. `source()` 双 `get()`：libpsml-2.1.0（strip_root）+ xmlf90-1.6.3（解到 `external/xmlf90-1.6.3`）。
2. `generate()`：CMakeToolchain，`CMAKE_SYSTEM_NAME=OHOS` / processor aarch64 显式覆写；
   `CMAKE_Fortran_COMPILER` 指到 flang-ohos 包内 flang，Fortran flags 按 netcdf-fortran
   口径（`--target=aarch64-unknown-linux-ohos` + SDK sysroot + clang resource-dir 探测，
   链接期 `-L<sdk>/llvm/lib/aarch64-linux-ohos` 供 libunwind.a）；
   `XMLF90_SOURCE_DIR` 指到第二源目录，走上游 source 机制离线构建 xmlf90。
3. `build()`：cmake.configure → cmake.build → `ctest --output-on-failure -O ctest_stdout.log` 全量 12 项 →
   逐行解析 ctest_stdout.log 的 `N/M Test #K ... Passed|Failed` 行（LastTest.log 仅交叉核对）→ 上报 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `hmbs_upstream.json`。
4. `package()`：cmake.install（libpsml + xmlf90 产物）→ COPYING 进 licenses/ →
   `res/hmbs_upstream.json` 随包携带；shared=true 时对 .so 重签名（binary-sign-tool）。
5. `test_package`：flang 编译 `test_libpsml_consumer.f90`（-I 包内全部 .mod 目录）→
   clang 链接 `-lpsml -lxmlf90` + 静态 Fortran 运行时 → 带 fixture 运行 →
   解析程序自身汇总行 → 上报 `HMBS_TEST_PACKAGE_RESULT` → re-emit 上游标记。

## 上游测试盘点（审计结论，非执行结果）

| # | ctest 注册名 | 来源文件 | 说明 |
|---|--------------|----------|------|
| 1 | libpsml_getz | examples/getz.F90 | 解析 80_Hg.psml，输出 80 |
| 2 | libpsml_getz_die | examples/getz.F90 | 不存在文件触发 custom psml_die |
| 3 | libpsml_getz_stat_non_existent | examples/getz_stat.F90 | stat 非零返回 |
| 4 | libpsml_getz_stat_parsing | examples/getz_stat.F90 | 畸形 bad.psml 路径 |
| 5 | libpsml_show | examples/show_psml.F90 | projector 数据匹配参照行 |
| 6 | libpsml_mgga | examples/show_psml.F90 | mgga.psml MGGA 分支 |
| 7 | XMLF90_SAX_Features | xmlf90 sax/features/example.F90 | SAX 特性解析 |
| 8 | XMLF90_SAX_check | xmlf90 sax/features/xmlcheck.f90 | 合法 XML 字符统计 |
| 9 | XMLF90_SAX_check_stat | xmlf90 sax/features/xmlcheck_stat.f90 | stat 版合法解析 |
| 10 | XMLF90_SAX_Malformed | xmlf90 sax/features/xmlcheck.f90 | 畸形 XML 报错 |
| 11 | XMLF90_SAX_Malformed_stat | xmlf90 sax/features/xmlcheck_stat.f90 | stat 版畸形报错 |
| 12 | XMLF90_SAX_BadEntity | xmlf90 sax/features/xmlcheck_stat.f90 | 非法实体报错 |

- 总数口径：ctest_entries，`upstream_test_total: 12`。
- `examples/run_*.sh`（run_test.sh 等）是手工安装检查脚本，非 ctest 注册，不计入总数。
- 执行结果：待真机预检回填（本轮不猜测）。

## 依赖版本

| 依赖 | 版本 | 来源 | 状态 |
|------|------|------|------|
| flang-ohos | 20.1.0 | 制品仓（仓库已有配方并合入，netcdf-fortran 等在用） | tool_requires，待预检实证 |
| xmlf90 | 1.6.3（commit 963fe5d1） | conandata 第二源，官方 gitlab 归档，sha256 已实测 | 随构建，无需制品仓 |

- xmlf90 选择 1.6.3 的理由：上游要求 ≥1.5.4；1.6.x 自带 CMake 框架（source 机制要求顶层
  CMakeLists.txt）；1.6.2+ 含 `xml_parse` stat 特性，与 libpsml 的 `check_xmlf90_stat`
  探针语义一致；是 2.1.0 发布时（2024-05）最新的稳定 tag。
- 本包无 `requires`（普通依赖），`package_info` libs 为 `psml + xmlf90`（静态链必备，
  上游 PUBLIC 链接语义）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 全量检出失败：`archives/g/gama/...patch??` 非法路径 | 上游某文件名尾带 `\r\r`，Windows NTFS 非法 | 稀疏检出（cone，限定 docs/knowledge/templates/.gitcode/ci/scripts/archives/l + 按需 add）；`core.protectNTFS=false` 后索引可写；此为本机限制，真机/Linux 不受影响 |
| 2 | xmlf90 无制品仓包（R36） | 制品仓确实没有 xmlf90 | 不新增 requires；用上游自带 source 机制 + conandata 第二源离线注入（E668 模式），构建期零网络 |
| 3 | 上游默认 `GIT_TAG master` 拉 xmlf90（不可复现） | LibpsmlFindPackage fetch 路径 | 用 `XMLF90_SOURCE_DIR` 固定走 source 路径，fetch 路径永不触发；版本钉死 1.6.3 |
| 4 | ctest 计数口径 | LastTest.log 无 `Test #K` 行 | 只读 LastTest.log（分母头 + verdict 短语），stdout 正则仅作诊断回显，不参与计数 |
| 5 | 真机 Fortran 编译器断裂：flang 链接报 Scrt1.o/crti.o/-lc 缺失 | SDK 挂载点漂移到 harmonybrew（resource=.../Cellar/ohos-sdk/26.0.0.18_1/native/...），主 glob 全在 /data 下空命中；包装 clang 的 -print-sysroot 直接 exit 1，故回退分支无 --sysroot 进破碎构建 | 主包：glob 增 harmonybrew/Cellar + 驱动祖先/resource 派生 native，_derive_sysroot_from_known 从 resource/unwind/驱动反推 sysroot，无 sysroot 直接抛环境错不再进 cmake；test_package：clang 经 PATH 发现 + 同口径反推 sysroot，flang 编译与 clang 链接均带 --target/--sysroot/-resource-dir/-L |
| 6 | 真机 configure 在 pkgconf 步 FATAL：Could NOT find PkgConfig（2026-09-30 预检） | XMLF90_SOURCE_DIR 已传（ALLOWED 含 source），但上游默认顺序 cmake→pkgconf→source→fetch，pkgconf 分支首行 find_package(PkgConfig QUIET REQUIRED)，真机缺 pkg-config 可执行文件时直接 FATAL，到不了 source | generate() 追加 xmlf90_FIND_METHOD=source + XMLF90_FIND_METHOD=source（上游 LibpsmlFindPackage 支持的 <name>_FIND_METHOD，大小写两路），强制只走 source 直达 add_subdirectory，跳过 cmake/pkgconf/fetch |
| 7 | 真机 12 项 ctest 全灭：`Fortran STOP: Cannot open test file`（2026-09-30 预检；构建本身 [100%] 成功） | 非 fixture 缺失：libpsml_show 已打印 `Processing: 80_Hg.psml`（输入文件正常打开，WORKING_DIRECTORY 与 install_tests 拷贝均正常），随后 STOP；xmlf90 的 example（无参数打开 test.xml）同样 STOP。定位到 `xmlf90-1.6.3/src/sax/m_sax_reader.f90` 的 `find_eor_eof`：每次 `open_xmlfile` 先 `open(STATUS="SCRATCH")` 建 EOR/EOF 探测文件，运行库经 libc tmpfile() 在 /tmp 下建匿名临时文件，HarmonyOS 上 /tmp 缺失或不可写导致 12 个测试进程全部在断言前 STOP | portability 补丁 `patches/0001-xmlf90-scratch-tmpdir-fallback.patch`：保留 SCRATCH 快捷路径，失败时回退到 $TMPDIR/$TMP/$TEMP 下的显名临时文件（最后是当前目录，用完 `close(status="delete")`），EOR/EOF 探测语义不变、不弱化任何断言；主包 `_run_upstream_tests` 同步把 TMPDIR/TMP/TEMP 经 os.environ + 排最后的 env 脚本指向已建的 build/tmp，test_package 的 test() 把 TMPDIR 指到可写的 build 目录 |
| 8 | 补丁打不上：`hunk no.1 doesn't match at line 324, actual character(len=1) :: c`（2026-09-30 预检 compile 阶段） | 补丁 hunk 头行号写错（-324/-349），实际 `call get_unit` 在 326 行附近；按错行号投放时正好落在 `character(len=1) :: c` 上，上下文对不上 | 按上游 1.6.3 实测源码重算 hunk 头（-326,7），回退文件名带单元号防并行 ctest 碰撞；conanfile 的 `build()` 保留 `apply_conandata_patches` 快捷路径，失败时经 `_apply_scratch_fallback` 做同语义 python 注入（幂等、无行号依赖），不弱化断言 |
| 9 | 链接失败：`ld.lld: error: undefined symbol: open_probe_file_`，被 `m_sax_reader` 的 `find_eor_eof` 引用（2026-09-30 预检 compile 阶段，xmlf90-sax-features 链接） | 补丁把回退逻辑做成模块内新子程序 `open_probe_file`，flang-20 编译 `find_eor_eof` 中的调用时按外部符号处理（引用名为 `open_probe_file_`），归档内无此外部定义故链接断裂；与 thin 归档/缺编译器无关 | 改用 Fortran 2008 `block` 内联回退：SCRATCH 失败时在 `find_eor_eof` 内部直接走 TMPDIR/TMP/TEMP/当前目录显名文件，不新增任何子程序与符号；`.patch` 与 `_apply_scratch_fallback` 双路同语义同步，不弱化断言 |
| 10 | 上游标记零计数：12 项 stdout 明确 `Passed`（`1/12 Test #1 ... Passed` 且 `Total Test time` 正常结束），但标记 `discovered=12 executed=0 passed=0`（2026-09-30 预检 compile 阶段，`_run_upstream_tests` 抛 `upstream tests failed`） | 计数主源选错：只读 `LastTest.log` 的 `Test Passed.` 等 verdict 短语；该文件本轮分母为 12 但 verdict 短语零命中（格式漂移或读到非 verdict 变体），而 stdout 的 `N/M Test #K ... Passed` 行（守则明示允许的另一确定源）明确有 12 行通过；单源失效即整体判失败，无回退 | 主源切换为 ctest 经 `-O ctest_stdout.log` 落盘的 stdout 全量日志：逐行解析 `N/M Test #K:` 行（分母 M 即 discovered，必须唯一）+ 同行尾 verdict 词逐行单判（Passed/Failed/Timeout/Skipped/Not Run，一行一类，未知 verdict 计 failed 并转储，executed=passed+failed，无算术修补）；`LastTest.log` 降为诊断交叉核对（drift 只告警，不参与计数）；主源缺失时如实失败并转储文件状态与搜过路径 |
| 11 | 真机 `source()` 对 gitlab.com 连续 ReadTimeout（2026-10-02 预检 compile 阶段；conan 内置 2 次退避重试后仍失败，主源 + xmlf90 第二源同宿主） | 实证结论为真机到 gitlab.com 的瞬时路由故障，非配方 URL 错误：文件仅 866,614 字节，本机直连 4.5s 下完且 sha256 与配方 `2977d4a…` 逐字节一致；全部候选镜像逐一实测不可用或字节不一致（见下表），无"字节完全相同"的可信异地镜像 | 按守则"找不到可信且可用的镜像时保留原 URL 并如实报告"：不改 conandata.yml/sha，不引入来源不明地址；等 hmbs 重跑预检（liborcus/0.21.0 有 transient timeout recovered 先例；本轮预检同时伴随 SSH 网关熔断等 infra 噪声） |
| 12 | 真机 compile 阶段空日志 Signal 9（2026-10-03/04 预检；stdout/stderr 均无构建输出） | 无配方归因证据：源码包仅 866KB，配方无高内存调用；最可能为真机 OOM killer 或 harness 侧 kill，非编译错误 | 配方层强制串行构建（`CMAKE_BUILD_PARALLEL_LEVEL=1` + `cmake.build -j1` 双保险，HMBS jobs=1 之外再钉死），峰值内存最低；不跳过任何测试、不改断言；若重跑仍空日志 Signal 9 则判 infra 待恢复 |

## 镜像可行性实证（2026-10-02，本机 curl 实测，不改 sha256 前提）

| 候选 | 结果 | 结论 |
|------|------|------|
| `gh-proxy.com/` + gitlab URL | 404 | GitHub 专用，拒绝 |
| `moeyy.cn/gh-proxy/` + gitlab URL | 404 | GitHub 专用，拒绝 |
| `ghfast.top/` + gitlab URL | 403 | 拒绝 |
| `gitclone.com/gitlab.com/...` | 404 | 拒绝 |
| gitlab API 归档（`?sha=2.1.0`） | 200 但 sha `7a1bdbc…` ≠ 配方 | 字节不同，拒绝 |
| gitlab generic packages API | 空列表，未发布 | 无此渠道，拒绝 |
| SIESTA 官方 upload 静态包（siesta 自用 `/-/project/11928852/uploads/…`） | 200 但 sha `ed14f327…` ≠ 配方 | 字节不同，拒绝 |
| Debian pool | libpsml 仅 `.orig.tar.bz2`（压缩格式不同）；xmlf90 为 `+dfsg` 重打包 | 无法保持原 sha，拒绝 |
| Gentoo distfiles | 404 未收录 | 拒绝 |
| 官方 `/-/archive/` 直连 | 200，866,614 字节，sha 与配方一致 | 唯一可信源，保留 |

## 源码修改

1 个 portability 补丁（`patches/0001-xmlf90-scratch-tmpdir-fallback.patch`，
conandata 已登记，`export_conandata_patches`/`apply_conandata_patches` 自动处理）：
只改 `external/xmlf90-1.6.3/src/sax/m_sax_reader.f90`（第二源，随包构建的
xmlf90），在 `find_eor_eof` 内部用 Fortran 2008 `block` 内联回退：裸
`STATUS="SCRATCH"` open 保留为快捷路径，失败时在块内走
TMPDIR/TMP/TEMP/当前目录显名文件（用完即删）。不新增任何子程序与符号、
不弱化任何断言。
未改上游测试、未引入 `__OHOS__` 平台宏。其余适配仍经 CMake 变量/工具链完成。

## 验证结果

```bash
# 待真机预检（conan create 全量：12 项 ctest + 4 项消费者检查）
# 回填：conan create 日志片段、HMBS_UPSTREAM_TEST_RESULT、HMBS_TEST_PACKAGE_RESULT
```

- 证伪计划（证据轮执行）：① 确认 fixture/二进制非空；② ctest 输出含 12 个用例的
  Passed 行且 LastTest.log 分母为 12；③ 消费者汇总行 `LIBPSML_CONSUMER 4/4`；
  ④ 必要时用 `exit 1` 桩替换二进制重跑，确认 harness 能抓到失败。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libpsml/manifest.yaml | 软件级 manifest |
| archives/l/libpsml/2.1.0/conanfile.py | 主配方（CMake + flang + ctest 全量） |
| archives/l/libpsml/2.1.0/conandata.yml | 双源 URL + sha256 |
| archives/l/libpsml/2.1.0/manifest.yaml | 版本级 manifest |
| archives/l/libpsml/2.1.0/notes.md | 本文件 |
| archives/l/libpsml/2.1.0/test_package/conanfile.py | 消费者测试入口（含双标记上报） |
| archives/l/libpsml/2.1.0/test_package/test_libpsml_consumer.f90 | 4 检查消费者程序 |
| archives/l/libpsml/2.1.0/test_package/fixtures/14_Si.psml | 上游原文件逐字复制夹具 |
| archives/l/libpsml/2.1.0/test_package/MANIFEST.yml | 上游 12 项声明 + 消费者声明 |

## 注意事项

- 本机 Windows 无 conan/OHOS 工具链，未在本机运行任何编译；一切构建验证走真机预检。
- `test_package` fixture 为 103 KB 上游原文件，有意为之（真实端到端解析，无有效数据
  就没有正向断言；手写 PSML 有模式无效风险）。
- 若预检出现 xmlf90 与 flang 的 Fortran 方言不兼容（如旧式 common/equivalence），
  下一轮按日志加补丁并在 manifest 登记。
- 若预检 `ctest -N` 注册数不是 12（如 xmlf90 testsuite 未注册），以实测为准修正
  `upstream_test_total` 与 MANIFEST（审计数让位实测数，附证据）。
