# tarsnap 1.0.41 适配笔记

任务分支：`feat/tarsnap-1.0.41`（路径 A：仅新增 `archives/t/tarsnap/`，零补丁文件）

## W0 依赖检查

| 依赖 | 类型 | 制品仓状态 |
|------|------|-----------|
| openssl/3.0.21 | 必需（configure 检查 openssl/rsa.h，链 -lcrypto） | archives/o/openssl/3.0.21 status: built（已合入 main） |
| zlib/1.3.2 | 必需（configure 检查 zlib.h，链 -lz） | archives/z/zlib/1.3.2 status: built（已合入 main） |
| e2fsprogs/1.47.4 | 必需（`--build=*-*-linux-ohos` 使 $target_os 命中 linux* 分支后，m4/check_linux_ext2fs.m4 硬性检查 ext2fs/ext2_fs.h） | archives/e/e2fsprogs/1.47.4（MateBook 真机 conan download 复核二进制并实装） |

- 可选依赖 bzip2（`AC_CHECK_HEADERS_ONCE([bzlib.h])`）不勾选则跳过，无影响。
- **MateBook 第一步**：配置 ohpcd remote 后 `conan download` 逐一复核上述两个
  依赖的二进制包真实存在（R35，禁止 conan list 判断）；若 3.0.21 二进制缺失，
  备选 openssl/3.5.8.1（status: published），改配方 requires 后重跑。

## W0b 历史经验核验

- 仓库 archives/ 无 tarsnap 历史归档（首次适配）。
- 复用的历史知识（均已在 main 合入验证）：
  - **E114 / DRAFT-6507**（tnef 1.4.18）：autoconf `configure`/`config.status`
    的 `umask 077 && mktemp -d` 在 HMDFS setgid 目录下产生不可写临时目录 →
    配方 `_drop_umask_077()` 就地去除。tarsnap 官方 configure 实测含该模式
    （grep 命中 2 处），config.status 由同一模板生成，一并修复。
  - **E074**：并行 make 触发 HMDFS jobserver fifo EPERM → `make -j1`（R9）。
  - tnef：设备 `uname`=HarmonyOS 时 config.guess 失败 → 显式
    `--build=aarch64-unknown-linux-ohos`。

## 构建系统分析

- 官方 autoconf tarball（tarsnap-autoconf-1.0.41.tgz）自带生成的 `configure`，
  不需要 automake/libtool tool_requires（区别于 tnef 的 maintainer 快照）。
- configure 检查：`zlib.h`（必需）、`openssl/rsa.h` + `openssl/md5.h|ripemd.h|sha.h`
  （必需/可选头）、`bzlib.h`（可选）。链接 `-lcrypto`（AC_CHECK_LIB）、`-lz`。
- 产物（bin_PROGRAMS）：tarsnap、tarsnap-keygen、tarsnap-keymgmt、
  tarsnap-keyregen、tarsnap-recrypt —— 工具类 → 软件级 commands.json（R38）。
- 构建方式：basic_layout in-source；configure 内联 `CC=`（R33），依赖路径由
  AutotoolsDeps 注入 conanbuild 环境的 CPPFLAGS/LDFLAGS/LIBS。

## 测试分析

- **上游无标准 `make check`**；官方测试框架为自定义 `.PHONY: test` 目标：
  `tests/test_tarsnap.sh .`，串行 6 场景，多个 check/断言，通过输出
  "ALL TESTS SUCCESSFULLY COMPLETED"。
- 场景 04（real keyfile）需要真实 Tarsnap 账号密钥 `TARSNAP_TEST_KEYFILE`，
  未设置时**按上游设计自跳过**（exitfile 写 -1），属 sanctioned skip，报告时
  如实标注 skipped，不计入失败。
- valgrind 缺失时逐 check 自动禁用（shared_valgrind_functions.sh），不影响。
- `libm-bench` 类无；06 场景输出与 .good 基线逐字比对，注意 locale/编码环境
  对输出的影响（MateBook 上如失败先查 LANG）。
- 消费者测试 `test_package/test_tarsnap.sh`：15 项断言，全部离线
  （五工具 --version 冒烟 + keymgmt 读 fake.keys 密钥/打印 key-id/派生只读
  密钥 → initialize-cachedir → dry-run 模拟归档），真实执行被适配工具
  （R34 工具类）。
- **keygen 离线限制（真机实测）**：tarsnap-keygen 完整流程必须联网向
  Tarsnap 服务器注册真实账号（keygen_network_register()，无账号报
  "No such user"），无法离线验证 keygen 生成密钥 → 密钥路径改用上游
  tests/fake.keys 夹具（与上游场景 03 同款），keygen 仅做 --version 冒烟。
- 真机第一轮消费者测试在 keygen 断言处失败即源于上述限制，修复后 15/15 通过。

## 相对上游的偏离

1. `_drop_umask_077()`：环境适配（E114），非源码改动，无补丁文件。
2. `--build=aarch64-unknown-linux-ohos`：config.guess 平台缺口，运行参数。
3. 测试走 `make test`（上游本无 check 目标），等价官方入口。
4. 无 patches/；conandata patches: {}。

## 状态（2026-09-24 MateBook 真机验证完成）

- [x] W0：openssl/3.0.21、zlib/1.3.2、e2fsprogs/1.47.4 二进制包复核（R35）
- [x] W3：conan create rc=0（configure + make -j1 + make install，5 个二进制全部产出）
- [x] 上游 make test：01/02/03/05/06 SUCCESS + 04 按上游设计 SKIP（离线可跑 5/5）
- [x] conan test：test_package 15/15 消费者断言通过（fake.keys 夹具方案）
- [ ] finish/submit 门禁（W2-W5，`.ci-result.json` 由工具写入）
- [ ] PR 绑定平台任务；PR 标题 `【积分赛】`前缀

## Windows 阶段已做（静态检查，未冒充真机验证）

- 官方 tarball 下载 + sha256 核验：bebdbe1e6e91233755beb42ef0b4adbefd9573455258f009fb331556c799b3d0
- configure.ac / Makefile.am / tests/ 体系人工审读（umask 077 命中 2 处、
  bin_PROGRAMS、test 目标接线、04 场景跳过逻辑均已核实）
- 配方与 test_package 编写；Python/sh 语法静态检查
---

**编译结束**: 2026-09-24 23:26
**最终状态**: built
