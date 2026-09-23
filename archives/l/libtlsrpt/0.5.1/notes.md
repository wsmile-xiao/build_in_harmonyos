# libtlsrpt 0.5.1 — 适配笔记

> 档案创建时间: 2026-09-18
> 最后更新: 2026-09-18
> 状态: built（待真机预检：conan create + test_package + 上游测试证据）
> 申请人: zhangyuge147（队伍：龙骑士）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libtlsrpt |
| 版本 | 0.5.1 |
| 上游仓库 | https://github.com/sys4/libtlsrpt |
| 上游 tag | v0.5.1（commit 4f9346b2afaa3f6d12c841930bfb1d900f5cd0f6，经 git ls-remote 确认存在） |
| 源码包 | https://github.com/sys4/libtlsrpt/releases/download/v0.5.1/libtlsrpt-0.5.1.tar.gz |
| sha256 | e5570db13c15d74ae467b00fb1aa40ddd24b22f3281069e712d60b7a2bf7b31d（与 FreeBSD ports TIMESTAMP/SIZE 363940 条目一致） |
| 构建系统 | Autotools（configure + make + make install） |
| 许可证 | LGPL-3.0-or-later |
| 依赖 | 无（FreeBSD ports 注明无依赖；configure.ac 无外部依赖检查；Gentoo ebuild DEPEND 为空） |
| 非系统同名库 | 是（OHOS /lib 下无 libtlsrpt，默认静态构建，保留 shared 开关） |

## 二、上游审计（测试存在性）

审计对象：上游 tag v0.5.1 全树（经 `git clone --branch v0.5.1` 落盘核验）。

顶层文件：Makefile.am、configure.ac、libtlsrpt.c、tlsrpt.h、tlsrpt_version.h.in、
demo.c、man/、doc/、packaging/、INSTALL、README.md、CHANGELOG.md。

- `Makefile.am`：仅 `lib_LTLIBRARIES/include_HEADERS/pkgconfig_DATA/SUBDIRS = man`，
  无 `TESTS`、`check_PROGRAMS`、`check-local` 目标。
- `configure.ac`：仅 `AC_INIT/AM_INIT_AUTOMAKE/AC_PROG_CC/AM_PROG_AR/LT_INIT`，
  无测试相关宏。
- 全树 `find -name '*test*'`：仅命中 `demo.c`（手动演示程序：main 直接跑三遍
  testrun，经 datagram 套接字发送，无断言、无 harness、无退出码判定，需
  collectd 配合，不构成自动化测试）。
- 无 `tests/`、`test/` 目录，无 gtest（`TEST(`/`TEST_F`）、pytest（`def test_`）、
  ctest 注册。

结论：**上游确实无自动化测试套件**。`test_package/MANIFEST.yml` 已按规范写入
`upstream_tests_exist: false` 与完整 `upstream_test_audit`，`conanfile.py`
与 `test_package/conanfile.py` 均输出 `status: "no_tests"` 的
`HMBS_UPSTREAM_TEST_RESULT` 机器证据（主配方 + test_package 双通道复发，
防包缓存命中时证据缺失）。

## 三、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| `libtlsrpt.c`（`build()` 内内存补丁，非 patches/ 文件） | OHOS libc `open_memstream` 缺陷：`fprintf` 成功但 `fclose` 恒返 EBADF（真机 `tlsrpt_finish_policy rc=28009 errno=9`；E999/c-json 四象限探针 + tinycbor R03 同指纹佐证：`fflush` 可发布缓冲，`fclose` 仍返 -9） | `finish_policy` 三路子流 + `finish_dr` 主流的每个 `fclose` 前补 `fflush`，`fclose` 返回 `EBADF` 时忽略（缓冲已由 `fflush` 落盘），其他错误仍记录；上游关闭顺序与 `free` 序列保持原样 | 内存补丁（`patches_applied: []`；无平台宏，R8/PF5 合规） |

- `conandata.yml` 仅官方 release URL + sha256（R39 合规，镜像 fallback 由 CI 自动添加）。
- `build()` 仅在 `configure` 缺失时（git checkout 场景）回退 `autoreconf`，
  正常 release 路径严格 `configure + make -j1`（R6：不改生成文件）。
