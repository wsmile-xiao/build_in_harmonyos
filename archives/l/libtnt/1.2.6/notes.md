# libtnt 1.2.6 适配笔记

## 任务背景

- **任务**：HarmonyOS PC 三方库适配 — libtnt 1.2.6
- **库身份**：libtnt 是 Debian 打包名，上游实体为 NIST **TNT（Template
  Numerical Toolkit）**——C++ 科学计算数值模板库（Array1D/2D/3D、
  Fortran 风格数组、CSR 稀疏矩阵视图等）。1.2.6 为官方最终发布版。
- **平台分支**：feat/libtnt-1.2.6（worktree：D:\harmonyos\worktrees\libtnt）
- **样板**：compile-time-regular 3.11.0（header-only 先例，已合入 main）
- **开始时间**：2026-09-16

## 开工前四维核验（2026-09-16 实测）

1. **制品仓**：仓库 main 与 `archives/l/` 无 libtnt 目录
   （`ls archives/l/ | grep -i tnt` → 空）→ 无历史实现 ✓
2. **上游源**：NIST 官网 download.html 列出 `tnt_126.zip`（源码 ~29KB）
   与 `tnt120doc.zip`（文档）；`tnt_3_0_12.zip` 为另一产品线（TNT 3.x），
   与本任务 1.2.6 无关 → 版本锁定 tnt_126.zip ✓
3. **SHA256**：本机下载实测
   `93c7cdd116a6faeb679890a52d5b513055388c7faaac74beea570f8f2edbd7e4` ✓
4. **依赖（W0）**：TNT 为零依赖 header-only 模板库（源码 include 仅为
   C++ 标准库头 iostream/cstdlib/cassert/cmath/sstream/time.h）→
   无需 conan download 依赖预检，天然通过 ✓

## 库特性与形态选型

- **零依赖**：无 requirements，W0 检查天然通过
- **纯 header 交付**：`package_type = "header-library"` +
  `implements = ["auto_header_only_mode"]` + `no_copy_source`，参照
  compile-time-regular 3.11.0 先例
- **扁平布局**：zip 内 21 个 `tnt*.h` 位于压缩包根（无顶层目录），
  package 后为 `include/tnt*.h`（与上游布局一致，消费者
  `#include <tnt.h>`）；**必须 `strip_root=False`**——Conan 2 的 zip
  剥根实现会把扁平条目的公共字符串前缀（"tnt"）误判为根目录并
  IndexError（见「关键坑 1」与知识草稿 E429）
- **许可证**：title 17 U.S.C. §105 公共领域（SPDX: NIST-PD），声明
  内嵌于每个头文件头部统一注释块；zip 无独立 LICENSE 文件，
  `package()` 从 tnt.h 提取首块注释落盘为 `licenses/LICENSE`

## 上游测试清点（R51 三步法第一步：如实申报）

**上游无测试套件**，清点证据（2026-09-16 本机解包实测）：

- `unzip -l tnt_126.zip` → 共 21 个文件，全部为 `.h` 头文件：
  tnt.h（聚合头）、tnt_version.h、tnt_subscript.h、tnt_i_refvec.h、
  tnt_math_utils.h、tnt_array1d/2d/3d.h + 对应 _utils.h、
  tnt_fortran_array1d/2d/3d.h + 对应 _utils.h、tnt_sparse_matrix_csr.h、
  tnt_stopwatch.h、tnt_vec.h、tnt_cmat.h
- 无 tests/ 目录、无 Makefile/CMakeLists/configure、无测试驱动文件
- NIST 官网 download.html 仅提供源码 zip 与文档 zip；
  examples.html 为示例代码片段页（hello-world 级），非测试套件

**对策**（三步法第二、三步）：

- 消费者验证由 test_package 承担：`test_libtnt.cpp` 覆盖 9 类核心
  组件（版本宏 / Array1D / Array2D matmult / Array3D / Fortran_Array2D
  1-based / Vector(deprecated) / math_utils hypot / Sparse_Matrix_CompRow
  (CSR，经 0001 补丁) / Stopwatch）+ 消费者用例（马尔可夫稳态/加权平均）+ 鸿蒙特有（musl 时钟/堆跨页/FPU），44 项
  运行期数值断言（自定义 CHECK 宏，-DNDEBUG 下不被剔除），退出码判定
- PR 模板如实回填：上游测试 0/0（N/A），适配后 test_package 44 项（含消费者用例与鸿蒙特有）

## 上游缺陷与 0001 补丁（真机实测发现，2026-09-16）

**`tnt.h` 聚合头在 clang 下 include 即编译失败**（任何消费者、任何使用
方式，包括空 main）：

