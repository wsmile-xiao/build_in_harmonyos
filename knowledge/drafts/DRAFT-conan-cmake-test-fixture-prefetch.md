# DRAFT-conan-cmake-test-fixture-prefetch：CMake configure-time 下载资产预取

> Status: DRAFT | Source: falcosecurity-libs 0.25.4 PR #8977 / CI build 52216

## 问题形状

部分 CMake 项目启用真实上游测试时，并不是下载 Catch2/GoogleTest，而是在
configure 阶段用 `file(DOWNLOAD)` 拉取原始二进制测试数据；同一类项目还会在
第一个 build step 用 URL 驱动的 `ExternalProject_Add` 下载 bundled 依赖归档。
上游随后检查 `${CMAKE_BINARY_DIR}/scap_files/<name>` 或
`${CMAKE_BINARY_DIR}/<name>-prefix/src/<archive>`，并用这些输入编译或运行测试。

这类输入既不是生产依赖，也不能因为 CI 网络受限就关闭整个上游测试。正确边界
是把测试数据纳入 Conan 的可审计 source 输入，再把它放到上游 CMake 已经约定
的二进制目录位置；对 URL 驱动的 bundled 归档也采用同一输入边界。

## 实际失败与最小复现

falcosecurity-libs 0.25.4 的上游 `userspace/libsinsp/test/CMakeLists.txt` 在
测试分支中为 7 个 scap fixture 执行 `file(DOWNLOAD)`。CI build 52216 的根源码
codeload 最终取得成功，但 Worker 先报没有 `curl`，随后 CMake configure 长时间
等待 7 个 S3 fixture；日志最后是 `Configuring done (9181.5s)`，外层
`conan create` 在 3600 秒处超时，两个上游套件和 `test_package` 均尚未执行。

最小复现条件是：

1. 保持 `BUILD_TESTING` 和上游 fixture 测试开关开启；
2. 在干净构建目录中执行 CMake configure；
3. 让 `${CMAKE_BINARY_DIR}/scap_files/` 中不存在 fixture；
4. 观察每个 `file(DOWNLOAD)` 都成为 configure 的外网前置条件。

这与根源码下载失败不同：根源码 URL/SHA 可以完全正确，configure 仍可能被
测试数据下载拖死。

## 可复用修复模式

### 1. 在 recipe 常量中固定每个官方 fixture

在 `conanfile.py` 的 `SCAP_FILES` 常量中记录每个文件的官方 HTTPS URL、文件名和真实 SHA256。falcosecurity-libs 本次
固定了 7 个文件；把 URL 放在 recipe 常量而不是 `conandata.yml`，是为了避开仓库 W3 通用预下载器把大文件部分下载误判为有效缓存：

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| kexec_arm64.scap | 60828200 | fdb49126fcf318baa9b0f23243c89d4573dc339f8386171a66ba2a46adacbecd |
| kexec_x86.scap | 31909696 | e3173873aedbbfab1b078f9ecaa08003a0367d5f46bf1ad88ea5ea35ccb818f6 |
| sample.scap | 139584 | ac88f617b9076087ae204f0342b7d5927bd8361cce8729703ea0b3fc5633120f |
| scap_2013.scap | 27548864 | a022bddc26c4e971827fd54611817b34df8e8c045f56c92fccd96ccd0dd52d8a |
| ptrace.scap | 129372 | 2cf3ee77ac35ffdd63b357aac2c0b721771a5ba362efa45dade2a0344aba0951 |
| mkdir.scap | 177648 | 09bc43ae6c40f6d0649867d211f640aed9af55b360039ef7213d8ee5ead8102b |
| fchdir.scap | 180556 | 6b7c3e8a3d366272efcc7ea9ad7e91e60cdc9677be0c88c1987826641f80ad44 |

不把二进制 fixture 或 bundled 归档直接放入 Git，也不写个人缓存路径或未核验镜像。

### 2. 在 Conan `source()` 中校验下载

对 `scap_files` 条目循环调用 `conan.tools.files.download()`，目标为
`Path(self.source_folder) / "scap_files" / filename`，并传入对应 SHA256。
这样失败发生在可定位的 source 阶段，且构建输入和原始测试数据有稳定身份。

### 3. 在 CMake configure 前 staging 到上游探测位置

`build()` 先执行现有补丁，再把 source 目录中已经校验过的文件复制到
`Path(self.build_folder) / "scap_files"`，之后才调用 `CMake(self).configure()`。
上游 CMake 无需修改：它的原有 `if(NOT EXISTS ...)` 检查会看到文件并输出
`Skipping download, file already present`。若文件缺失，配方应报错，不能静默
回退到未校验内容。

### 4. 为 URL 驱动的 ExternalProject 归档复用同一边界

在修复 fixture 后的 clean W3 中，CMake 不再卡在 scap 数据，但首先对
`uthash` 和 oneTBB 的 URL 下载报 GitHub TLS `SSL_read ... unexpected eof`；
同一构建还声明了 jsoncpp、valijson、RE2 和 zlib 的 URL/URL_HASH。根源码正确
并不能保证这些 bundled 输入可从 CMake 内部网络获取。

把 6 个确实启用的归档固定为 `BUNDLED_SOURCES`（prefix、文件名、官方 URL、
SHA256），在 Conan `source()` 校验到 `bundled_sources/`，然后在 configure 前
复制到 `build_folder/<prefix>-prefix/src/<filename>`。CMake 的原始
`ExternalProject_Add(URL ... URL_HASH ...)` 保持不变；其 download step 会验证
已有归档并解压，不再发起网络请求。不要把未启用的依赖或未经源码确认的归档
盲目加入，否则会扩大 recipe 输入和失败面。

