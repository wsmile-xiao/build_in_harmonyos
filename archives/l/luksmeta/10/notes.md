# luksmeta 10 — HarmonyOS PC 适配笔记

## 上游与源码

- 上游仓库：https://github.com/latchset/luksmeta
- 官方发布包：https://github.com/latchset/luksmeta/releases/download/v10/luksmeta-10.tar.bz2
- 发布标签提交：`9e93e212d24eeedf1d61bfd8d9864940a4834b6e`
- SHA256：`a842538ba39680c8319c41dac0bcc082fe40fb43342561761925c0daa1a48f28`
- 构建系统：Autotools；语言：C

## 依赖预检

唯一直接依赖为 `cryptsetup/2.8.8`。适配前执行：

```text
conan download cryptsetup/2.8.8 -r=ohpcd --only-recipe
Download completed
```

配方使用制品仓已发布的依赖，不捎带构建其他归档。

## 适配实现

1. 通过 `AutotoolsToolchain` 自动生成构建/宿主三元组；交叉环境实测为 `build=x86_64-linux-gnu`、`host=aarch64-linux-ohos`。上游发布包的 `config.sub` 已原生支持 `ohos` 和 `linux-ohos`。
2. 为上游要求的 `libcryptsetup.pc` 建立 Conan 私有生成目录覆盖文件，并使用不含 `.la` 的实体库视图，避免历史 `.la` 路径和 OHOS SONAME 软链接装载问题。
3. 安装 `libluksmeta.so`、`luksmeta.h`、`luksmeta.pc` 与 `luksmeta` CLI；打包时删除不可重定位 `.la` 并实体化共享库软链接。
4. 上游测试依赖 GNU `error.h` 且硬编码 `/tmp`。7 个自动生成的可移植补丁加入等价错误报告辅助头，并把临时路径改为 `${TMPDIR:-/tmp}`/`getenv("TMPDIR")`；没有删除、跳过或弱化任何断言。
5. Release 配置默认带 `-DNDEBUG`，而上游 C 测试依赖 `assert()`；配方追加 `-UNDEBUG`，确保断言在实际测试中执行，避免空跑。

## 上游测试清点与实测

上游 `Makefile.am` 注册 `TESTS = $(check_PROGRAMS) test-luksmeta`：

| # | 测试 | 类型 | 结果 |
|---|------|------|------|
| 1 | test-crc32c | C 单元测试 | PASS |
| 2 | test-lm-assumptions | LUKS1 布局测试 | PASS |
| 3 | test-lm-init | 初始化/损坏检测/nuke | PASS |
| 4 | test-lm-one | 单槽生命周期 | PASS |
| 5 | test-lm-two | 多槽生命周期 | PASS |
| 6 | test-lm-big | 大数据与边界测试 | PASS |
| 7 | test-luksmeta | CLI 端到端及 CVE-2025-11568 边界 | PASS |

上游测试共 7 项，实际执行 7 项，通过 7 项，失败 0 项，通过率 100%。构建日志输出机器可读标记 `HMBS_UPSTREAM_TEST_RESULT`。

## 消费者与 HarmonyOS 特有测试

- `test_api.c`：16 个断言，真实调用 `crypt_init`、`crypt_format`、`luksmeta_init/test/save/load/wipe/nuke`，并验证 UUID 与载荷往返。
- `test_ohos.c`：9 个断言，编译期要求 `__OHOS__`，在 HarmonyOS 可写 `TMPDIR` 中验证稀疏文件、`fsync`、LUKS1 格式化及元数据完整生命周期。

消费者测试共 2 个程序、25 个断言，全部通过；其中 HarmonyOS 特有测试 1 个程序、9 个断言，全部通过。

## 交付物

- `lib/libluksmeta.so*`
- `include/luksmeta.h`
- `lib/pkgconfig/luksmeta.pc`
- `bin/luksmeta`
- `licenses/COPYING`

## 已知边界

库操作普通文件中的 LUKS1 头无需 root 或 device-mapper 激活权限；测试覆盖该完整路径。真实块设备的创建、挂载和 device-mapper 激活仍受调用进程权限与系统安全策略约束，这是上游 `libcryptsetup` 的运行环境边界，不影响本包 API 与 CLI 的构建和普通文件验证。