- 根因链条：`tnt_sparse_matrix_csr.h` 的
  `Sparse_Matrix_CompRow(int M, int N, int nz, const T *val, const int *r, const int *c)`
  构造函数以 `rowptr_(M, r)`、`colind_(nz, c)` 初始化成员，而
  `rowptr_`/`colind_` 是**非依赖类型** `Array1D<int>`——clang 对类模板
  成员定义中非依赖构造做**解析期急切检查**（GCC 延迟到实例化，故上游
  在 GCC 时代从未暴露），`const int*` 与既有重载 `Array1D(int, T*)`
  （丢 const）/`Array1D(int, const T&)`（类型不符）均不匹配 →
  `no matching constructor`；
- `val_(nz, val)`（`Array1D<T>`，依赖类型）则在使用时实例化后同样报错
  （真机第一轮 12 errors 实证）；
- 上游 zip 无测试、Debian 包仅安装头文件从不编译，此缺陷从未被发现
  （上游死代码级缺陷）。

**补丁 `0001-sparse-matrix-comprow-non-const-ctor-args.patch`**（3 行，
patch_type=bugfix）：构造函数声明+定义的 `val/r/c` 三个指针参数去
const——恰好匹配既有 `Array1D(int, T*)` 重载（i_refvec(T*) 为别名
视图语义，与类文档"Read-only view"一致）；调用方以非 const 缓冲区
构造，访问器 API（val/row_ptr/col_ind）保持 const 不变。test_package
恢复 Sparse_Matrix_CompRow 用例（非 const 栈数组）；链接期另发现
`Stopwatch::running()`（tnt_stopwatch.h:48）与稀疏类的 copy
ctor/operator= 同为**声明未定义**的悬空声明，测试改用
start/stop/resume 断言——组件冒烟共 32 项断言、9 组（消费者用例另 6 项，合计 38）。

## 源码静态排查（本机，编译器缺失的替代验证）

- include 自洽性：`tnt_math_utils.h` 用 fabs/sqrt 且含 `<cmath>` ✓；
  数组类 assert.h/cassert 配对齐全 ✓；`tnt_subscript.h` 纯 typedef ✓
- 平台相关面极窄：唯一系统调用为 `tnt_stopwatch.h` 的 `clock()`
  （`<time.h>`，POSIX/C 标准函数，OHOS musl libc 支持）；
  无 dlopen/无 syscall/无 glibc 专用宏/无 bash shebang → 预扫描零风险
- 老旧语法排查：无 dynamic exception specification、无 auto_ptr、
  无 iostream.h；C++98 模板代码在 C++17（CI profile 口径）下编译
  无已知障碍（TNT 上游即按 ANSI C++ 编写，Debian 长期使用现代
  编译器构建通过）

## 关键坑与决策

### 1. 上游 zip 无顶层目录（扁平结构）→ strip_root 必须为 False

与 GitHub codeload tarball（恒有 repo-name/ 根）不同，NIST zip 是
21 个文件直接位于压缩包根。**不能沿用 tarball 配方常见的
`strip_root=True`**：Conan 2 的 zip 剥根实现用 `os.path.commonprefix`
（纯字符串前缀）检测根目录，21 个 `tnt*.h` 的公共前缀 `tnt` 被
误判为根目录名，随后 `name.split("/", 1)[1]` 直接 IndexError
（conan 2.31.2 本机实测复现）。配方定死 `strip_root=False`，
详见「验证记录」与知识草稿 E429。

### 2. zip 无 LICENSE 文件

NIST 公共领域声明是每个头文件头部相同的 15 行注释块。recipe 在
`package()` 用 `load(tnt.h)` + `split("*/")` 提取首块注释写入
`licenses/LICENSE`——文本逐字来自上游，非手工转写。

### 3. 类名与文件名不一致（消费者易踩）

`tnt_sparse_matrix_csr.h` 定义的类是 `Sparse_Matrix_CompRow<T>`
（非字面的 Sparse_Matrix_CSR）；`tnt_vec.h` 是 pre-1.0 deprecated 的
`Vector<T>`。test_package 按真实类名调用。

## 验证记录

