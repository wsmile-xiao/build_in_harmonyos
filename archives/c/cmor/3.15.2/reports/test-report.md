# cmor 3.15.2 测试报告

## 一、构建与 L1 测试（conan create）

本地 `conan create archives/c/cmor/3.15.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable` **全绿通过**：

- **主包构建**：autotools configure → make → `libcmor.a` 生成成功，头文件 `cmor.h/cmor_func_def.h/cmor_md5.h` 及 `cdTime/` 子目录、LICENSE 正确装包。
- **三个补丁全部应用**（`Apply patch (portability): 0001` / `Apply patch (bugfix): 0002` / `Apply patch (bugfix): 0003`），构建产物源码经 grep 验证含三处修复标记。
- **L1 官方测试（test_package）**：`test_cmor` 编译链接运行成功，**1/1 断言通过**：
  1. 版本宏断言（CMOR_VERSION_MAJOR/MINOR/PATCH == 3.15.2）
  2. `cmor_setup()` 返回 0
  3. `cmor_close()` 返回 0

## 二、上游测试

### 2.1 上游注册清单

`Makefile.in` 的 `test_C` 目标注册 **13 个 C 测试**（`test_a_C` 逐个编译运行）：

| # | 测试名 | 说明 |
|---|--------|------|
| 1 | ipcc_test_code | IPCC 风格端到端写入 |
| 2 | test_singletons | 单例变量 |
| 3 | test_grid | 网格定义 |
| 4 | test_cmor_grid_unstructured_fabi | 非结构化网格 |
| 5 | test_cmor_grid_unstructured_3d_fabi | 非结构化 3D 网格 |
| 6 | test_unit_cat_unique | 单位分类唯一性 |
| 7 | test_cmor_append_associated | 追加关联变量 |
| 8 | test_cmor_append_associated_point | 追加关联点变量 |
| 9 | test_cmor_singleton_and_generic | 单例与通用变量 |
| 10 | test_cmor_nwdFracLut | 查找表变量 |
| 11 | test_cmor_depth_coord_half | 深度坐标半层 |
| 12 | test_sdepth1_float | 深度坐标 float |
| 13 | test_lots_of_variables | 大量变量 |

### 2.2 实测结果（最终闭环）

在 OHOS 环境（ohos-aarch64，clang 15，OHOS 6.0），用**正式 Release `libcmor.a`**（conan create 产物）逐个真实编译并运行 13 个测试二进制（运行时设 `UDUNITS2_XML_PATH` 指向 udunits2.xml）：

- **PASS = 13 / 13（100%）**：全部 exit 0
- **FAIL = 0**
- **SKIP = 0**

### 2.3 从"12 个 SIGSEGV"修复到"13/13 全过"的根因与证据链

初版评估曾判定大部分失败为运行期 hdf5 C++ 绑定 ABI 环境限制；用 **AddressSanitizer 重编 cmor 库**复跑后确证根本原因是 **cmor 库自身的内存错误 + 一个运行期环境变量缺失**，非环境限制。逐一定位如下：

| # | 根因 | ASAN/实测证据 | 修复 |
|---|------|--------------|------|
| 1 | `strncpytrim`（cmor.c）对空字符串输入：`n=0, k=n-1=-1`，循环先判 `in[k]` 后判 `k>0` → 读 `in[-1]` 全局缓冲区越界 | `ERROR: AddressSanitizer: global-buffer-overflow ... in strncpytrim cmor.c:548`；`READ of size 1 at ... 1 bytes to the left of global variable '.str.15'` | 0002 补丁（交换条件顺序 `(k > 0) && (in[k]==' ')`），ASAN 复查不再报错 |
| 2 | `cmor_CV_checkSourceType`（cmor_CV.c）对**未初始化 `regex_t`** 调用 `regfree`：`szTokenAdd` 循环 AER/else 分支在 `regcomp` 之前就 `regfree`；`regcomp` 失败分支也 `regfree`。musl 的 `regfree` 解引用未初始化指针 → SIGSEGV | 崩溃栈 `cmor_write → cmor_setGblAttr → cmor_CV_checkExperiment → cmor_CV_checkSourceType → regfree → SIGSEGV`（-rdynamic 符号栈） | 0003 补丁（统一"先 regcomp 成功再 regexec 再 regfree"），复跑不再崩 |
| 3 | `cmor_setGblAttr`（cmor.c:6397）写 singleton 维度时 `j==-1`（无 singleton 维度）仍访问 `cmor_axes[j]` → `cmor_axes[-1]` 负索引越界 | `ERROR: AddressSanitizer: global-buffer-overflow ... in cmor_create_var_attributes cmor.c:6397`；`55784 bytes to the right of global variable 'cmor_vars'` | 0002 补丁（`j != -1` 才取 `ref_table_id/ref_axis_id`），ASAN 复查不再报该错误 |
| 4 | 上游测试运行未设 `UDUNITS2_XML_PATH` → udunits 单位系统加载失败（"Error reading units system"、"Pa" 解析失败、`cmor_nerrors != 0`） | 带 `UDUNITS2_XML_PATH` 后 `test_singletons` 立即从 rc=1 变 rc=0 | 运行期环境变量，非代码缺陷；测试脚本/run 环境注入 udunits2.xml 路径 |

**验证方法**：cmor 源码对象级 ASAN 重编（clang -fsanitize=address）→ 迭代抓取 `global-buffer-overflow`/`stack-buffer-overflow` 报告定位越界点 → 前 3 个库缺陷逐个修复后在 ASAN 与普通构建双重复验 → `conan create` 固化补丁 → 用正式 Release `libcmor.a` 真实编译运行 13 个上游测试全过。

## 三、测试统计汇总

| 项目 | 数量 |
|------|------|
| 上游注册 C 测试（test_C） | 13 |
| 上游实测通过 | **13（100%）** |
| 上游实测失败 | 0 |
| 上游测试跳过 | 0 |
| test_package 自研断言 | 5（版本宏 1 组 + cmor_setup 返回 0 + setup 后 cmor_nerrors==0 + cmor_close 返回 0 + close 后 cmor_nerrors==0） |
| test_package 结果 | 1/1 通过 |

> 说明：PR body 申报口径以**用例级**为准（测试进程 rc=0 完整通过数）。13/13 均为完整运行（rc=0），无崩溃/跳过。Python 118 与 test_case 38 依赖 python 绑定模块与预置输入文件，平台限定不运行，未计入。
