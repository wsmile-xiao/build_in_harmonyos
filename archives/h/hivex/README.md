# hivex

**Windows 注册表 hive 文件读写库** — 纯 C 实现，读、改、写 Windows 注册表的
二进制 hive 文件；是 libguestfs / virt-v2v 访问客户机注册表的后端。

- 上游仓库：https://libguestfs.org/（源码分发：https://download.libguestfs.org/hivex/）
- 许可证：LGPL-2.1-only（上游 LICENSE 明确 "LGPL v2.1, but not later versions"）
- 版本：1.3.24（autotools；tarball 自带 `configure` 与内置 gnulib，无需 autoreconf）

## 产物

| 产物 | 说明 |
|------|------|
| `lib/libhivex.a` | 静态库（R26：系统同名库隔离，默认静态） |
| `include/hivex.h` | 公共头文件 |
| `lib/pkgconfig/hivex.pc` | pkg-config 元数据 |

本包**只交付库**。上游同一 tarball 还带 `hivexsh`（交互式 shell）与 `hivexml`
（导出 XML）两个 CLI，二者用**手写 getopt**（选项串 `"df:wu"` / `"dku"`），
`--version`、`--help` 都会被判为非法选项并以 `EXIT_FAILURE` 退出，无法通过
门禁的 L2 smoke test；且 R38/PF8 要求任何 `bin/` 载荷必须配软件级
`commands.json` 与 tool 包类型。故 `package()` 中删除 `bin/`，需要 CLI 的消费者
从同一 tarball 自行构建。

## OHOS 适配要点

- **E007/E072 平台三元组**：OHOS 原生构建（host=build）profile 不传 `--host`，
  configure 回落到 `build-aux/config.guess`；2022 版 GNU config.guess 没有
  HarmonyOS 分支，直接报 `cannot guess build type; you must specify one`。
  `build()` 内先调用仓内 `scripts/patch-autotools-ohos.pl`，再按其等价逻辑
  **幂等补齐**：脚本第 2.3 步（config.sub 的 kernel-os 白名单加 `linux-ohos*`）
  的守卫写成 `unless (/linux-ohos/)`，而它自己第 2.1 步刚写入
  `basic_os=linux-ohos` 文本，守卫因此命中、该步被静默跳过（脚本仍自评 4/5
  通过），configure 随后报 `Kernel 'linux' not known to work with OS 'ohos'`。
  补齐后三元组为 `aarch64-unknown-linux-ohos`。**不使用** `--build/--host` 绕过
  （autoconf 会当成交叉编译，跳过全部 `AC_RUN_IFELSE`，产出错误 config.h）。
- **E490 helper 执行位**：`configure`/`config.guess`/`config.sub`/`install-sh`/
  `missing` 被生成的 Makefile 直接执行，某些适配路径复制源码时会丢 `+x`
  （`/bin/sh: <b>/configure: Permission denied`，Error 126）。配方按需补执行位，
  本机模式已正确故实跑为 no-op。
- **依赖全关**：`--disable-ocaml/--disable-perl/--disable-python/--disable-ruby`
  （语言绑定不在范围内）、`--disable-nls`（configure.ac 无条件
  `AM_GNU_GETTEXT([external])`，关闭后不再需要 msgfmt/xgettext/libintl）、
  `--without-readline`（仅 hivexsh 行编辑用）。libxml2 不提供，hivexml 子目录
  由 `HAVE_LIBXML2` 条件自动排除，因此本包无任何外部依赖。
- **shared 被拒绝**：configure.ac 用 `/usr/bin/ld --help` 探测
  `VERSION_SCRIPT_FLAGS`，OHOS 无该文件 → 退化成 Solaris 形式 `-Wl,-M -Wl,`，
  lld 无法解析；该标志只出现在 `libhivex.so` 链接行，故默认静态构建干净，
  `shared=True` 在 `validate()` 中直接拒绝。

## 测试统计（双口径）

- source_declared_total = 1（`lib/Makefile.am`：`check_PROGRAMS = test-just-header`、
  `TESTS = test-just-header`；ocaml/perl/python/ruby 绑定已关闭，extra-tests 被
  `ALWAYS_FALSE` 永久排除）
- configured_executable_total = 1
- executed_passed_total = 1（层 1 `make check`：`PASS: test-just-header`，
  `TOTAL 1 / PASS 1`）
- 上游通过率：**1/1（100%）**
- 层 2 `test_package` 消费者端到端：**37/37 断言**（ctest 1/1，0 失败）——
  两阶段生产者/消费者工作流，覆盖 REG_SZ/REG_DWORD/REG_QWORD/REG_MULTI_SZ/
  REG_BINARY 五种类型的写入与读回、键值计数、parent 链、整树递归遍历与错误路径
- 门禁：`conan-verify` G0/G1/G2/G3/G4 全 PASS；W3 本地 CI 模拟（L0/L1/L3/L5）通过
- 详情见 `1.3.24/reports/` 与 `1.3.24/manifest.yaml`