| 阶段 | 内容 | 结果 |
|------|------|------|
| 2026-09-16 本机 | 源码下载 + sha256 实测 | ✓ 与 conandata 一致 |
| 2026-09-16 本机 | 解包清点 21 头文件 + R51 测试清点 | ✓ 上游 0 测试 |
| 2026-09-16 本机 | include 自洽性静态排查 | ✓ 无缺失 include |
| 2026-09-16 本机 | `conan export`（conan 2.31.2） | ✓ 配方导出成功 `#ffa85234c0c8ba1e11e032282fbbe334` |
| 2026-09-16 本机 | `conan source`（隔离副本，E378 姿势） | ✓ 官方 URL 下载 + sha256 校验 + 21 头解出到源码根 |
| 2026-09-16 本机 | `conan export-pkg` + 产物检查 | ✓ package 21 头 → include/ + licenses/LICENSE（NIST 声明逐字） |
| 2026-09-16 本机 | CMakeDeps 消费者生成 | ✓ libtnt-config.cmake / libtnt::libtnt 目标 / 版本 1.2.6 |
| 2026-09-16 本机 | 制品仓探测（W0b） | 匿名 API 被服务端策略拦（"system acceleration policy not enabled"）；archives/ 无 libtnt + 零依赖 → 无重复适配风险，同版本冲突由 CI L0j 核验 |
| 2026-09-16 真机DEV1 | conan create（CI profile） | ✗ 该机无 /data/service/hnp/bin/clang++（CI worker 专属路径），改用本机 ohos-local profile 或换机；内存全程稳定 ~8.2G |
| 2026-09-16 真机DEV2 | conan create（CI profile，conan 2.29.1=CI 同版本） | 编译期抓到 2 个问题：① test 自身 Array3D 误用 operator()（实为三重下标）→ 已修；② Sparse_Matrix_CompRow 上游缺陷 → 当轮先移除用例；内存全程稳定 ~15.8G |
| 2026-09-16 真机DEV2 | 最小化探针（仅 include sparse 头 + 空 main） | 确认 include 即编译失败——clang 对非依赖 Array1D<int> 成员初始化做解析期急切检查（GCC 延迟，故上游从未暴露）→ 定性为上游硬缺陷，改打 0001 补丁修复（见「上游缺陷与 0001 补丁」），恢复稀疏用例（Stopwatch::running() 亦为上游悬空声明，去调用） |
| 2026-09-16 真机DEV2 | conan create 第四/五轮（补丁后） | 编译链接全绿；运行 SIGSEGV → 插桩定位 test_array2d：`A * B` 形状不匹配返回空数组后越界访问（operator* 是逐元素乘非矩阵乘，测试语义用错）→ 改同形状自乘验证，矩阵乘用 matmult |
| 2026-09-16 真机DEV2 | 消费者用例（路径B）| ✓ test_consumer.cpp：马尔可夫稳态幂迭代（v←v·P 收敛至解析解 2/3,1/3 + 归一性 + Stopwatch 计时）+ Array1D 加权平均 = 93.0，6/6 断言；中间踩两个坑：target_link_options 不支持多目标、转移矩阵初版写成转置（行和≠1 不保归一）均已修 |
| 2026-09-16 真机DEV2 | rule12 整改：新增鸿蒙特有测试 test_ohos.cpp | CodexBai 审查 rule12 要求鸿蒙特有测试 ≥1。新增 6 项：musl clock()/CLOCKS_PER_SEC 实测（busy loop 计时>0 量级合理）+ 真机堆 512×512 double（2MB 跨页）精确整数和 + aarch64 FPU 0.1-matmult 误差界 1e-12。断言 38→44 |
| 2026-09-16 真机DEV2 | **`conan create` 终轮（rc=0 全绿）** | ✓ ctest 3/3（libtnt_smoke + libtnt_consumer + libtnt_ohos）Passed，三二进制直跑 32+6+6 全过（合计 44/44）；包 `6b129b068851896169fae42d399fa922d239ce8a`（21 头 + LICENSE，revision `8131dbb3ed3383c633bc39e33ca73e80`）；CI profile（clang15/libc++/17）+ conan 2.29.1（与 CI 同版本）；内存 17.69G→17.71G 可用，净影响为零 |

### 本机验证发现并修复的问题

1. **`strip_root=True` 对扁平 zip 必崩**（conan 2.31.2 实测 IndexError）：
   Conan 的 zip 剥根实现用 `os.path.commonprefix`（纯字符串前缀）检测根
   目录，21 个 `tnt*.h` 的公共前缀 `tnt` 被误判为根目录名，随后
   `name.split("/", 1)[1]` 越界。已改为 `strip_root=False`，并沉淀知识
   草稿 E429（knowledge/drafts/E429-draft-A31F.kv/.md）。
2. **export-pkg 会向配方目录写 build-release/ 生成物**（E378 已有记录）：
   本机验证一律在 `.tmp` 隔离副本进行，归档目录已确清无污染。

## 下一步（真机空闲窗口执行）

```bash
# 真机上（worktree 已同步到分支 feat/libtnt-1.2.6）：
cd <repo-checkout>
conan create archives/l/libtnt/1.2.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64

# 或单包 shadow CI：
CI_PACKAGES="archives/l/libtnt/1.2.6" zsh ci/conan/build_and_test.sh

# 验证通过后：finish → 回填 manifest/test_summary → 提交 → 建 issue/PR
```

- 轻量任务：header-only 无编译，单次 conan create 预计 <5 分钟，
  可排白天短时 smoke 窗口
- 预计风险点：低（纯模板库；唯一外部依赖是标准库头）
