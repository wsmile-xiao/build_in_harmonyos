# E677 LAPACKE 包未发布时上游 tester 的传递解法：openblas 内嵌 LAPACKE + conan 2 不可直连测试依赖

> 状态: Draft（待审核 promote）| 日期: 2026-09-29
> 来源: feat/lapackpp-2024.10.26（build_tests=ON 整改，上游测试 0/181 → 177/177）
> 机器可读层: 同目录 `E677-lapackpp-tester-lapacke-via-openblas-transitive-provider.kv`

## 现象

`lapackpp/2024.10.26` 首版 `build_tests=OFF`：上游 tester 构建被
`test/CMakeLists.txt` 两个硬门禁早退——

```cmake
if (NOT blaspp_cblas_found)   # "CBLAS not found; tester cannot be built."
if (NOT lapacke_found)        # "LAPACKE not found; tester cannot be built."
```

上游测试 0/181。而尝试直连依赖又撞上 conan 校验：

```
ERROR: The direct dependency 'openblas/0.3.34' is not used by any
       requirement of component 'lapackpp'
```

## 根因（三个独立机制叠加）

1. **上游门禁是真探针**：tester 校验路径硬用 LAPACKE C 接口
   （`test/lapacke_wrappers.hh` include `<lapacke.h>`），上游
   `cmake/LAPACKConfig.cmake` 用 **try_run**（真编译+真运行）探测，没法靠
   预置变量蒙混。
2. **依赖缺口有传递替代**：`lapacke/3.12.1` 配方未发布制品仓
   （`conan install --requires=lapacke/3.12.1` 实测 Unable to find）。但
   **openblas/0.3.34 内嵌全量 LAPACKE**：`lapacke.h` 等 4 个头 +
   `libopenblas.a` 内 `LAPACKE_*` 符号（nm 实核），且它本就是
   `cblas/3.12.1` 的既有传递依赖。上游 LAPACKConfig 自带
   "LAPACKE in BLAS library" 探测路径——把 libopenblas.a 追加到
   `LAPACK_LIBRARIES` 末位，探针即真实通过，**上游探测逻辑原样生效**。
3. **conan 2 拓扑校验**（2.29 实测）：`requirements()` 里的 direct require
   **必须**被 `cpp_info.requires`（或某 component）引用，否则
   `package_info()` 报错；`dev=True` 不存在（TypeError）；`visible=False`
   也绕不过——该依赖若同时经其他包的常规边进图，合并后节点仍是
   visible=True。直连测试依赖必然污染交付拓扑。

## 解法

核心思路：**不改交付拓扑，让上游自己的探测逻辑找到传递提供方**。

1. libopenblas.a 追加到 `tc.variables["LAPACK_LIBRARIES"]` **末位**——只
   影响测试/探针构建的链接行，交付库链接面与 `cpp_info.requires` 不动。
2. **不直连 require**：经既有传递边访问——`self.dependencies["openblas"]`
   对传递依赖同样可索引（openblas 经 cblas 进图）。direct require 一个
   不加 → conan 校验不触发，package_id 实测不变（8c816a29… 前后一致）。
3. **tester 拓扑（无符号重复的关键）**：参考 liblapack.a 在 libopenblas.a
   之前扫描 → LAPACK_* 符号由参考实现提供，openblas 的 LAPACK 实现成员
   不被拉入；tester 的 BLAS_*/cblas_*/LAPACKE_* 符号全部由 libopenblas.a
   单一提供，链接行上没有 libblas.a/libcblas.a。「参考 LAPACK + OpenBLAS
   BLAS 内核」是标准发行版组合形态。
4. 上游 cblas 门禁变量（`blaspp_cblas_found`/`blaspp_cblas_include`/
   `blaspp_cblas_libraries`）由桥接片段指向 openblas 包（见 E671 的桥接
   手法）。

## 实测证据（lapackpp/2024.10.26，2026-09-29）

- configure 输出实录：`Found LAPACKE library in BLAS library`（try_run 探针
  经 qemu 真实执行）。
- `build/Release/lapackpp_upstream_test_summary.txt`：
  `host_quick: invocation PASS=177 FAIL=0 | test-case PASS=4928 FAIL=0`；
  DEVICE 4 项 NOT_RUN（gpu_backend=none）。
- 交付包 package_id 前后一致（8c816a292964e583c3cc3f24af996b714947264a），
  文件面不变；两轮完整 conan create 结果逐项一致。

## 禁止

- ❌ 直连 `requires("openblas/…")` 而不进 `cpp_info.requires`：conan 2
  package_info() 必报错；为过校验写进 cpp_info.requires 则污染交付拓扑。
- ❌ 预置 `set(lapacke_found TRUE)` 伪造门禁：try_run 是真探针，伪造只会把
  错误后移到编译/链接期。
- ❌ 用 openblas 整体顶替参考 LAPACK/BLAS 后端（改 BLAS_LIBRARIES/
  cpp_info.requires）：测试需求不应反向改变交付面。

## 对下游的直接复用

适用于任何「上游测试硬依赖独立 LAPACKE 包而该包未发布」的场景（lapackpp、
SLATE 族）；更一般地适用于「测试专用依赖要进构建图但不能进交付拓扑」的一切
conan 2 配方：走传递边 + 追加到测试链接行，不直连 require。
