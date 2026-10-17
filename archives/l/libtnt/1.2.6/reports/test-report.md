# libtnt 1.2.6 测试报告（前置阶段）

> 状态：**真机验证全绿（conan create rc=0，32/32 断言通过）**
> 生成时间：2026-09-16

## 本机已完成的验证

| # | 项目 | 方法 | 结果 |
|---|------|------|------|
| 1 | 源码完整性 | 下载 https://math.nist.gov/tnt/tnt_126.zip 并 `sha256sum` | `93c7cdd1...2edbd7e4`，与 conandata.yml 一致 |
| 2 | 上游清点 | 解包列目录 | 21 个 `.h`，无构建系统、无测试套件、无 LICENSE 文件 |
| 3 | R51 测试清点 | 同上 + NIST 官网站点核对 | 上游 0 测试（证据链见 notes.md / test_package/MANIFEST.yml） |
| 4 | include 自洽性 | grep 全量头文件 include 与所用 C 函数交叉核对 | 无缺失（cmath↔fabs/sqrt、cassert↔assert 配对齐全） |
| 5 | 平台风险预扫 | 源码 grep：dlopen/syscall/glibc 宏/bash shebang/老式 C++ | 零命中；唯一系统面是 `clock()`（标准 C） |
| 6 | 配方语法 | `conan export`（本机 conan 2.31.2） | ✓ 通过，revision `#ffa85234c0c8ba1e11e032282fbbe334` |
| 7 | W0 依赖 | requirements 为空 | 零依赖，天然通过 |
| 8 | source() 全链路 | `conan source`（.tmp 隔离副本） | ✓ 官方 URL 下载、sha256 校验通过、21 头解出到源码根 |
| 9 | package() | `conan export-pkg` + 产物检查 | ✓ include/ 21 头 + licenses/LICENSE（NIST 公共领域声明逐字提取自 tnt.h） |
| 10 | 消费者生成 | `conan install -g CMakeDeps` | ✓ libtnt-config.cmake、libtnt::libtnt 目标、版本 1.2.6 |
| 11 | strip_root 行为 | conan 2.31.2 unzip API 实测 | ⚠️ 扁平 zip 下 `strip_root=True` 必崩（IndexError）→ 配方已定 `strip_root=False`，知识草稿 E429 |

## 真机执行结果（2026-09-16，DEV2 10.62.178.77，conan 2.29.1=CI 同版本）

| # | 项目 | 命令 | 判定 |
|---|------|------|------|
| 1 | conan create | `conan create archives/l/libtnt/1.2.6 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` | **✓ rc=0**；包 6b129b068851896169fae42d399fa922d239ce8a，21 头 + LICENSE，revision 8131dbb3ed3383c633bc39e33ca73e80 |
| 2 | test_package | 同上（create 内置） | **✓ libtnt_smoke 1/1 Passed；直跑 `all 32 checks passed`（9 组组件）** |
| 3 | 内存护栏 | 构建前后 MemAvailable | 17.69G → 17.71G（净影响为零，无内存压力） |
| 4 | L4/L5 | GitCode PR CI（build_and_test.sh） | 待 PR 阶段执行 |

真机迭代过程（5 轮编译 + 1 轮运行期定位，全部记录于 notes.md 验证记录）：
修复了 2 个测试自身 API 误用、发现 2 个上游硬缺陷（tnt.h include 即编译
失败 → 0001 补丁；Stopwatch::running() 声明未定义 → 测试规避）与 1 个
上游语义陷阱（Array2D operator* 逐元素乘，形状不匹配返回空数组）。

## 已知限制

- 上游硬缺陷 2 处（详见 notes.md）：tnt.h 在 clang 下 include 即编译
  失败（0001 补丁修复）；Stopwatch::running() 与稀疏类 copy
  ctor/operator= 声明未定义（悬空声明，消费者不可调用）。
- 本机（Windows）无 C/C++ 编译器与 OHOS SDK，最终以真机 clang 15
  实测为准（已通过）。
