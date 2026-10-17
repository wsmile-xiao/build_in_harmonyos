# libcmis 0.6.3 适配笔记

## 编译环境

- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built（首轮工作树，真机预检待跑）
- 上游: https://github.com/tdf/libcmis（tag v0.6.3）
- 源码包: libcmis-0.6.3.tar.gz（799.4 KB，与上游 Release 页标注一致）
- sha256: `a7de8359f002e91cc430fcdfc14e1bb9cb45ac6a47ead8905f88f589b1eca6a2`（实测下载校验）

## 编译步骤

conanfile.py `build()` 实际执行的步骤（真机）：

1. 探测可写 TMPDIR 与可用 POSIX shell，固化进 conanbuild（c-client/cubelib/libdatovka 模式）。
2. 生成脚本 `configure`/`config.status` 的 autoconf mktemp 回退 `/tmp` 重定向到可写目录。
3. `configure` 的 `umask 077` 改为 `umask 022`（HMDFS setgid 目录，ezstream/libdatovka 先例）。
4. 清除 profile 注入的不可用 `/data/service/hnp/bin/bash` 字面引用。
5. 用 pkgconf/3.0.5 建立 `pkg-config` 垫片并前置 PATH（configure 的 PKG_CHECK_MODULES 需要）。
6. 显式 shell 调用源码 `configure`（内联 SHELL/CONFIG_SHELL/TMPDIR 优先于 conanbuild 导出），参数见 manifest.yaml。
7. `make -j1` 编译库。
8. 两阶段上游测试：`make check TESTS= -j1` 编译测试程序（SDK-first loader 前缀），`make check -j1` 运行（conan-only loader 前缀），日志加总 automake 小节。
9. `make install`（install 垫片规避 toybox/HMBS install 语义差异），删 `.la`，校验 `lib/libcmis-0.6.a` 真实存在。

## 上游测试清点（审计结论）

- `qa/libcmis/Makefile.am`: `TESTS = test-utils test-json test-atom test-factory test-sharepoint test-ws`（6 个，gdrive/onedrive 上游已注释“need updating”）。
- `qa/libcmis-c/Makefile.am`: `TESTS = test-api`（1 个；test-c-build 只编译不运行）。
- `qa/mockup/Makefile.am`: 仅 noinst 辅助库，无 TESTS。
- 合计 7 个测试程序，全部为 cppunit，全部离线（mockup 拦截 HTTP + DATA_DIR fixtures 随包发布，无网络需求）。
- 计数口径：顶层 `make check` 每个有测试的子目录各打印一个 `# TOTAL` 小节，配方加总所有小节（不是取单个）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 需要 xmlto（man 页） | OHOS 无 xmlto | `--without-man` |
| 2 | clang 下 -Werror 易失败（-Weffc++ 等） | 上游默认 werror | `--disable-werror`（与 Nixpkgs 打包选择一致） |
| 3 | cmis-client 需 boost program_options 且需 live 服务器交互验证 | 交付物是库；CI/真机无法交互验证 client | `--disable-client`，纯库包，无 commands.json（R38） |
| 4 | boost.m4 不走 pkg-config | boost 探测走 --with-boost 路径 + 链接测试 | generate() 传 `--with-boost=<boost 包根目录>` |
| 5 | 真机 /tmp 只读、profile bash 不可用 | 预检历史经验（E002/E009） | 复用 _writable_tmpdir/_detect_shell/持久化三件套 |
| 6 | 设备无系统 pkg-config | configure 硬依赖 PKG_CHECK_MODULES | tool_requires pkgconf/3.0.5 + pkg-config 垫片 |

首轮工作树尚未真机验证；以上 5–6 的处理均为基于 libdatovka/cubelib/c-client 已合入经验的前置复用，真机失败时按预检日志继续修复。

## 源码修改

无（patches_applied 为空；umask/shell 替换均为构建时字符串处理，未提交补丁文件）。

## 依赖版本

- curl/8.15.0（60+ 已合入配方同款 pin）
- libxml2/2.15.3.1（repo-unique 硬化版，libdatovka 同款）
- openssl/3.5.6.1（与 curl 范围统一，libdatovka 同款直接依赖）
- boost/1.90.0.4（含 date_time，libphonenumber/lief/mailio 同款）
- cppunit/1.15.1（published）
- tool: pkgconf/3.0.5