- 平台判断：`validate()` 限定 `os in ("Linux", "OHOS")`（R32）。
- 编译器经 AutotoolsToolchain 注入，不裸用 shell 环境变量（R33）。
- 无 `__OHOS__` 平台宏注入（R8 / PF5 合规）。

## 四、test_package 设计（R34 反空壳）

`test_package/test.c` 实质调用被测库全部核心 API（非打印空壳）：

1. `tlsrpt_version()`：非空 + 字符串精确等于 `0.5.1`；
   `tlsrpt_version_check(0,5,1)` 接受自身版本，`tlsrpt_version_check(9,9,9)` 拒绝外来主版本。
2. `tlsrpt_strerror(TLSRPT_ERR_TLSRPT_CANCELLED)` 非空；
   `tlsrpt_error_code_is_internal()` 识别内部错误码；
   `tlsrpt_errno_from_error_code()` 提取 errno 部分。
3. 全生命周期：`tlsrpt_open`（dummy datagram socket，无需 collectd）→
   `tlsrpt_init_delivery_request` → `tlsrpt_init_policy(STS)` →
   `tlsrpt_add_policy_string` → `tlsrpt_add_mx_host_pattern` →
   `tlsrpt_add_delivery_request_failure` → `tlsrpt_finish_policy(FAILURE)` →
   `tlsrpt_finish_delivery_request`（无监听时返回 sendto 错误仅记录、不判失败，
   与 demo.c 行为一致）→ `tlsrpt_close`（句柄置 NULL 校验）。

CMake 侧：`CMakeLists.txt` 经 `find_package(libtlsrpt)` 链接
`libtlsrpt::libtlsrpt`，注册 `ctest` 用例 `test_libtlsrpt`。
`test()` 用 bash 包裹执行 ELF（OHOS mksh 限制），`can_run` 守卫交叉构建，
成功后输出 `HMBS_TEST_PACKAGE_RESULT(discovered=3/passedCount=3)`，
与 `MANIFEST.yml assertion_count: 3` 一致。

## 五、编译验证命令（真机预检用）

```bash
cd archives/l/libtlsrpt/0.5.1
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

预期：`conan create` 成功，日志含 `HMBS_UPSTREAM_TEST_RESULT`（no_tests/0/0/0）
与 `HMBS_TEST_PACKAGE_RESULT`（3/3），`./test_libtlsrpt` 输出
`test libtlsrpt 0.5.1: OK`。

## 六、真机证据（待 HMBS 预检回填）

- 本轮为首轮工作树提交，未做任何 commit/push；以上通过率数字为配方设计值，
  最终以 HMBS 真机预检日志实测为准，届时回填 PR 正文并更新本节。
- 证伪预案：确认 `test_libtlsrpt` 二进制非空、参照字符串 `0.5.1` 来自库内
  `TLSRPT_VERSION_STRING`（非测试自带常量比自身）；必要时可将桩替换为
  `return 1` 重跑，确认 harness 能捕获失败；无静默跳过分支（`can_run` 为假时
  属交叉构建跳过，真机原生构建必执行）。

## 七、审查规则自查（.gitcode）

- R34：test.c 全程调用真实 API，无空壳；test() 含 `self.run` 真实执行（PF3/L0d 合规）。
- R39/PF7：conandata 仅官方 GitHub release HTTPS URL + 真实 sha256，无镜像/搬运源。
- R8/PF5：无平台宏、无 `-D__OHOS__` 注入、无 patches。
- R37/PF8/PF9：首次适配用上游版本号 `0.5.1`；settings 四项齐全；
  `package_type="library"` 无 commands.json；单包单版本目录；分支 `feat/libtlsrpt-0.5.1`。
- R6：未改任何生成文件；R26：非系统同名库，静态默认合法；R32/R33 合规。
- 文件结构：conanfile.py + conandata.yml + test_package（conanfile/CMakeLists/test.c/MANIFEST.yml）
  + 双层 manifest.yaml + notes.md 齐全；无二进制、无状态文件、无 SUMMARY.md 改动。
