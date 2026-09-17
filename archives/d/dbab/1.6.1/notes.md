# dbab 1.6.1 适配笔记

## 编译环境

- 构建系统: makefile（仅安装，无编译）
- 编译日期: 2026-09-13
- 编译器: 不适用（纯 shell/Perl 脚本）
- 状态: built（待真机预检验证后由 HMBS 提交）

## 编译步骤

1. 下载源码：`https://github.com/suntong/dbab/archive/refs/tags/1.6.1.tar.gz`
   （15062 字节，sha256 `bb5b3abc…9898f`，与 Debian `dbab_1.6.1.orig.tar.gz`
   校验值一致，交叉印证为官方源）。
2. `build()`：对 4 个 shell 脚本执行 `bash -n` 语法校验；输出上游
   `no_tests` 证据标记（见下）。
3. `package()`：按上游 Makefile 安装清单用 `copy()` 复制——5 个脚本到
   `bin/`，3 个配置样例到 `etc/dbab/`，手册页到 `share/man/man8/`，
   文档到 `share/doc/dbab/`，参考配置与 systemd 单元到 `share/dbab/`，
   LICENSE 到 `licenses/`。
4. `test_package`：`bash test.sh`（13 个断言，全部离线、无需 root）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `make install` 在真机不可直接复用 | 安装目标依赖 `ronn` 生成的 `assets/dbab-svr.8`（发布包缺失），且硬编码 `INSTALL = /usr/bin/install -c` | 配方用 Conan `copy()` 按上游安装清单逐项复制，效果等价；在 notes/README 中记录偏离原因 |
| 2 | 上游无测试套件，无法执行上游测试 | 24 文件发布包审计：无 `tests/`/`t/` 目录，Makefile 仅有 `man/clean/install` 目标，上游 CI 仅做 release-draft | `MANIFEST.yml` 写入 `upstream_tests_exist: false` + 完整 `upstream_test_audit`；`build()` 输出 `status:"no_tests"` 证据标记；`test_package` 用离线 fixture 覆盖三脚本核心变换逻辑与像素载荷完整性 |
| 3 | 脚本安装路径上游为 `sbin/` | Conan 工具包惯例使用 `bin/` 并经 `cpp_info.bindirs` 暴露 | 重定位到包内 `bin/`，`commands.json` 同步声明 |

## 源码修改

无补丁。纯脚本包，无需为 OHOS 修改源码。

## 依赖版本

无 Conan 依赖。运行时依赖（由使用环境提供）：系统 `perl`
（`dbab-svr` 需 `IO::Socket::IP` 模块）、`dnsmasq`、`curl`
（`dbab-get-list` 下载拦截列表时）。

## 验证结果

```bash
# 真机预检（HMBS 后台执行，本轮未跑）：
# conan create archives/d/dbab/1.6.1 --user=ohpcd --channel=stable
#   -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期：build() 中 4/4 shell 语法校验通过 + no_tests 标记；
#       test_package 中 13/13 断言通过 + HMBS_TEST_PACKAGE_RESULT 标记。
```

本地 file-level 自检（配方结构完整性）：conanfile.py / conandata.yml /
manifest.yaml / notes.md / test_package（conanfile.py + test.sh +
MANIFEST.yml + .gitignore）齐备；test.sh 断言计数 13 与 MANIFEST 一致。

## 2026-09-13 evidence 轮修复（上游标记 test_package 复发）

- 真机门禁报 `incomplete`（evidence）：上游测试发现 0/执行 0。
  根因：`HMBS_UPSTREAM_TEST_RESULT`（no_tests）只在主配方 `build()`
  输出，`test_package` 阶段 stdout 无此标记；缓存命中轮 build()
  被跳过时门禁扫不到上游证据（c10t/c4log/abuild-sudo 均在 test()
  复发标记）。另 `framework:"none"` 改为 `"ctest"`（c10t 同类
  no_tests 先例），审计扩展到 git tag 树（30 blobs/trees 全扫描，
  含 `.github/` nfpms 打包配置与 release-only workflow 说明）。
- 改动：`test_package/conanfile.py` 在 `test()` 末尾经
  `self.output.info` 复发同一 no_tests 标记；主配方 `build()`
  标记同步新文案；`MANIFEST.yml` 审计补 git 树证据。
- 上游复核结论不变：tag 1.6.1 确无任何测试套件（无 tests/t
  目录、无 *test* 文件、无 check/test 目标），`no_tests` 非伪造；
  test_package 13 断言保持独立的消费者验证。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/dbab-svr` 等 5 脚本 | 工具主体（`sbin/` 重定位至 `bin/`） |
| `etc/dbab/{dbab.addr,dbab.list+,dbab.list-}` | 配置样例 |
| `share/man/man8/*.8` | 手册页（随包附带的 4 份） |
| `share/doc/dbab/{dbab.md,README.md}` | 文档 |
| `share/dbab/*` | dnsmasq/squid 参考配置与 systemd 单元样例 |

## 注意事项

- `dbab-get-list` 需联网访问 `pgl.yoyo.org`，离线环境仅 `dbab-add-list`
  本地列表可用；PR 正文补充说明已声明。
- 本机未运行 conan（按任务守则，验证交由 HMBS 真机预检）；工作树保持未提交。
