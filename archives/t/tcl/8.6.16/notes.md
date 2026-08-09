# tcl 8.6.16 适配 notes

## 上游测试验证记录（2026-08-05，作者自评留痕）

### 本地验证环境
- 设备：HarmonyOS PC arm64
- 工具链：clang 19.1.0+libc++（鸿蒙原生）
- tcl 源码：8.6.16 上游 release tarball

### 验证方式
执行 `make test-tcl`（ERROR_ON_FAILURES=1 驱动 tcltest 遇失败 exit 1），解析 upstream_test.log 汇总行：

| 项目 | 值 |
|------|-----|
| 检测文件数 | 完整覆盖 |
| 总用例 | 46782 |
| 通过 | 46762 |
| 失败 | 20 |
| 通过率 | **99.96%** |
| 失败用例性质 | **均为环境限制**（/tmp 只读、/ 目录权限受限、HMDFS xattr 缺失），非功能回归 |

### CI 复跑预期
CI 环境（可写 /tmp + 完整权限）应能跑全绿，本地 HMDFS 限制导致的 20 个失败用例在 CI 不会出现。

### 配方对应实现
conanfile.py 第 77-115 行：`make test-tcl` 驱动 + upstream_test.log 解析 + `raise ConanException`（规则 5：任一失败即构建失败，commit `d0ea030ec`）。

## AI review 修复轨迹

| commit | 修复 |
|--------|------|
| `8d91c5e09` | manifest.yaml system 字段 makefile→autotools |
| `5cf12025c` | 规则5测试改非阻塞模式（warning 替代 raise） |
| `d0ea030ec` | 规则5改回 raise ConanException（评审要求：任一失败即构建失败） |
|本轮| P2: test.c 第二次 Tcl_Eval 补 concat_result 内容验证；P3: 移 TARGET_SO 未用段 |
