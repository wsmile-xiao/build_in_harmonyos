# pari-seadate-big 20170418 适配记录

## 对象和上游清点

任务目录名保留 `pari-seadate-big`；对应 PARI 官方 `seadata-big.tar`，发布日期 2017-04-18。

官方 SHA256：`7c4db2624808a5bbd2ba00f8b644a439f0508532efd680a247610fdd5822a5f2`。
原始归档大小 103526400 字节；文件清单为 44 个 `data/seadata/sea*.gz` 和 `README.big`。素数阶覆盖 503 至 797。归档没有源代码、构建文件、测试目录或测试命令；源码语言预检 `--lang other` 返回 `build_system=none`、`detected_language=other`。

| 上游测试类型 | 数量 | 清点依据 |
|---|---:|---|
| 单元测试 | 0 | 归档无测试源码 |
| 集成测试 | 0 | 归档无测试脚本 |
| 其他测试 | 0 | 仅数据和说明文件 |

PARI 官方文档中的 `make test-all` 属于完整 PARI 消费端源码发行包，不属于本数据归档。没有删除或修改上游测试，也没有声称通过不存在的上游套件。

## 适配方案与依赖核验

采用仓库无构建/数据资源模板思路：Conan 下载并校验原始归档，安装 44 个压缩文件和说明文件，不修改上游数据，不增加源码补丁，不编造编译产物。Conan 2.29.1 的合法 `package_type` 不含 `data` 或 `none`，因此显式使用 `unknown`，同时清空 include/lib/bin 信息，声明资源目录。

`settings` 保留四项以符合框架规范，`package_id()` 清空平台信息；数据本身是架构无关的。测试消费者是 C99 程序，使用鸿蒙 SDK 编译。

W0 核验：`conan download pari/2.17.4 -r=ohpcd --only-recipe` 和完整包下载均成功。已发布的 PARI 二进制为 OHOS 6.0 armv8，不可直接在 x86_64 虚拟机执行。big 数据的打包不依赖 PARI，因此主配方无需引入其 GMP/readline/ncurses 依赖树。

实际 PARI 消费还要求基础 `sea0`。在官方 PARI 2.17.4 `src/basemath/ellsea.c` 中，`seadata_cache()` 在加载单个大阶多项式前调用 `get_seadata(0)`；缺少基础数据会使 `ellmodulareqn(503)` 报 `sea503` 缺失。独立实验确认：GP 直接 `read("sea503.gz")` 成功，而接口失败；加入官方基础 `sea0` 后接口返回多项式次数 504、Atkin 类型 1。保留压缩文件即可，解压不能解决缺少基础数据的问题。

补充 PARI 测试使用官方 `seadata-small.tgz` 作为消费端夹具，SHA256 为 `bf5be913472b268df7f1242f94c68113fcacceb30c280507447ff2be62760a8f`。夹具和 GP 都没有打入 big 包。

## 测试设计与实测

`expected.json` 的校验值从通过官方整体 SHA256 验证的归档独立提取，测试运行时不从待测包重算期望值。

| 测试场景 | 数量 | 实测环境 |
|---|---:|---|
| 压缩 SHA256、gzip 完整性、Atkin 向量与整数系数结构 | 44 | Conan 测试驱动主机 |
| 文件清单和上游 README 校验 | 1 | Conan 测试驱动主机 |
| 目标消费者完整读取，验证阶数标头、字节数和 CRC32 | 44 | OpenHarmony 6.0 x86_64 虚拟机 |
| 截断输入拒绝 | 1 | 同一虚拟机，预期非零退出 |
| 鸿蒙可写 TMPDIR 沙箱复制、含空格路径、重命名与重读 | 1 | 同一虚拟机，OHOS 编译分支 |
| **Conan 总计** | **91** | **通过** |
| PARI `ellmodulareqn` 类型、次数和模 1000003 的双变量求值 | 44 | Ubuntu WSL、PARI/GP 2.15.4，补充验证 |

最后一行不计入鸿蒙执行数量。数学期望值使用原始向量的独立 Horner 求值（x=2、y=3）生成；GP 使用自身 API 生成二元多项式后求值比对。

鸿蒙特有测试不以 `uname` 的 Linux 字样判断系统；HDC 开发设备路径读取 `param get const.ohos.fullname` 验证设备；原生 Worker 路径不依赖开发 shell 的 param 命令，C 程序只有在 SDK 定义 `__OHOS__` 时执行真实沙箱文件操作，其他编译产物明确失败。HDC 测试同时核验远端退出码标记与完整测试数量，防止 hdc 返回零但远端脚本失败。

