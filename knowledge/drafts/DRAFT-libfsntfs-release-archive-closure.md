# DRAFT-libfsntfs-release-archive-closure：libyal 多组件发布包闭包审计

> 状态：DRAFT，路径 B（贡献创新）候选，最终分类与知识条目编号以官方审核为准
> 触发库：`libfsntfs/20251028`
> 主题：证明 libyal 多组件 Autotools release archive 是自包含输入，并对镜像回退与测试 fixture 能力做可复核分类

## 新增问题

`libfsntfs` 不是只含一个主库目录的普通 Autotools 项目。它的发布包需要同时携带
17 个同族 libyal 组件目录，以及已经生成的 `configure`、`aclocal.m4`、`config.guess`、
`config.sub` 和 `Makefile.in`。上游 Git 提交与正式发布包的文件闭包不同，单看版本号
或主库源文件不能证明 Conan 输入完整。

本轮还遇到发行版源包常见的来源边界：上游 release URL
`libfsntfs-experimental-20251028.tar.gz` 当前不可用，但 Debian 的
`libfsntfs_20251028.orig.tar.gz` 可获取。镜像只能在文件名、SHA-256、关键源文件和
上游提交关系都可审计时使用。

## 可复用方法

### 1. 先做源码闭包审计

从 `configure.ac`、顶层 `Makefile.am` 和库目录 `Makefile.am` 提取本地组件清单，逐项
检查目录存在；同时检查发布包所需的生成文件存在。对 `libfsntfs/20251028`，闭包为：

- `libbfio`、`libcdata`、`libcerror`、`libcfile`、`libclocale`、`libcnotify`
- `libcpath`、`libcsplit`、`libcthreads`、`libfcache`、`libfdata`
- `libfdatetime`、`libfguid`、`libfusn`、`libfwnt`、`libhmac`、`libuna`
- `configure`、`aclocal.m4`、`config.guess`、`config.sub`、`Makefile.in`

任何一项缺失都应在 `build()` 的早期报告为“源包非自包含”，而不是等到 configure
报错后猜测依赖。

### 2. 区分 Git 快照、正式发布包和发行版 orig

验证镜像时至少保留以下证据：

1. 固定下载 URL、显式文件名和 SHA-256；
2. 上游目标提交及提交时间；
3. `configure.ac`、`Makefile.am`、库目录 Makefile 和公开头文件模板等关键文件的
   内容比对；
4. 归档中的本地组件目录和生成文件清单。

这样可以把“上游 release URL 暂时不可用”处理成可复核的源包替代，而不是使用浮动
下载地址、最新版本或未经验证的本地缓存。

### 3. 以依赖边界约束配方

当归档已经包含完整同族源码时：

- Conan `requires` 保持为空，除非另有独立、可发布的外部依赖；
- 不调用未锁定的 `synclibs.sh` 或 `git clone`；
- 不在当前库 PR 中新增 17 个依赖库的配方；
- 可选 `libfuse`、Python 等功能单独关闭并记录，不把关闭可选能力误写成依赖缺失。

该方法的重点是“先证明输入完整，再冻结依赖边界”，不是把所有 bundled 源码都改造成
静态 staging 依赖。

### 4. 分层记录上游测试能力

顶层 Autotools runner 的测试结果要分别记录：

- runner 是否被 `make check` 调用；
- 测试程序是否编译并执行；
- 测试所需的 `input`/fixture 目录是否存在；
- 最终结果是 PASS、SKIP 还是 FAIL。

本轮 `make check` 共 4 个顶层 case，2 个 PASS、2 个 SKIP、0 个 FAIL。两个 SKIP 是
输入驱动测试发现发布归档不包含 `input` 目录，属于测试数据能力边界；其余测试仍然
实际执行。不能写成 `0/4`，也不能把 `2 SKIP` 记为 `4/4 PASS`。

除上游 runner 外，适配侧还要单独标记平台专项消费者测试。libfsntfs 的
`test_package/test_ohos.c` 仅在 `__OHOS__` 目标下编译，验证非 `/tmp` 的 `TMPDIR`
临时文件读写和清理，共 5 个断言。它证明的是 HarmonyOS HMDFS 运行环境下的
消费者可执行性，不冒充上游单元测试，也不改变上游 runner 的 PASS/SKIP/FAIL 统计。

## 与已有知识的差异

- `E277` 处理缺失 vendored 依赖时在构建期 staging；本条处理发布包已带齐同族源码时
  的自包含性证明和“不要拆依赖”的入口决策。
- `E337/E058` 处理 Git 快照缺少生成文件时的 bootstrap 或生成文件归档；本条处理生成
  文件已存在的 release archive 身份核验，以及官方 release URL 不可用时的固定 orig
  镜像回退。
- `E270` 处理外部 CID/基线测试对象的离线闭包；本条不引入外部测试对象，只核验源码
  包内目录和顶层 runner 的 fixture 能力。
- `E2147` 处理嵌套 fixture 的唯一计数与重复终态；本条只处理 Autotools 顶层 runner
  的输入目录缺失分类。
- `E087/E330/E011` 已覆盖 HMDFS shell、权限和执行机制；本条只引用这些机制在
  `libfsntfs` 中的验证结果，不重复申报。

## `libfsntfs` 实证

- 源包：Debian `libfsntfs_20251028.orig.tar.gz`
- SHA-256：`9edbd1982f8868121391a35696e34c413794a5d88cd91e4ec8b183133eb577f6`
- 上游提交：`f8994835320b989894fe53970c721efed83df220`
- 17 个本地 libyal 组件目录均存在
- 生成 Autotools 文件均存在
- 关键源文件与上游提交对应文件一致
- Conan 配方未新增外部 Conan 依赖，并对缺失闭包主动失败
- 真机 Shadow CI：总体 1/1 成功
- 上游 `make check`：2 PASS、2 SKIP、0 FAIL
- `test_package`：9/9 通用断言通过，5/5 OHOS 专项断言通过
- L1e 负向依赖验证通过

## 路径 B 候选说明

本草稿贡献的是一套可迁移的“发布包身份、源码闭包、依赖边界、测试 fixture 能力”
联合审计方法，不是把现有 HMDFS 通用 workaround 换名重复提交。它适用于其他
libyal 系或类似多组件 Autotools 发布包，可在 Conan 构建前提前判断：

1. 当前源包是否真的可离线、自包含；
2. 镜像回退是否仍对应目标上游版本；
3. 是否应拆出独立依赖库；
4. 测试跳过是否由缺失 fixture 引起而非代码失败。
5. 是否存在只在 OHOS 目标编译的专项消费者测试，并且其断言对应真实的平台运行时约束。

本条目作为路径 B（贡献创新，10 分候选）提交，最终是否认定及最终编号由知识库维护
者和官方评审决定。