## 验证结果

```bash
# 首轮：工作树已完成，真机预检待 HMBS 后台执行
# 待回填：conan create 日志中的 make check 加总（TOTAL/PASS）与
# HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT 两行标记
```

## 证伪计划（预检通过后做一次）

1. 确认测试日志非空且含 7 个程序的运行痕迹（非仅汇总行）。
2. 按守则做一次反向验证（如用桩二进制确认 harness 能抓失败）。
3. 区分通过与静默跳过：SKIP>0 即判 failed（配方已实现）。

## 注意事项

- 产物为静态库 `libcmis-0.6.a` + `libcmis-c-0.6.a`，头文件 `include/libcmis/`，pkgconfig `libcmis-0.6.pc`。
- `libcmis` 不是系统同名库；static 默认是仓库 autotools 配方的常规选择（aalib/libdatovka 同款）。
- Windows 宿主检出说明：本机为大小写不敏感文件系统，上游 `archives/l/libXext` 与 `archives/l/libxext` 同名冲突、`archives/g/gama` 下文件名含非法字符，工作树对这三处做了 `assume-unchanged`/稀疏规避；与本适配无关，后端 Linux 侧不受影响。

## 真机预检 round-2（2026-09-19）：qa/libcmis 1/6 失败的诊断与修复

- 现象：`make check -j1` 加总 TOTAL=6 PASS=5 FAIL=1 SKIP=0，失败目录为 `qa/libcmis`
 （见预检 `HMBS_UPSTREAM_TEST_RESULT`；`make check-recursive` 在该目录中断，
  后续 `qa/libcmis-c` 未执行，故计数为 6 而非 7）。
- 直接证据：
  1. 预检日志 `libcmis/0.6.3: export_conandata_patches(): No patches defined in conandata`——
     工作树 `patches/0001-qa-tmpfile-tmpdir-fallback.patch` 存在但从未在
     `conandata.yml` 注册，构建时根本没有应用。
  2. 全源码扫描（upstream.tar.gz 内全部 .cxx/.hxx）：只有 3 个文件调用 `tmpfile()`——
     `qa/libcmis/test-decoder.cxx`（属失败目录的 `test-utils` 程序）、
     `qa/libcmis-c/test-document.cxx`、`qa/libcmis-c/test-folder.cxx`。
     automake 按程序计数，`test-utils` 失败即表现为 6 个程序中恰好 1 个 FAIL。
  3. 真机平台能力 `hardlink:0/chmod:0` + 配方自注 `/tmp` 只读；musl 的 `tmpfile()`
     硬编码 `/tmp`、无视 `TMPDIR`，而配方虽已把 `TMPDIR` 指向可写目录，
     却救不了 `tmpfile()` 本身。`DecoderTest::setUp()` 拿到 NULL stream 即整程序失败。
- 修复（本轮工作树，未提交，待 HMBS 真机预检验证）：
  1. `conandata.yml` 注册该补丁（`patches:` 列表，`patch_type: portability`），
     使 `build()` 开头的 `apply_conandata_patches()` 真正生效。补丁行为：
     先试 `tmpfile()`，仅在返回 NULL 时用 `TMPDIR/TMP/TEMP` 下的 `mkstemp()`
     回退；不断言、不改测试逻辑（`qa/libcmis-c` 的同类调用一并覆盖）。
     补丁锚点已对原始 tarball 全量校验（26 hunks / 3 files，锚点行均存在）。
  2. `conanfile.py` 新增只读诊断 `_dump_test_suite_logs()`：`make check`
     非全绿时把各 `test-suite.log` 尾部（每文件 80 行、最多 5 个）打印到 stdout，
     下一轮预检可直接看到失败断言，不再依赖摘要猜测。
- 证伪计划（预检返回后执行）：① 确认日志含 `test-suite.log` 明细与 7 个程序痕迹；
  ② 若仍有 FAIL，按新明细定位到具体断言再修，不复用本轮假设。