## 复现

在具备工具链和 PARI 基础数据的 HarmonyOS PC 上：

```sh
conan create archives/p/pari-seadate-big/20170418 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

Conan 数据完整性与 C 消费者测试不需要 PARI 程序。原生 OHOS 测试需要环境中提供 `binary-sign-tool`（亦检查仓库常用的 HNP 路径），测试使用 Python 创建的可写临时目录，并显式传给沙箱子进程。

本地 Windows → 虚拟机测试使用 SDK 26.0.0、clang 15、Conan 2.29.1。将 SDK `native/build-tools/cmake/bin` 加入 PATH，指定实际的 Windows build profile 和 OHOS x86_64 host profile：

```powershell
$env:PARI_SEADATA_HDC = (Get-Command hdc).Source
$env:PARI_SEADATA_HDC_TARGET = '127.0.0.1:5555'
conan create archives/p/pari-seadate-big/20170418 `
  -pr:h=.ohc/profiles/ohos-6-x86_64-sdk26 `
  -pr:b=.ohc/profiles/windows-x86_64-build `
  -c:h tools.gnu:make_program=ninja --build='pari-seadate-big/*' -nr
```

这里的 `.ohc/profiles` 是本机环境文件，不属于可移植配方。测试配方从 Conan 的架构设置传入 `OHOS_ARCH`，不会把 x86_64 虚拟机误编成 SDK 默认的 arm64。HDC 由主机 Python 执行，不在 Windows 上加载目标平台的 `conanrun.sh`。

额外数学验证：

```sh
python3 test_package/test_pari.py --gp /实际路径/gp \
  --datadir /Conan包路径/share/pari --base-sea0 /基础数据路径/seadata/sea0
```

## 状态与边界

当前 `built` 表示本地 Conan 构建和虚拟机测试完成，未上传或标记 `published`。测试设备报告 `OpenHarmony-6.0.0.47`，架构 x86_64；没有将这些实测写成 arm64 PC 原生运行结果。数据无架构差异，arm64 原生测试入口已提供，但仍须由实际 arm64 CI/设备执行。

仅本软件归档参与交付，SDL、tinyxml2、libsodium、bmkdep、Boost 和 libXext 的既有本地改动保留。
## 本地 CI 与仓库检查

原始 `ci/conan/setup.sh` 与 `ci/conan/build_and_test.sh` 在 WSL 执行通过（W3，退出码 0），通过仓库 `FinishPipeline.step35_local_ci()` 生成带日志 SHA256 的 `.ci-result.json`，没有手写通过标记。最新完整输出位于 `reports/w3-local-ci.log`。

CI 的 host/build 共用 OHOS profile 是原始脚本行为；本机 profile 将 C 编译转交 Windows SDK，测试明确通过 HDC 执行。主包没有编译或构建依赖。`JUNK_PR_DIFF` 使用本次软件的完整实际新增文件补丁，避免旧 `origin/main` 比较基线混入 upstream 的其他软件以及用户保留的本地改动。源码预下载使用原始 CI 的校验流程；临时 `file://` 地址已由脚本恢复为官方 HTTPS 地址。

L0、L1、L4 通过。数据包没有 bin/lib，原始 CI 的 L2 标记 skip、L5 标记 warn，均为数据包适用范围限制，并非可执行程序通过记录；通用 L1e 也因无 bin/lib/include 而跳过。实际 share/pari/seadata 的完整性、目标端读取及截断拒绝由本包 91 项测试覆盖。

仓库 `tests/run_all.py` 中 10 个套件直接通过；`test_v1220.py` 把 Git 路径固定到鸿蒙 HNP 安装位置，在 Windows 上无法启动。仅在测试进程内把该路径映射到本机 Git 后，原有全部 33 个断言通过。未修改 tests 或 CI 基础设施文件。
## PR #9098 下载超时处理

远端构建 #42798 在 `source()` 下载阶段达到默认 3600 秒限制；103526400 字节归档仅下载到约 46.6 MB，尚未执行消费者编译或测试。Worker 未找到 curl，预下载失败后使用 Conan 内置下载继续传输。日志中的“交互式测试卡住”为通用诊断，不符合此次失败阶段。

Worker 的总预算硬上限为 1 小时，因此撤回此前无效的 10800 秒覆盖，恢复默认 3600 秒。HTTP 下载参考仓库 ASTAP 配方的分段方案：8 个并发连接、每段 2 MiB、每段最多 3 次尝试；只访问原始官方 URL，核验 HTTP 206、完整 Content-Range 和分段长度，拼接后再次核验 103526400 字节总大小和官方 SHA256，成功后才原子替换归档。没有更换镜像、减少数据或删减消费者测试。

