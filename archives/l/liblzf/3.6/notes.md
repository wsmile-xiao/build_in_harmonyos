# liblzf 3.6 OHOS 适配记录

- 上游：http://software.schmorp.de/pkg/liblzf.html（Marc Alexander Lehmann）
- 源码包：`liblzf_3.6.orig.tar.gz`（Debian pool，任务指定上游 URL）
  - 与官方发布包 `http://dist.schmorp.de/liblzf/liblzf-3.6.tar.gz` 逐字节相同（57120 字节，
    同一 sha256：`9c5de01f…fb46a`，经清华 Debian 镜像实测验证）
  - conandata.yml 用有序 URL 列表：清华 Debian 镜像在前（CI 下载超时保护），
    `deb.debian.org` 官方 URL 保留最后回退；同一文件、同一 sha256
- 许可证：BSD-2-Clause OR GPL-2.0-or-later（见上游 lzf.h 头）
- 构建系统：Autotools（configure.ac + 预生成 configure + 手写 Makefile.in）
- 产物：`lib/liblzf.a`（静态，dictate：上游不构建 .so）+ `bin/lzf` CLI + `include/lzf.h`
- 依赖：无（纯 C，无外部 Conan 依赖；W0：无依赖可查）
- 适配路径：路径 A（基础适配）

## 历史归档核验（W0b）

仓库已有 `archives/l/liblzf/3.6/` 历史归档（2026-04-24，旧探索流程），已逐项核验：

- 历史结论：设备原生工具链 configure+make 成功（`status: published` 旧口径），源码
  `https://dist.schmorp.de/liblzf/liblzf-3.6.tar.gz`。
- 历史遗留补丁 `patches/0001-Makefile.patch` / `0002-config.h.patch` 为**设备本地生成文件
  的原样捕获**（硬编码 `/storage/Users/currentUser/usr/local`、clang/llvm-ar 设备路径），
  违反 R6（只改源文件，不改 `Makefile`/`config.h` 等生成文件），在 CI clean 环境无法复用，
  本轮已删除（偏离说明即本段）。
- 历史 notes 勾选了 "make check 结果" 但无任何实测记录；经本轮发布包审计确认上游根本没有
  check/test 目标，该勾选为空挂，本轮按 `no_tests` 如实处理。
- 历史经验可迁移部分：构建系统确为 Autotools、产物为静态库 + `lzf` CLI（与本轮配方一致）。
- 环境不可迁移部分：设备直编成功不可作为 CI 证据，本轮配方改走 Conan AutotoolsToolchain
  + HMBS 环境修正，待真机预检实证。

## 上游测试审计结论

上游确无测试（`upstream_tests_exist: false`，口径 `manual_audit`，
`upstream_test_total: 0`）：18 项发布包无 tests/ 目录、无 *test* 源文件、
手写 Makefile.in 目标仅 all/clean/lzf/liblzf.a/install/dist/bench，
无 check/test 目标。详见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。

因此主配方 `build()` 不运行 `make check`（`upstream_test_in_build: false`）；
`HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0, executed=0)` 由
test_package 每次运行输出（含包缓存命中轮次，conanfile 复发）。

## 配方要点

1. 不传 `--build/--host`（R15）：包内无 config.guess/config.sub，不探测 triplet。
2. HMBS 环境修正（bwm/0.6.3 同款）：`generate()` 写 build 域 env 脚本固定可用
   SHELL/CONFIG_SHELL（`/bin/sh` 优先，避开 profile 里部分真机不可执行的 HNP bash）、
   可写 TMPDIR（OHOS `/tmp` 只读）、真实存在的 CC/CXX（profile 值优先，缺失时回退
   PATH/SDK 探测，仅 isfile 探测，R49）；`build()`/`package()` 显式 shell 调用。
3. `package()` 用 `make install prefix=... bindir=... libdir=... includedir=...`
   显式覆盖：手写 Makefile.in 不认 DESTDIR，直接用默认路径会装到系统目录。
4. 静态库天然合规 R26（无 .so 产物）；`package_info()` 声明 `libs=["lzf"]` +
   `bindirs=["bin"]`（bin/lzf 是真实安装的 CLI，L0k/R38 按 tool 声明 commands.json）。
5. 平台判断 `self.settings.os in ("Linux", "OHOS")`（R32）；编译器来自 Conan
   conf/Toolchain（R33，无裸 `${CC}`）；Python 源码无 `__OHOS__` 平台宏（R8 无需）。
6. HMBS install 垫片只接受单文件双参调用，`install -c -d` 直接报 Error 64
  （xeyes/adms 同款）：`package()` 在 build_folder 下写 cp/mkdir 垫片
  （os.open 0o755 保证可执行位，chmod 容错），以 `INSTALL=` 覆盖 + PATH
   前置方式让 `make install` 走垫片；仅处理垫片不支持的子能力，不改安装逻辑。

## 消费者测试（test_package，ctest 共 6 用例）

- `api:roundtrip_text/binary/large`：真实压缩解压往返 + 字节级比对（大零块要求压缩率 <5%）。
- `api:corrupt_einval`：手工非法回指流 `{0x20,0x00}` 必须返回 0 且 errno==EINVAL（lzf.h 文档行为）。
- `api:small_out_e2big`：32 字节字面量流入 4 字节缓冲必须返回 0 且 errno==E2BIG。
- `cli:help_and_roundtrip`（test_cli.sh）：`lzf -h` usage 断言、管道往返字节一致
  （非空守卫，防空文件比空文件假通过）、文件 `f→f.lzf→f` 往返字节一致、
  垃圾输入解压必须失败（反向证伪 harness 有效性）。
- 计数口径：`ctest -N` 取 discovered，ctest 输出 `Test #N … Passed|Failed` 行计数，
  与 `Testing/Temporary/LastTest.log` 同解析器交叉校验 + 汇总行核对；
  三源不一致直接报失败标记并让构建失败，不做数字修补。

## 验证命令（真机预检由 HMBS 后台执行，本轮未提交）

```bash
cd archives/l/liblzf/3.6
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

- 预期：conan create 成功；日志含 `HMBS_TEST_PACKAGE_RESULT={"executed":true,
  "passed":true,…,"discovered":6,"passedCount":6}` 与
  `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",…,"discovered":0,"executed":0}`。
- 本轮按任务要求只完成未提交工作树，真机 rule4 门禁通过前不 commit/push/建 PR。
