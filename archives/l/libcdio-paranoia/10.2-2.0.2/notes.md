# libcdio-paranoia 10.2-2.0.2 HarmonyOS PC 适配记录

### 对话 #1 [2026-09-21]

- 问题：旧版 Autotools helper、HMDFS 临时目录和发布 BIN/CUE 测试夹具阻塞 OHOS 构建或离线回归。
- 操作：加入六个最小补丁，使用 Conan 私有依赖前缀，完成上游测试、消费者测试和 W3 验证。
- 结果：静态 arm64 Conan 包构建成功；物理音频 CD 测试按环境限制跳过。

## 软件与源码

- 任务：AtomGit task 13088，`libcdio-paranoia` `10.2-2.0.2`
- 任务分支：`feat/libcdio-paranoia-10.2-2.0.2`
- 构建系统：Autotools (`configure` + GNU make)
- 官方源码：`https://ftp.gnu.org/gnu/libcdio/libcdio-paranoia-10.2+2.0.2.tar.bz2`
- SHA256：`186892539dedd661276014d71318c8c8f97ecb1250a86625256abd4defbf0d0c`
- 直接依赖：`libcdio/2.3.0`，已在 HarmonyOS PC Conan 缓存中解析并安装；提交前用 `conan download libcdio/2.3.0 -r=ohpcd --only-recipe` 实测制品仓可用
- 目标：`aarch64-unknown-linux-ohos`

源码包在本地和 HarmonyOS PC 上均用 SHA256 校验；归档根目录是
`libcdio-paranoia-10.2+2.0.2`，Conan 配方使用 `strip_root=True`。

## 依赖与环境证据

适配前用 Conan 验证了 `libcdio/2.3.0` 依赖可用。HarmonyOS PC 侧已验证 clang、GNU make、Python/Conan 与 AtomCode 可用；构建使用 clang/clang++，不依赖 gcc。

构建在 HarmonyOS PC 的独立源码目录完成，工作区临时文件通过 `$TMPDIR` 指向用户可写目录。Conan 配方通过 `PkgConfigDeps` 生成 `libcdio.pc` 的消费者发现信息，并在 OHOS 上给 Autotools 增加 `-all-static`，使配置探测、上游测试和消费者测试使用自包含的 arm64 可执行文件。

## 配方构建步骤

探索阶段使用的等价命令如下（最终以 Conan 配方复现）：

```sh
./configure --prefix="$DEFAULT_PREFIX" \
  --disable-shared --enable-static \
  --disable-example-progs --without-versioned-libs
make -j1
make -j1 check
make install DESTDIR="$TEST_PREFIX"
```

正式 Conan 配方执行：

1. `get()` 下载并校验官方 tar.bz2；
2. `apply_conandata_patches()` 应用 OHOS 与测试夹具补丁；
3. `AutotoolsToolchain` 生成静态配置和 OHOS toolchain 参数；
4. `Autotools.configure()`、`make -j1`、`make check -j1`；
5. `Autotools.install()` 安装头文件、静态库、pkg-config 文件和 `cd-paranoia`；
6. 删除包含构建机绝对路径的 libtool `.la` 文件；
7. `test_package` 调用两个公开版本 API。

## 补丁说明

| 补丁 | 原因 | 性质 |
|---|---|---|
| `0001-config-guess-ohos.patch` | 旧版 GNU `config.guess` 不识别 HarmonyOS，补充 `aarch64-unknown-linux-ohos` 推断 | OHOS portability |
| `0002-config-sub-ohos.patch` | 旧版 `config.sub` 拒绝 `linux-ohos` | OHOS portability |
| `0003-configure-hmdfs-tmpdir.patch` | HMDFS 上 `umask 077` 创建的 configure 临时目录不可继续写入；改为 `022` 并显式 `chmod 755` | OHOS filesystem portability |
| `0004-test-cue-files.patch` | 官方 tarball 的 `cdda*.cue` 引用 `BOING.BIN`，但同包实际提供的是对应的 `cdda*.bin`；修正为匹配的已发布测试数据 | test fixture correctness |
| `0005-endian-cue-files.patch` | endian 回归测试先生成 `cdda-be.bin`/`cdda-le.bin`，但复制的 CUE 仍指向原始文件；生成阶段重写 CUE 文件名 | test correctness |
| `0006-start-track-fixture.patch` | `libcdio/2.3.0` 的 BIN/CUE 驱动会把 image entry 从 1 重新编号；用六个 one-sector data entries 后再放置 7/8/9 音频轨道，保留非 1 音频轨道场景 | dependency-compatible test fixture |

