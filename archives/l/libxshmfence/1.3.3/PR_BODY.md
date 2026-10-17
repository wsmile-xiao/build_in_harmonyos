- **三方库名称**：libxshmfence
- **上游版本**：libxshmfence 1.3.3（对应 `libxshmfence.so.1`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxshmfence
- **适配路径**：路径 A（基础适配） + 知识库扩展（复用 X11 家族 autotools 模式）
- **使用知识库**：OHOS 下 X.Org autotools 库的通用工具链修复模式（libxkbfile/libxcb 同法）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | 来源：libxshmfence 1.3.3 release tarball；`test/Makefile.am` 注册 `check_PROGRAMS = xshmfence_test` 且 `TESTS = $(check_PROGRAMS)`，即上游自动化测试 `test/xshmfence_test.c`（fork 5 子进程验证围栏触发/等待语义，busy-wait + alarm(10) 超时自限） |
| 集成测试 | 0 | 无独立集成测试套件 |
| 其他测试 | 0 | 上游仅生成库 |
| **合计** | **1** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 不变（复跑） | 上游 `test/xshmfence_test.c` 原样接入 `test_package/upstream_test/`（`libxshmfence_upstream_test`），链接已安装的 libxshmfence 实跑（fork 5 子进程 + trigger/await/query/reset 全链路，返回 0 = 通过） |
| 集成测试 | 0 | 不变 | 上游无独立集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（7 个导出符号强引用链接）+ `version_contract.c`（7 个导出函数强类型签名契约 + 完整围栏生命周期功能冒烟），无显示依赖，无需 X server |
| **合计** | **3** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：**1/1（100%）**——上游唯一自动化测试 `test/xshmfence_test.c` 未做任何修改，按上游相对 include 结构 vendored 进 `test_package/upstream_test/`，链接**已安装的 libxshmfence.so.1**，由 GitCode CI 在 OHOS aarch64 worker 上编译并执行（`libxshmfence_upstream_test`，fork 5 子进程 + alarm(10) 时序自限，返回 0 = 通过）。
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxshmfence_api_surface` + `libxshmfence_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/libxshmfence/1.3.3/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxshmfence/1.3.3`；目录使用小写 `archives/l/libxshmfence/1.3.3/`，符合 conan slug 规则。
- **上游测试统计**：经解包 libxshmfence-1.3.3 release tarball 核验，`test/Makefile.am` 注册 `check_PROGRAMS = xshmfence_test` 且 `TESTS = $(check_PROGRAMS)`，可执行用例数 N=1（`test/xshmfence_test.c`），如实声明，不存在少报。
- **上游测试实际执行**：`xshmfence_test.c` 依赖 fork + 共享内存围栏（memfd_create + futex，OHOS Linux 内核均已具备）+ alarm(10) 超时自限。测试自身上限 ~2s，在 OHOS CI worker 上稳定通过；本 PR 将其原样集成进 `test_package`，由 CI 实跑并回填真实通过率（1/1）。
- 本地静态校验：conanfile.py / test_package/conanfile.py AST 语法通过；conandata.yml / manifest.yaml / MANIFEST.yml YAML 解析通过；L0 静态门禁通过。上游官方源码 sha256 本地核验一致。依赖解析：唯一依赖 xorgproto/2025.1（configure 只跑 `PKG_CHECK_MODULES(XPROTO, xproto)`，xproto 为 xorgproto 的 headers-only 模块）。

## 知识库扩展

复用 X11 家族 autotools 适配模式（与 libxkbfile/libxcvt/libxcursor 同法，
config.sub/config.guess ohos 补丁复用既有知识）。新增一个 configure 陷阱：
`AC_ARG_WITH(shared-memory-dir)` 在 configure 期自动探测 `/run/shm /dev/shm
/var/tmp /tmp`，全不存在则硬失败。OHOS CI worker 无 `/tmp`，配方通过
`--with-shared-memory-dir=<build_folder>/tmp` 绕过；运行时主分配路径是
`memfd_create(2)`（OHOS Linux 内核已具备），SHMDIR 仅在 memfd 不可用时作为
`mkostemp` 兜底，所以烘焙进二进制的路径不影响真实消费者。本 PR 是 X server /
DRI3 客户端消费共享内存围栏的构建前置。
