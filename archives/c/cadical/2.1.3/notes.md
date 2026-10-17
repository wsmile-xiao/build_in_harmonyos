# CaDiCaL 2.1.3 适配笔记

## 状态

- 分支：`feat/cadical-2.1.3`
- Issue：[#2687](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2687)
- 当前状态：本机前置适配完成，OHOS 手工单线程验证与 r10 单包完整 shadow CI 均通过；专属 issue 已创建
- 上游：<https://github.com/arminbiere/cadical/tree/rel-2.1.3>
- 许可证：MIT

## W0 依赖检查

CaDiCaL 自身无第三方 Conan 依赖。已在隔离 Conan home 中查询 `ohpcd` 制品仓，未发现 `cadical` 既有配方，因此本版本是首次适配，无需拆依赖库 PR。

## 源码与构建系统

- 源码 URL：<https://github.com/arminbiere/cadical/archive/refs/tags/rel-2.1.3.tar.gz>
- SHA256：`abfe890aa4ccda7b8449c7ad41acb113cfb8e7e8fbf5e49369075f9b00d70465`
- 构建系统：自定义 `configure` + GNU make，不是标准 Autotools
- 编译器注入：`AutotoolsToolchain` 生成 `conanbuild` 环境，由 configure 读取 `CXX/CXXFLAGS`
- 默认产物：`build/libcadical.a`、`build/cadical`、`build/mobical`
- 上游安装规则：无 `make install`，也不支持 `--prefix`

配方在源码根目录执行 `sh ./configure`，随后执行 `make -j1` 与上游 `make test`。使用 `sh ./configure` 是为了不依赖源码包执行位和 shebang 行为。

最初使用等价 codeload 地址
`https://codeload.github.com/arminbiere/cadical/tar.gz/refs/tags/rel-2.1.3`。
OHOS Conan 2.29.1 会按最终 URL 后缀推断归档格式，因该地址没有 `.tar.gz` 后缀而误按 zip 解包并报 `BadZipFile`。两个地址下载内容的 SHA256 相同，均为上述校验值；配方已改为带 `.tar.gz` 后缀的 GitHub archive 地址。

## 打包决策

只打包库消费者需要的文件：

- `lib/libcadical.a`
- `include/cadical.hpp`
- `include/ccadical.h`
- `include/ipasir.h`
- `licenses/LICENSE`

`cadical` 与 `mobical` 会随上游默认目标构建，因为 `make test` 需要它们，但不复制到 `bin/`。这样本 PR 保持纯库包，不触发软件级 `archives/c/cadical/commands.json` 要求，也不修改版本目录之外的软件级文件。

上游只生成静态库，因此配方保留 `shared` 选项接口但在 `shared=True` 时抛出 `ConanInvalidConfiguration`。

## OHOS 适配补丁

- `0001-run-required-shell-scripts-with-sh.patch`：HMDFS 会丢失或拒绝源码脚本执行位，构建与测试必需脚本统一通过 `sh` 调用。
- `0002-use-tmpdir-for-upstream-test-files.patch`：上游测试临时文件改写 `TMPDIR`，并将 `parcompwrite` 报警从 1 秒放宽到 60 秒，覆盖 HMDFS 的 I/O 延迟。
- `0003-make-api-tests-portable.patch`：C API 测试把 `-std=c++11` 与 `-std=c++17` 均转换为 `-std=c11`，并用 `alarm(1)` 替换 OHOS 缺失的 `ualarm`。
- `0004-serialize-compressed-input-pipes.patch`：用通用 `std::recursive_mutex` 覆盖读模式压缩管道从 `popen()` 创建到 `pclose()` 的完整生命周期，不引入平台条件编译。独立 100 线程探针显示无串行化 69 次失败、仅串行化创建 10 次失败、完整生命周期串行化 0 次失败；递归锁允许同线程重叠持有多个读管道，避免自死锁。

## 上游测试

`make test` 依次执行 7 个测试组：

```text
usage trace api cnf icnf mbt contrib
```

其中 `test/api/run.sh` 驱动 API 测试程序；r10 实际执行 16 个并全部通过。不同测试组数量不能相加为唯一总用例数，以下记录按日志原始分组保留。

消费者测试 `test_package/test.c` 覆盖：

- 空公式求解返回 SATISFIABLE（10）
- 三子句公式得到唯一解 `x1=false, x2=true`
- `ccadical_val` 读取模型
- 单变量矛盾公式返回 UNSATISFIABLE（20）
- 正常释放两个 solver

## 本机验证

Windows 宿主机已完成源码下载、SHA256 校验、源码解包、构建系统检查、配方语法、YAML 解析和补丁顺序应用检查。宿主机缺少 `make/clang++/cmake/ninja` 等工具链，因此不在 Windows 声称 `conan create` 通过；目标 OHOS 结果以下一节真实日志为准。

Windows `tar.exe` 无法处理上游 `src/configure -> ../configure` 相对符号链接；用 Python `tarfile` 解包成功。这是本机解包工具限制，不是源码缺陷，也未作为补丁处理。

## OHOS 手工单线程验证

在 `10.62.220.52` 真机隔离目录中按单线程完成手工验证：

- 使用 OHOS clang 编译 82/82 个库源文件。
- configure 通过 `-DNCLOSEFROM` 走上游在缺少 `closefrom` 时的既有降级路径。
- `libcadical.a` 归档成功，SHA256 为 `230cb8c4b658b4abbc0fd3669c7bfdac607077ec93c93d7278788d44be713397`。
- `test_package` 编译并在 HMDFS 上运行成功，输出 `CaDiCaL signature: cadical-2.1.3` 与 `All CaDiCaL consumer tests passed.`。
- runner exit code 为 `0`；运行目录为 `/storage/Users/currentUser/ohos-test-runs/codex-cadical-2.1.3-manual-r8-20260905-124111-24967`。

以上是手工单包验证，不等同于 shadow CI 汇总通过，不能记录为 `Total: 1 / Success: 1`。

## OHOS 单包 Shadow CI

r10 运行目录：
`/storage/Users/currentUser/ohos-users/codex/cadical-2.1.3-r1/ohpc-ci-shadow/runs/20260905T060200Z-cadical-r10`

失败与修复链：

- r7：API 组 `10 ok, 6 failed`。其中 3 个 C 测试因 `-std=c++17` 用于 C 源码失败，`example_tracer` 写 `/tmp` 后崩溃，`terminate` 使用 OHOS 缺失的 `ualarm`。
- r8：加入 TMPDIR、C 标准转换与 `alarm` 修复后，API 组变为 `15 ok, 1 failed`，仅 `parcompwrite` 因压缩输入管道 I/O 超时失败。
- r9：加入完整 `popen` 生命周期串行化补丁，但补丁 hunk 行号元数据错误，Conan 在 `apply_conandata_patches()` 阶段拒绝应用。
- r10：修正 0004 补丁元数据后完整通过。

提交前仅对 patch 文件清理尾随空白，并缩小 0001 中一处不影响变更内容的上下文范围。已在 Windows 用最终补丁重新应用上游源码，并与 r10 使用的已打补丁源码树逐文件对比完全一致，因此这次格式清理不改变实际构建输入，不需要重复占用真机重跑。

r10 结果：

- `L0_RESULT=pass`
- `L1_RESULT=pass: upstream tests + test_package executed`
- `L2_RESULT=skip: no bin/ dir`（本包有意不发布求解器可执行文件）
- `L4_RESULT=pass: patches clean`
- `L5_RESULT=pass: lib/ has content`
- `Build Summary: Total: 1 / Success: 1 / Failed: 0`

r10 上游测试按日志分组验证：

```text
usage:   35 ok, 0 failed
trace:   79 ok, 0 failed
API:     16 ok, 0 failed
CNF:     228 ok, 0 failed
ICNF:    6 ok, 0 failed
MBT:     1000 generated traces, 1000 ok, 0 failed
contrib: 2 ok, 0 failed
```

`test_package` 输出：

```text
CaDiCaL signature: cadical-2.1.3
All CaDiCaL consumer tests passed.
```

包内容检查确认包含 `lib/libcadical.a`、`include/cadical.hpp`、`include/ccadical.h`、`include/ipasir.h` 与 `licenses/LICENSE`。

## 下一步

当前 recipe、补丁与验证记录已由 r10 覆盖；仅更新 `notes.md` 或 `manifest.yaml` 不需要重跑 CI。若后续再次修改配方或补丁，先确认真机无其他 Conan 重任务、内存余量充足、HMDFS inode 可安全写入，并继续保持单包、单线程、限内存策略。仓库内单包命令为：

```sh
CI_PACKAGES="archives/c/cadical/2.1.3" zsh ci/conan/build_and_test.sh
```

如使用 shadow CI 运行器：

```sh
/path/to/run-ohos-shadow-ci.sh archives/c/cadical/2.1.3
```

重点复核 r10 已确认的门禁：`Total: 1`、L0/L1 通过、上游 `make test` 真实日志、L2 纯库跳过原因、L4/L5 通过，以及 `lib/libcadical.a` 与三个头文件存在。

发布前需将分支非破坏性地同步到最新 `origin/main`，并保持一库一 issue、一分支、一 PR。当前不因 unrelated libXext/libxext 大小写路径冲突修改版本目录外的文件。

## 临时文件

本机下载、解包与隔离 Conan home 均位于 `D:\harmonyos\.tmp\cadical-2.1.3\`，未写入项目根目录。
