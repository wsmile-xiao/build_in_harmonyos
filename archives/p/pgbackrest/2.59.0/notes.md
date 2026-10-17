# Adaptation notes: pgbackrest 2.59.0

## 任务与范围

- 分支：`feat/pgbackrest-2.59.0`（与平台任务登记名逐字符一致）
- 允许改动路径：`archives/p/pgbackrest/`
- 交付：版本级 `conanfile.py` / `conandata.yml` / `manifest.yaml` / `notes.md` / `test_package/` / `patches/`，
  软件级 `manifest.yaml` / `README.md` / `commands.json`

## 上游信息

- 上游版本：2.59.0（GitHub release tag `release/2.59.0`）
- 源码：`https://github.com/pgbackrest/pgbackrest/releases/download/release/2.59.0/pgbackrest-2.59.0.tar.gz`
- SHA-256：`faaf8faa14a6392279654ee216a493fcd07b0c513af4b55fe34faec062cb8875`
- 语言：C（C11）；构建系统：Meson（不是 `./configure` + Makefile）

## 构建系统实况（与任务提示词预期不同，以 tarball 实际为准）

GitHub release 资产是 meson `dist` 产出的**分发 tarball**（根目录存在内容为 `2.59.0` 的 `dist` 标记文件），
`meson.build` 用 `if not dist` 把 `doc/src`、`test/src` 的代码生成工具与 `yaml-0.1` 依赖整体排除。
因此：

- 纯 C 核心编译**不依赖 Perl**，也不依赖 libyaml；上游内嵌 Perl 的部分（文档/测试生成工具）只在 git
  检出树里构建时才被触发，本归档不触碰这些路径。
- 发行包里可用的上游测试面只有 `test/meson.build` 注册的**唯一一个套件 `smoke`**（`test/smoke.py`）。

## 改动清单（2 个补丁，均为可移植性，不改任何断言语义）

1. `0001-meson-define-posix-c-source-on-harmonyos.patch`
   - 文件：`meson.build`
   - 原因：Meson 把 OHOS 目标报为 `host_machine.system()='harmonyos'`，上游只对 `'linux'` 加
     `-D_POSIX_C_SOURCE=200809L`，于是 `gmtime_r`/`localtime_r`/`nanosleep` 未声明
     （`common/type/convert.c:570`、`common/time.c:45` 编译失败）。
   - 做法：为 `harmonyos` 增加同一分支。

2. `0002-smoke-test-loopback-tcp-and-numeric-uid.patch`
   - 文件：`test/smoke.py`（上游测试驱动）
   - 原因（两条平台限制，均已在 `archives/p/postgresql/18.3` 归档中记录）：
     - OHOS 上 `AF_UNIX` 的 `bind()` 返回 `EPERM`，而 smoke 套件用私有 unix socket 启动 PostgreSQL 并把
       `listen_addresses` 置空，服务端无法启动；
     - OHOS 应用 uid（20000000+）在 `/etc/passwd` 里没有记录，`pwd.getpwuid(os.geteuid())` 抛 `KeyError`；
       PostgreSQL 自身对同一情况回退到数字 uid 作为引导超级用户名。
   - 做法：启动前探测 unix socket 可用性，不可用时改用 `127.0.0.1` 回环 TCP（端口改为运行时申请的空闲端口，
     避免与宿主上已有的 PostgreSQL 冲突）；run user 识别在 `KeyError` 时回退到 `str(os.geteuid())`。
   - 影响面：仅改变测试驱动与 PostgreSQL 的连接方式；`initdb → stanza-create → check → full backup →
     加载数据 → incr backup → 抹掉数据目录 → restore → 校验恢复后行数` 的步骤与断言完全不变。
     在支持 unix socket 的平台上走原路径，行为与上游一致。
   - 单独说明：`TMPDIR`（工作目录）由配方指向一个「新建文件属主等于当前 uid」的目录，这是 pgbackrest
     `restore` 的属主校验（`src/command/restore/clean.c.inc:442`）在 HMDFS `/storage` 挂载下的必要条件
     （该挂载对新文件上报的属主是 20001006，不是应用 uid）。

配方另有两处把上游查找与 Conan 产物对齐的适配（不产生补丁）：

- 上游 `dependency('liblz4')` ↔ Conan lz4 包提供的 `lz4.pc`：在 generators 目录生成转发 `liblz4.pc`。
- 上游 `cc.find_library('bz2')` ↔ Conan bzip2 包：把 bzip2 的 include/lib 目录注入 Meson native file 的
  `c_args` / `c_link_args`。

## 安装后重签名

`meson install` 会重写安装产物的 RUNPATH（打包产物因此不含构建机路径），这会使链接器写入的 `.codesign`
段签名失效；HarmonyOS 对签名不匹配的 ELF 拒绝执行（`Operation not permitted`）。`package()` 安装完成后
用平台 `binary-sign-tool sign -selfSign 1` 重新签名（与仓内 `p11-kit` 配方同样手法）。

## 测试

### 上游测试

| 测试入口 | 用例数 | 结果 |
|---|---|---|
| `meson test -C <builddir> --print-errorlogs`（套件 `smoke`，`test/smoke.py`） | 1 | 1 通过 / 0 失败（本机实测 36.3s–38.0s） |

上游分发包里 `meson.build` 只注册了 `smoke` 这一个测试；它对系统上发现的每套受支持 PostgreSQL 跑一遍
完整备份/恢复循环（本次环境发现 PostgreSQL 18.3 一套，故为 1/1）。

### 消费者与平台断言（`test_package/test.sh`，conanrun 环境）

| 类别 | 编号 | 断言 |
|---|---|---|
| 消费者用例 | C1 | `pgbackrest --version` 输出含 `2.59.0` |
| 消费者用例 | C2 | `pgbackrest version` 输出含 `2.59.0` |
| 消费者用例 | C3 | `pgbackrest --help` 列出 `stanza-create` / `backup` / `restore` |
| 消费者用例 | C4 | 非法选项以非零退出码被拒 |
| 鸿蒙特有测试 | H1 | 产物为 ELF64、小端、AArch64 |
| 鸿蒙特有测试 | H2 | 动态加载器为 OHOS musl（`ld-musl-aarch64.so.1`） |
| PC 特有测试 | P1 | 产物含鸿蒙 PC 加载签名段 `.codesign` |
| PC 特有测试 | P2 | 产物无 RPATH/RUNPATH（构建机路径未烤入） |

断言合计 8（消费者 4 + 鸿蒙特有 2 + PC 特有 2），`test_package/conanfile.py` 的 `test()` 是驱动入口，
不重复计入。

## 本地验证

- 两个补丁对干净树 `git apply --check` 全过；应用后与验证树 `diff -r` 完全一致。
- `conan create archives/p/pgbackrest/2.59.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
  → 退出码 0：上游 `smoke` 1/1 + `test_package` 8/8。
- 端到端复核（手工，绕过测试驱动以确认适配本身不掩盖问题）：initdb → `stanza-create` → `check` →
  全量备份 → 插入数据 + `pg_switch_wal` → 增量备份 → 删除数据目录 → `restore` → 启动后
  `select count(*)` 得到 2000 行（与备份前一致）。

## 已知限制

- 上游 `doc/` 的 man/HTML 文档在分发包中已是预生成产物，本适配不重建文档（重建需要 git 检出树里的
  Perl 文档工具链）。
- smoke 套件的连接方式在 OHOS 上为回环 TCP（unix socket 被平台拒绝），因此不覆盖 unix socket 连接路径；
  该路径在支持 unix socket 的平台上仍按上游原样执行。
