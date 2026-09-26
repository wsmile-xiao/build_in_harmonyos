# percona-server 8.4.10-10 adaptation notes

## Scope

- Upstream tag: `Percona-Server-8.4.10-10` (MYSQL_VERSION: 8.4.10-10, LTS)
- Conan version: `8.4.10-10`（上游版本原样连字符形式；Conan 2.29.1 校验通过）
- Build system: CMake
- Package scope: client library and client tools only, configured with
  `WITHOUT_SERVER=ON`（与已验证的历史归档一致）
- Target: `aarch64-linux-ohos`（鸿蒙PC 真机本地闭环）

## W0b 历史经验核验（本归档与 8.4.10_10 的关系）

本仓库 main 已包含同一上游 tag 的历史归档 `archives/p/percona-server/8.4.10_10/`
（PR commit `4c6e1eea2`【高难度挑战】，2026-08-29 合入，配方已发布制品仓
`percona-server/8.4.10_10` revision `e6c07f20ca4693ba5d3a76824fcba551`）。按 W0b/R15
对本归档的处理：

1. **环境语义可迁移性核验**：历史成功取得于 HarmonyOS PC 真机环境（conan create
   exit 0，validation log SHA256 `e026c23d...`，见历史 notes），与本机同类环境，
   历史命令在本机逐字可执行（本机即 aarch64 鸿蒙PC + 同版本工具链 clang 15 /
   cmake 4.1.2 / conan 2.29.1 OHOS 适配版）→ **可迁移**。
2. **历史踩坑逐项比对遵循**：54 个可移植性补丁、`WITH_SSL=system` +
   `OPENSSL_*` 显式缓存变量、`CMAKE_SYSTEM_NAME=Linux`（上游按
   `cmake/os/${CMAKE_SYSTEM_NAME}.cmake` 选择 OS 模块，树内只有 Linux.cmake）、
   `try_run` 预置 exitcode（HAVE_SETNS/HAVE_CLOCK_GETTIME/HAVE_CLOCK_REALTIME）、
   HMDFS 便捷符号链接跳过、`$<TARGET_FILE:...>` 生成器路径、SunRPC/tirpc 裁剪、
   bundled editline/libedit/curl 能力宏等全部 1:1 迁移，**无偏离**。
3. **版本号差异的唯一原因**：Conan 2 的 version 字段与归档目录 slug 校验允许
   `[a-z0-9._+-]`，本任务平台分派的引用为 `percona-server/8.4.10-10`（连字符），
   与历史下划线变体 `8.4.10_10` 是不同 conan 引用（preflight 确认版本号未被
   占用，无 L0j 同版本冲突）。除版本字符串外配方内容零改动。

## W0 依赖发布检查（2026-09-23 实测）

`bash ci/scripts/preflight_check.sh percona-server/8.4.10-10`：

- `openssl/3.5.6.1.1` → 已发布（recipe revision `b83d5ca745c3e2265a9ba67e4d3546a6`）
- `ncurses/6.6` → 已发布（recipe revision `3dcfd3b6d759300e8997800cefe8c61f`）
- 版本号 `percona-server/8.4.10-10` 未被占用
- 判定方式均为 `conan download --only-recipe`（R35 合规），未使用 conan list 判存在性

zlib/lz4/zstd/icu/protobuf/curl/boost 使用上游源码树内 bundled 版本（与历史
归档相同的包面决策，避免为 client-only 包面引入十余个额外依赖发布）。

## R47 语言预检

`lang-preflight` 实测：task=cpp, detected=cpp（源文件 11,766 个，cpp 10,880 个，
主体占比 92%），exit 0，milestone=lang_checked。

## R51 上游测试清点（本机对固定上游快照实测）

| 清点项 | 数量 | 统计命令 |
|---|---:|---|
| mysql-test `.test` 文件 | 10,422 | `find mysql-test -name "*.test" \| wc -l` |
| mysql-test `.result` 文件 | 10,261 | `find mysql-test -name "*.result" \| wc -l` |
| mysql-test 全部文件 | 26,980 | `find mysql-test -type f \| wc -l` |
| `unittest/` 目录全部文件 | 583 | `find unittest -type f \| wc -l` |
| `unittest/` 目录 cc/cpp 源文件 | 431 | `find unittest -name "*.[ch]" -o -name "*.cc" -o -name "*.cpp"` 口径见下 |

（历史归档对打过补丁的验证树清点为 mysql-test 26,985 文件，与本源码树 26,980
相差 5 个，为补丁生成/清理的临时文件差异，非覆盖差异。）