测试补丁不删除断言，也不替换库 API；它们让测试描述与实际随源码发布的 BIN 数据、测试生成文件和已固定依赖的 BIN/CUE 语义一致。`0006` 的测试仍由 `cd-paranoia -Q` 检查音频轨道编号 7/8/9。另从干净源码核对 `test/endian.sh.in` 的 `orig_le_cue_file` 为 `data/cdda.cue`，因此 `0005` 的 `cdda.bin`/`BOING.BIN` 重写路径实际生效。

## 上游测试清点与实测

`make check` 注册 9 项：

- `test/cdda_interface/toc`：1 PASS；
- `test`：5 PASS，1 SKIP（`testparanoia` 需要物理音频 CD）；
- `example`：2 SKIP（示例程序需要物理音频 CD）；
- FAIL：0，XFAIL：0。

结果为 **6 PASS / 3 SKIP / 0 FAIL**，排除明确硬件依赖的 SKIP 后通过率 **6/6 = 100%**。所有测试均在 HarmonyOS PC 实际执行；不是手写结果文件。

## 消费者测试

`test_package/test.c` 链接 Conan 包并调用：

- `cdio_cddap_version()`（`libcdio_cdda`）；
- `cdio_paranoia_version()`（`libcdio_paranoia`）。

该测试确认头文件、两个目标库、libcdio 传递依赖和静态链接关系可供消费者使用。已发布的 `libcdio/2.3.0` CMake 元数据未填充 include 目录，测试包在发现该包后补充其实际 `include/` 路径；这不改变被测包的 Conan 依赖关系。

## 已知注意事项

- 补丁文件中的 `git diff --check` 空白告警来自统一 diff 必需的空白上下文标记（空上下文行和原始制表符），不是补丁应用后新增的源码空白；排除 `patches/*.patch` 后目标变更无告警，六个补丁均已由 Conan 成功应用。
- `cd-paranoia` 是库与 CLI 混合包，因此保留 `package_type = "library"`、`cpp_info.libs`，并在软件级 `commands.json` 声明 `cd-paranoia` 工具。
- 上游物理光盘测试在无光驱的 HarmonyOS PC 上按上游逻辑 SKIP；BIN/CUE 离线回归测试全部通过。
- 当前本机 Git checkout 存在其他任务的既有脏文件；本任务只应提交 `archives/l/libcdio-paranoia/` 及其 `commands.json`，不得带入 `libXext`、`ndiff`、`pcal` 或 feedback 等无关变更。
- `git fetch origin main` 在当前 macOS 环境因 AtomGit SSH 公钥权限失败；本地任务分支从现有 main HEAD 建立，远程 HarmonyOS 编译证据已独立保存。提 PR 前需在具备仓库权限的环境完成最新 main 同步/审计。
- 官方 PF9 预检会把新软件必须提交的软件级 `README.md`、`manifest.yaml`、`commands.json` 判为缺少版本目录层；这是 PF8（R38 命令元数据）与 PF9 的已知冲突。提 PR 时需使用官方 `--no-preflight` 例外，并在正文说明该冲突及已通过的替代检查，不得删除这些元数据。
- HarmonyOS PC 上已实际运行 `python3 scripts/ohc-run.py conan-verify libcdio-paranoia 10.2-2.0.2 --profile ci/conan/profiles/ohos-aarch64`，G1/G2/G3 通过，随后 `zsh ci/conan/build_and_test.sh archives/l/libcdio-paranoia/10.2-2.0.2` 通过，L0/L1/L2/L5 均通过，Conan consumer test 输出两个版本字符串。官方 `finish` 的 G0 clean-verify 另受该设备 `toybox: Unknown command toybox` 的脚本环境问题影响；不影响 Conan 干净构建或目标包测试。
---

**编译结束**: 2026-09-21 18:08
**最终状态**: built