该方式保留上游测试注册、runner 和分母；它只是移动输入获取边界，不改变断言、
测试名或预期结果。只有当上游实际使用的目录不是 `CMAKE_BINARY_DIR`，或 fixture
还参与源码生成时，才应改用该项目自己的 source-dir/ExternalProject 注入方案。

## 最新设备实证（v8-rerun2，2026-09-16）

在 inode 资源恢复且 gate 通过后，使用提交前工作树（含未提交 BUNDLED_SOURCES follow-up）执行任务专属 Conan create；完整日志为 `~/tmp/uc2/falcosecurity-libs-0.25.4/conan-create-fixture-v8-rerun2.log`，SHA256 `07170b6649b19a7fa5af04aef52870acd64439d3da3d1d3cea97db38f175ad64`。Conan 内部返回码为 0：7/7 fixture staging、6/6 bundled archive staging、7/7 fixture download skip、6/6 ExternalProject archive hash match 且无网络回源；`unit-test-libsinsp` 805（804 通过、1 跳过）、`libscap_test` 363/363，真实消费者 1/1、2/2 API 断言通过。

## 当前提交复验

最新提交的 W3 日志为 `reports/w3-local-ci.log`；其完整 `build_and_test.sh` 运行再次确认 7/7 fixture skip、6/6 bundled ExternalProject archive hash match、两套上游测试 1168 runner 用例（1167 通过、1 跳过）和真实消费者 1/1 通过。该 v8-rerun2 是带未提交 follow-up 的探索验证，不能替代最终提交对应的 W3 证据。

## 设备实证

设备日志：`~/tmp/uc2/falcosecurity-libs-0.25.4/conan-create-fixture-v6.log`。

| 验证项 | 结果 |
|---|---|
| Conan source 根 tarball | 官方 codeload，SHA 校验通过 |
| fixture source 获取 | 7/7 进入 Conan 本地下载缓存并通过 SHA 校验 |
| configure 前 staging | 7/7 `Staged pre-fetched scap-file` |
| configure fixture 下载 | 0 次，7/7 `Skipping download` |
| bundled ExternalProject 归档 | 6/6 已校验并 staging 到 `<prefix>-prefix/src` |
| bundled ExternalProject 网络下载 | 0 次；CMake 仅验证已有归档 |
| `unit-test-libsinsp` | 805 执行，804 通过，1 个有证据跳过 |
| `libscap_test` | 363 执行，363 通过 |
| `test_package` | 1 个消费者程序、2 个 API 断言，全部通过 |
| `conan create` | exit code 0 |

## 失败方案与边界

- 只把根源码 URL 从 GitHub archive 换成官方 codeload，只能解决根 tarball
  入口，不能解决 configure 期测试数据或 build 期 ExternalProject 下载；本任务
  CI 52216 和 W3 首次 clean 失败分别证明了这两个边界。
- 关闭 `BUILD_TESTING` 或删除 fixture 测试会破坏上游测试账本，不是本模式的
  修复。若确有平台限制，必须逐项记录未注册/跳过及技术原因。
- 用个人缓存、未核验镜像或无 SHA256 的下载会使 worker 结果不可复现。
- 仅把文件放进 source 目录不够，因为上游检查的是二进制构建目录；目标路径
  必须由上游 CMake 源码确认。

## 查重与新增价值

- E299 只规定对 Conan `source()` 下载错误按传输、HTTP、完整性分类；它没有
  CMake 二进制测试数据 staging 模式。
- E342 处理测试框架 FetchContent/ExternalProject 的 configure 网络依赖，并以
  CMakeDeps 或保留测试分母为核心；本草稿处理的是原始测试数据，不是测试框架。
- E377 处理 ExternalProject 的辅助源码目录绑定；本草稿不构建第三方源码，且
  上游直接探测 `CMAKE_BINARY_DIR/scap_files`。
- is_utf8 configure-download 草稿处理非测试 benchmark 的无条件源码下载并新增
  开关；本草稿保留测试开关和全部可运行用例，不添加关闭 benchmark 的守卫。

因此新增的是“原始测试数据的 checksum-bound Conan source + configure 前
binary-directory staging”这一可跨 CMake/Conan 仓库迁移的模式，而不是重复泛化
的网络故障记录。

## 适用范围

适用于：上游 CMake 测试确实需要原始 fixture，或 bundled ExternalProject 使用
URL/URL_HASH 获取固定归档；下载发生在 configure/build；上游已定义稳定的二进制
目录布局；配方可以从官方地址取得并校验数据。

不适用于：fixture 是源码生成器输入且需要 `ExternalProject`/`FetchContent`
的源码树；上游只有私有运行时服务才能提供数据；或 URL/SHA 无法从权威来源
确认。此时应按对应知识条目处理，不把本模式当作万能离线缓存。

## 官方 S3 端点选择

CI build #49520 证明：根源码 codeload 可成功，而 recipe 在虚拟主机 S3 URL 获取大型 fixture 时仍可能因 `UNEXPECTED_EOF_WHILE_READING` 长时间停滞。对同一官方对象做 Range 探针后，path-style 的 `https://s3.eu-west-1.amazonaws.com/falco-distribution/<key>` 返回 HTTP 206；切换端点时保持对象尺寸和 SHA256 不变，并在 recipe 的 `source()` 中继续执行完整校验。

这不是镜像回退或跳过 fixture。端点必须仍属于原官方 bucket，先用 HEAD/Range 与 SHA256 核对；若官方 path-style 也不可达，应记录网络证据并等待/修复 CI 环境，不能把个人缓存或未核验代理提交为输入。