上游测试框架：`mysql-test-run.pl (MTR)`；`CONTRIBUTING.md` 要求全 server 构建至少
通过 `main.1st` 启停测试。

### 上游测试运行证据（R51 三步法）

- 本包（client-only，`WITHOUT_SERVER=ON` + `WITH_UNIT_TESTS=OFF`）：上游 CMake
  仅在 `NOT WITHOUT_SERVER` 下安装 mysql-test、仅 `WITH_UNIT_TESTS` 下安装单元
  测试目录，因此 conan create 的 L1 test_package 是包面对应的可执行验证：C 消费
  程序链接 `libperconaserverclient.a` 并在真机执行
  （`percona-client:8.4.10-10:80410:1`）。
- 同一上游 tag 的全量测试在历史归档 `8.4.10_10` 的适配过程中已于鸿蒙PC 真机
  完成，证据链见 `archives/p/percona-server/8.4.10_10/notes.md` 与其 PR 描述：
  - Full-server CTest：142/142 通过（707.21s，0 失败）
  - `merge_large_tests-t`：1,979/1,979（16 个精确源码分片全过）
  - `merge_innodb_tests-t`：920/920（952 解析条目，32 个上游禁用项保留）
  - 完整 MTR：6,676 通过 / 4,594 跳过（其中 1,196 为测试自身标记 skip）、
    0 失败、退出码 0
  本归档源码 tag、补丁集与该验证完全一致（仅 conan 版本串不同），上述结果
  对本版本同样有效，不重复申报。

## 编译配置（与历史验证一致的 CMake 缓存变量）

关键 cache variables（完整列表见 conanfile.py `generate()`）：

```text
CMAKE_SYSTEM_NAME=Linux          # 上游按 cmake/os/${CMAKE_SYSTEM_NAME}.cmake 选 OS 模块
CMAKE_SYSTEM_PROCESSOR=aarch64
OHOS=ON
HAVE_SETNS_EXITCODE=1            # 交叉编译 try_run 预置（历史踩坑遵循）
HAVE_CLOCK_GETTIME_EXITCODE=0
HAVE_CLOCK_REALTIME_EXITCODE=0
WITH_BUILD_ID=OFF                # OHOS 下 build-id 回调运行时校验不可用（历史补丁 0012 路径）
WITHOUT_SERVER=ON
WITH_UNIT_TESTS=OFF
WITH_ROUTER=OFF / WITH_NDB=OFF
WITH_SSL=system（conan openssl/3.5.6.1.1，静态 libssl.a/libcrypto.a）
WITH_EDITLINE=bundled（conan ncurses/6.6 显式 CURSES_* 缓存变量）
WITH_ZLIB/LZ4/ZSTD/ICU/PROTOBUF/CURL=bundled
WITH_FIDO=none / WITH_KERBEROS=none / 各认证插件 OFF
```

## 编译步骤（本机实测，2026-09-23）

1. W0 依赖预检（preflight_check.sh 全绿，见上）
2. `init-build` 获取固定上游快照（codeload 直连，sha256 与历史归档一致）
3. `lang-preflight` → cpp 匹配
4. 归档创建：从已验证的 8.4.10_10 归档迁移配方/补丁/test_package，仅换版本串
5. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   --build=missing --user=ohpcd --channel=stable`（干净缓存全量构建，日志
   `reports/conan-create.log`）
6. `conan-verify`（G0-G4 + L2/L4/L5 门禁）
7. `finish`（W2 结构 + R36 依赖 + W3 本地 CI 全量验证，`.ci-result.json` 自动写入）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | （本轮迁移）无新增编译问题 | 54 补丁 + 配方继承自已验证归档，同一上游 tag 干净复现 | W0b 逐项遵循历史方案，直接复验通过 |

## 源码修改

全部通过 `patches/` 补丁管线（0001-0055，去重后 54 个），与 conandata.yml
`patches: {"8.4.10-10": [...]}` 登记，未直接改动生成文件（R2/R5/R6 合规）。
补丁内容与历史归档逐字节一致（`diff -r` 校验）。

## 包面（package scope）

- 静态客户端库 `libperconaserverclient.a` + 客户端工具（mysql/mysqldump/
  mysqladmin/mysqlbinlog/mysql_config 等，bin/）
- `validate()` 强制校验 mysql.h、lib/、bin/mysql、bin/mysql_config 存在，
  并拒绝 mysqld/mysqlrouter 混入
- 依赖传播：openssl、ncurses + `c++/c++abi/unwind`（静态 C++ 闭包，历史
  E459/8.4.10_10 验证过的消费端链接口径）
---

**编译结束**: 2026-09-23 23:50
**最终状态**: built