下载预算为 2700 秒，单次 I/O 超时不超过 30 秒；使用 HTTPResponse.read1 读取已到达数据，以便持续检查预算，避免服务器慢速滴流导致 read 等待填满缓冲区。分段错误会取消其余任务并清理临时文件。CI 提供 file:// 预下载归档时仍使用 Conan get 校验完整 SHA256。

新增 `test_package/test_download.py`，以真实本地 HTTP 服务覆盖并发上限、分段重试、忽略 Range、错误 Content-Range、截断响应、数据损坏、启动前及传输中的预算耗尽，共 8 项宿主回归。它们单独统计，不冒充鸿蒙或上游原有测试。远端 CI 是否通过仍以同一 Worker 重跑结果为准。

最终本地 W3 实测：在 WSL 空 Conan 缓存及无 curl 的隔离 PATH 下，原始 setup.sh + build_and_test.sh 全流程耗时 932.8 秒（15 分 33 秒），预算保持 3600 秒；没有预下载缓存，实际走官方 HTTPS 分段下载。完整 103526400 字节和 SHA256 校验通过，Conan 91 项及鸿蒙特有测试通过；独立下载回归 8/8 通过。目标为 OpenHarmony-6.0.0.47 x86_64 虚拟机，经 HDC 执行。该次历史日志保留在 reports/w3-parallel-cold-ci.log，计时见 reports/w3-parallel-timing.json；.ci-result.json 由原始流程自动写入，其日志 SHA256 为 f59530c1efc5cd431826c236539fefd164e2879e381e0b4119fc41999fdef5dd。

## 许可证正文来源

数据包中的 README.big 声明 GPL-2.0-or-later，但上游数据归档没有附带其引用的 COPYING。
本目录 COPYING 原样取自官方 pari-2.17.4.tar.gz 的 pari-2.17.4/COPYING，随 Conan 包放入 licenses。
来源：https://pari.math.u-bordeaux.fr/pub/pari/unix/pari-2.17.4.tar.gz
该归档 SHA256：02651d99c391007d384b3fadbc20abc6916b77036f9e496c99e9ce8688ca4b53。

## PR #9098 原生 Worker 缺少 param 命令

远端构建 #42836 在 OpenHarmonyPCDeveloper-CI-021 上耗时 1314.35 秒（约 22 分钟），已完成 50/50 分段、官方 SHA256 校验、数据打包、消费者编译签名及前 90 项检查。失败发生在最后的 OHOS 沙箱测试之前：原生 Python 尝试运行 `param get const.ohos.fullname`，Worker 没有该命令，抛出 FileNotFoundError。此次不是下载超时或编译错误。

修复只移除原生路径对 param 的强制探测；`--ohos` 仍由 Conan 的 OHOS 设置启用，实际 `--sandbox` 调用保持 check=True。C 消费者只有在工具链定义 __OHOS__ 时执行沙箱操作，非 OHOS 产物返回失败。仍验证可写 TMPDIR、真实数据复制、含空格路径、重命名及完整 CRC，不删除或跳过第 91 项。

新增 test_native.py 的 2 项宿主编排回归：没有 shell 工具时仍调用沙箱、沙箱失败必须向上传递。目标子进程在宿主上明确模拟，这两项不计入 Conan 或鸿蒙测试数量。先在旧代码得到 2 项失败，再在修复后 2/2 通过。另以真实 Linux 编译的消费者、完整数据及空 PATH 执行原生驱动：前 90 项通过，沙箱因非 OHOS 产物而失败，确认移除 param 不会让其他平台冒充鸿蒙通过。虚拟机没有原生 Python，实际 OHOS 沙箱继续通过 HDC 验证；arm64 原生完整成功仍待远端重跑。

本次修复后重新执行原始本地 W3：空 Conan 缓存、无 curl、官方 HTTPS 冷下载，经 HDC 在 OpenHarmony-6.0.0.47 x86_64 虚拟机运行全部 91 项，退出码 0，耗时 1002.0 秒（16 分 42 秒），预算 3600 秒。最新日志 reports/w3-local-ci.log 的 SHA256 为 3c13d5f00edc6814ab59372a91bf67e230cd6555e386367fa829e872361f048a，与自动生成的 .ci-result.json 一致；计时见 reports/native-fix-ci-timing.json。原生编排回归 2/2 通过，非 OHOS 真实产物拒绝检查通过。远端 arm64 Worker 修复后是否全过仍待 PR 重跑。
