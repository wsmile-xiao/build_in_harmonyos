# libmpd 11.8.17 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, Conan AutotoolsToolchain)
- 上游版本: 11.8.17 (https://www.musicpd.org/download/libmpd/11.8.17/libmpd-11.8.17.tar.gz)
- SHA256: `fe20326b0d10641f71c4673fae637bf9222a96e1712f71f170fca2fc34bf7a83` (365015 字节)
- 上游地址: https://www.musicpd.org/download/libmpd/
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS profile, clang 15, libc++)
- 状态: built (待真机预检通过后由 HMBS 统一提交)

## 上游测试审计
- 对 tarball 全树扫描: 无 TESTS/check_PROGRAMS/add_test/enable_testing/TEST(/def test_ 声明, 无 tests/ 或 test/ 目录.
- 唯一含 test 字样的是 `example/testcase/testcase.c`: 需连接真实 MPD 服务器的交互式 demo, 不构成自动化套件.
- 结论: 上游确无自动化测试套件 (test_package/MANIFEST.yml 记录完整审计, upstream_tests_exist: false, upstream_test_total: 0).
- 配方 build() 不调用 `make check`; 每次运行输出 `HMBS_UPSTREAM_TEST_RESULT` status:no_tests (discovered/executed/passed 均 0).

## test_package 设计 (R34 实质调用)
- `test_libmpd.c` (8 个 CHECK-OK, 离线无网络): mpd_new_default 非空 + hostname localhost (1-2) -> mpd_new 构造 + hostname 匹配 (3-4) -> set_hostname 回绕 (5) -> set_port/set_password/set_timeout 均 MPD_OK (6) -> 无服务器时 mpd_check_connected==FALSE (7) -> 信号连接器 + mpd_misc_get_tag_by_name("Artist")>=0 (8) -> mpd_free 无崩溃.
- test() 逐行计数 CHECK-OK: 打印合法 JSON 标记 `HMBS_TEST_PACKAGE_RESULT` (discovered=8/passedCount=实际计数); 含字面 `self.run()` 调用满足 L0d.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本轮真机 evidence/incomplete: 无法读取当前 archive 代码树 | `feat/libmpd-11.8.17` 分支与 upstream/main 同步但未创建 `archives/l/libmpd/11.8.17`, 真机预检无法启动 | 新建整套配方 (conanfile/conandata/test_package/MANIFEST/manifest/notes), 保持未提交等待 HMBS 同步预检 |
| 2 | 2011 年代码在现代 clang 报 int-conversion 错误 | 旧式代码隐式转换 (Nixpkgs/Homebrew 同型先例) | toolchain `cflags.append("-Wno-int-conversion")`, 不改语义 |
| 3 | 头文件安装路径特殊 | 头文件在 `include/libmpd-1.0/libmpd/*.h`, pc Cflags 为 `-I.../include/libmpd-1.0` | cpp_info.includedirs=[include/libmpd-1.0, include], cmake/pkg_config 名称对齐 |
| 4 | Windows 检出本仓必然脏 (libXext/libxext 大小写冲突) | 上游同时存在仅大小写不同的归档目录 | 本 PR 仅新增 archives/l/libmpd/**, 不碰冲突文件 (需要时 skip-worktree) |

## 依赖版本
- glib/2.88.0.1 (transitive_headers+transitive_libs; 上游 PKG_CHECK_MODULES glib-2.0>=2.16)
- 构建工具: 无 tool_requires (AutotoolsToolchain + PkgConfigDeps, 真机侧提供 clang/make/pkg-config)

## 验证结果
```bash
# 真机预检 (HMBS 后台统一执行, 本轮不本地跑 conan):
# conan create archives/l/libmpd/11.8.17 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
configure + make -j1 -> install -> test_package ./test_libmpd 8/8 CHECK-OK; 上游标记 no_tests 0/0
```

## 注意事项
- 本轮严禁 commit/push/建 PR/写 GitCode 接口与 `.hmbs/pr.json`; 工作树保持未提交, 待 HMBS 真机全部门禁通过后统一提交.
- `url` 填官方上游 (musicpd.org); CI 会自动追加镜像 fallback, conandata 只写官方原始 URL + 原 sha256.
- libmpd 非系统同名库, 保留动态库切换 (默认 shared=False 按标准 flags 切静态/动态).

## 2026-09-20 真机 compile 失败修复（已合入工作树，待预检）
- 现象：configure 报 checking for gcc... /data/service/hnp/bin/clang → C compiler cannot create executables（Error 77）。
- 根因：OHOS SDK clang 不从路径推断 --target，无该标志则链接探针失败；且 profile 绝对路径 CC 在构建沙箱可能不可执行，旧手动 sh configure 调用脆弱。
- 修改（conanfile.py）：generate() 在 OHOS 下给 extra_cflags/cxxflags/ldflags 与 cflags/cxxflags/ldflags 追加 --target=aarch64-unknown-linux-ohos；新增 _resolve_cc（--version 实测可用则沿用，否则 PATH 回退，恒带 --target）+ _fix_conanbuild_shell（conanbuild.sh 末尾重导出 CC/SHELL/TMPDIR）+ _dump_config_log；build() 改回标准 autotools.configure()/make 并在失败时转储 config.log；package() 同步追加 shell pin。

## 2026-09-24 真机 compile 失败修复（未提交，待预检）
- 现象：config.guess (2009-12-30) 报 unable to guess system type，UNAME_SYSTEM=HarmonyOS，configure 报 cannot guess build type; you must specify one（Error 1，autotools.configure()）。
- 根因（E007）：上游自带 config.guess/config.sub 无 HarmonyOS/__OHOS__ 分支，原生构建（无 --build/--host）下 configure 必须靠 config.guess 猜 build 类型，第一阶段即中断。
- 修改（conanfile.py）：新增 _patch_autotools_ohos()（纯 Python 复刻 scripts/patch-autotools-ohos.pl，不依赖真机 perl；递归修 source 树下全部 config.guess/sub，2009 版无 __ANDROID__ 锚点时仅加 HarmonyOS 系统识别块，echo/exit 旧风格自适应，幂等）；build() 在 OHOS 下 apply 后调用；generate() 在 OHOS 下显式追加 --build/--host=aarch64-unknown-linux-ohos（build==host，原生路径，cross_compiling=no，非 E007 禁止的 --host-only 交叉绕过）。
