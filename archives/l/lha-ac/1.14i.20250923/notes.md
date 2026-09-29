# lha-ac 1.14i.20250923 配方与验证说明

## 包名与上游

- 比赛包名/目录：`lha-ac/1.14i.20250923`。
- 上游仓库：<https://github.com/jca02266/lha>。
- 固定源码提交：`0a07ec7fcc8014d0a4a3fa844abf1ea4f8278a28`。
- 源码 SHA256：`711fee59f71081f492b16125a5e0fd1069e44522be788ce4b6e851eeb42da42d`。

## 构建设计

上游 Git archive 只有 `configure.ac`、`Makefile.am` 与源码，没有生成 `configure`。OHOS Worker 只有 `autoconf`、没有 `automake`/`aclocal`，直接 `autoreconf -i -f` 无法完成，因此配方把固定 commit 上 `autoreconf -i -f` 的生成物（`configure`、各级 `Makefile.in`、`aclocal.m4`、`config.h.in`、`install-sh`、`missing` 等 14 个文件）随配方携带，在 `build()` 中解包并刷新时间戳，再为 OHOS 增加 `aarch64-unknown-linux-ohos` 的 `config.sub` 识别。构建和测试统一使用设备自带 Bash，避免 `/bin/sh` 功能不足导致误判。

这 14 个文件以 `prebuilt-autotools.tar.gz.b64`（确定性 tar.gz 的 base64 文本，2278 行）随配方分发，而不是直接提交 `.tar.gz`。原因是 CI Worker 的 `checkout-pr` 步骤用 `curl` 拉取 GitCode 的 `<pr>.diff` 再 `git apply`；该接口对二进制文件只输出 `Binary files ... differ`，不含 `GIT binary patch` 数据，`git apply` 会直接报 `missing binary patch data` 并让 CI 停在 `checkout-pr`。改成文本载荷后 diff 可正常应用，配方在 `build()` 里校验 SHA256 后解码解包，构建行为与产物完全一致。

- 载荷文件：`prebuilt-autotools.tar.gz.b64`，SHA256 `95e1ec431aee64698de0181ef6d539f0052ee1552fbd2dcb7605b5027cce3058`（配方硬校验，不匹配即报错）。
- 载荷内层 tar.gz 的 SHA256：`8305bdf80dcc99bba318e0b6bd8d72f17c2e0ad90bc2b32482374d0fd529250e`。
- 生成方式：对固定 commit 执行 `autoreconf -i -f`，把生成物按路径字典序打包，mtime 归零、uid/gid 归零、可执行脚本显式回写 `0755` 后 gzip，再 base64（每行 76 列），可重复生成同样的字节。显式回写权限是必需的：载荷在 Windows 上打包，NTFS 不保存可执行位，否则解包后 `configure` 会以 `Permission denied` 失败。

上游 `tests/lha-test` 作为真实测试入口运行，共跑两轮：`make check` 跑上游默认集合，
`tests/lha-test all` 再补上 2G/4G 的 `lha-test51`/`lha-test52`。

配方对上游测试只有一处可移植性修改（见 `patches/0001-ohos-compare-preserved-modes.patch`）：

- 位置：`tests/lha-test18` 的三处目录权限断言。
- 原因：真机实测鸿蒙 `/storage` 文件系统不保留目录 `chmod` 结果——`chmod 544` 与 `chmod 766` 的目录
  都报告 `drwxrws--x` / `2771`，所以上游硬编码的 `dr-xr--r--`、`drwxr--r--`、`drwxrw-rw-` 断言在本平台
  不可能成立，与 lha 实现无关。
- 改法：把这三处断言改成“解包后目录权限与源目录权限一致”的等价比较；不删除、不跳过用例，
  也不修改归档、解包、校验等任何功能性断言。
- 消费者测试额外用真实文件权限往返（`chmod 400`）验证 lha 的模式保存/恢复能力。

## 上游测试

上游 `tests/` 内包含：

- `lha-test1` 到 `lha-test20`；
- `lha-test7_lv0`、`lha-test7_lv1`、`lha-test7_lvg`；
- `lha-test51` 与 `lha-test52`，分别校验 2G 和 4G 归档；
- `lha-test6` 与 `lha-test9` 已被上游 runner 注释，属于移除或未完成测试。
- 实际执行集合为 23 项：`lha-test1` 作初始化，后续为 2、3、4、5、7、7_lv0、7_lv1、7_lvg、8、10-20、51、52。

配方执行 `make check` 以及 `tests/lha-test all`，后者会把上游启用的常规用例和 2G/4G 用例都跑一遍。真实结果以 OpenDesk 日志为准，不预先填写通过数。

OpenDesk 真机（任务 `20260924-205214-68cd55-lha-evidence13`，强制重建）实测：

- `make check`：21 个套件、519 条断言，全部 `... ok`；
- `tests/lha-test all`：23 个套件、521 条断言，全部 `... ok`（含 `lha-test51`/`lha-test52`）；
- 两轮合计 1040 条断言，非 ok 结果为 0 条。

## 消费者测试

`test_package/test.sh` 直接调用安装后的 `bin/lha`，包含 16 条真实检查；其中 1 条是独立的完整消费者端到端流程，执行 `archive -> list -> test -> extract -> byte-compare`，另外 15 条为功能断言。真机输出为 `TEST_PACKAGE_RESULT total=16 passed=16 failed=0`、`CONSUMER_WORKFLOW_RESULT total=1 passed=1 failed=0`：

1. 无参数运行时打印 lha 用法/版本横幅。
2. `lha a` 创建非空归档（同时覆盖归档文件存在且非空）。
3. `lha l` 列出成员 `plain.txt`。
4. `lha lv` 详细列表输出 `LV` 压缩级别列（`lha l` 默认不打印压缩方法，因此改用上游的 `lv` 输出）。
5. `lha t` 校验归档完整。
6. 解压后的 `payload/plain.txt` 与原文件逐字节一致。
7. `lha a` 同时归档两个成员。
8. 多成员列表包含 `plain.txt`。
9. 多成员列表包含 `big.txt`。
10. 多成员解压后的 `big.txt` 与原文件逐字节一致。
11. `lha d` 删除成员成功。
12. 删除后的列表不再包含 `plain.txt`。
13. `lha a` 对含子目录的目录树归档成功。
14. 解包后的目录权限与源目录在当前平台报告的权限一致。
15. 解包后的文件权限（`chmod 400`）与源文件一致。
16. **完整消费者端到端流程**：使用安装后的 `bin/lha` 归档两个真实文件，列表确认两个成员，执行完整性校验，解压到全新目录，并对两个文件逐字节 `cmp` 比对；该流程单独输出 `CONSUMER_WORKFLOW_RESULT`，不是对前面断言的重命名或汇总。

脚本不把程序输出回喂给 shell 解析（原写法会把用法横幅里的 `$prefix` 当成变量展开，在 `set -u` 下直接报 unbound variable），而是逐条检查工具写出的文件。

## 真机验证

- 环境：OpenDesk HarmonyOS aarch64，HongMeng Kernel 1.12.0。
- 命令：`conan create archives/l/lha-ac/1.14i.20250923 -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing`。
- 状态：已由任务 `20260924-205214-68cd55-lha-evidence13`（强制重建 `--build=lha-ac/1.14i.20250923`）验证：
  `CREATE_EXIT=0`，上游两轮 1040 条断言 0 失败，消费者检查 16/16 通过，完整消费者端到端流程 1/1 通过。
