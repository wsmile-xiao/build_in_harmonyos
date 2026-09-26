# tarsnap 1.0.41 — HarmonyOS PC 适配说明

## 概况

`tarsnap` 是 Tarsnap 安全在线备份服务的客户端命令行工具集（分块加密备份）。

- 上游：https://www.tarsnap.com/ （官方 autoconf tarball）
- 形态：autotools（官方 tarball 自带生成的 `configure`，无需 autoreconf）
- 产物：`bin/tarsnap`、`bin/tarsnap-keygen`、`bin/tarsnap-keymgmt`、
  `bin/tarsnap-keyregen`、`bin/tarsnap-recrypt` + man 页
- 依赖：openssl/3.0.21、zlib/1.3.2、e2fsprogs/1.47.4（制品仓已发布，真机 conan download 复核二进制）
- 许可证：Tarsnap（顶层 COPYING 为客户端专用许可；捆绑 libcperciva/libarchive 等组件另有各自声明）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 设备 `uname` 返回 `HarmonyOS`，`config.guess` 猜不出三元组 | `configure` 显式传 `--build=aarch64-unknown-linux-ohos`（tnef 1.4.18 先例） |
| 2 | autoconf 的 `configure`/`config.status` 用 `umask 077 && mktemp -d` 建暂存目录，HMDFS setgid 目录下 `drwx--S---` 不可写 | 配方内 `_drop_umask_077()` 就地去除（E114 / DRAFT-6507，同 tnef） |
| 3 | 并行 make 触发 HMDFS jobserver fifo EPERM（E074） | `make -j1` |
| 4 | openssl/zlib 头文件与库路径 | `AutotoolsToolchain` + `AutotoolsDeps` 注入 CPPFLAGS/LDFLAGS/LIBS，configure 内联 `CC=`（R33） |
| 5 | 上游无标准 `make check`，官方测试为自定义 `make test` 目标 | `build()` 直接运行 `make test` |
| 6 | CLI 工具门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游（make test → tests/test_tarsnap.sh .）

6 个场景串行执行，通过后输出 "ALL TESTS SUCCESSFULLY COMPLETED"：

| 场景 | 内容 | 离线可跑 |
|------|------|----------|
| 01-trivial | --help/--version/无参数退出码与输出断言 | ✅ |
| 02-c-dry-run-no-keyfile | 无密钥 dry-run 报错行为 | ✅ |
| 03-c-dry-run-fake-keyfile | fake.keys：--initialize-cachedir + -c --dry-run --print-stats | ✅ |
| 04-c-d-real-keyfile | 需真实 Tarsnap 账号密钥 | ❌ 无 `TARSNAP_TEST_KEYFILE` 时按上游设计自跳过 |
| 05-passphrase | 带口令密钥解密路径（fake-passphrased.keys） | ✅ |
| 06-progress-output | --progress 输出与 .good 基线比对 | ✅ |

### 消费者（test_package/test_tarsnap.sh，15 项断言）

真实执行被适配工具，全部离线：五个工具二进制冒烟（--version/--help）、
`tarsnap-keymgmt` 读取上游 tests/fake.keys 夹具密钥（--print-key-id /
--print-key-permissions）、离线派生只读密钥（--outkeyfile -r 回读校验同
key id）、`--initialize-cachedir`、`-c --dry-run --print-stats`（真实加密/
分块路径，不联网）。

> tarsnap-keygen 完整流程必须联网注册真实 Tarsnap 账号（真机实测），无法
> 离线验证密钥生成，故 keygen 仅做 --version 冒烟，密钥路径用上游夹具。

## 状态

`status: built`（2026-09-24 真机验证）—— conan create rc=0；上游 make test
5 场景 SUCCESS + 04 场景按上游设计 SKIP（离线可跑 5/5 通过）；消费者
test_package 15/15 通过。finish/submit 门禁待执行。
