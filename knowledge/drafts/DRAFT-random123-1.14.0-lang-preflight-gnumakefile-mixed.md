# DRAFT-random123-1.14.0：lang-preflight 对仅有 GNUmakefile 的 C/C++ 库误判 mixed

> Contributor: pc5-13 | Status: Draft | Updated: 2026-09-07
> Source: random123 1.14.0 HarmonyOS PC 适配（task random123-1.14.0-r01-pc5-13）
> 领域：语言预检（R47 / lang_detect）/ 构建系统识别 / Conan 2 header-only 配方

## 背景

random123（D. E. Shaw Research）是 header-only 计数器型随机数库，顶层仅有
`GNUmakefile`（无 CMakeLists.txt / Makefile / configure.ac / meson.build）。
`ohc-run.py lang-preflight random123 1.14.0 --src <src>` 判定
`detected_language=mixed（build_system=none）`，自动写入 env_unsupported 终态。

源码统计：cpp 25 个 / c 11 个 / bash 2 个（辅助不计入主体），cpp 主体占比
25/36 = 69.4%，低于 70% 单语言阈值。

## 错误签名

```text
lang-preflight.*detected_language.*mixed|build_system.*none|
无 manifest 且主体占比 69% < 70% → mixed|env_unsupported.*mixed
```

## 根因

`lang_detect._manifest_scan` 的顶层 names 检查集合只包含 `"Makefile"` 精确匹配、
`CMakeLists.txt`、`configure.ac/Makefile.am`、`meson.build`，**未识别
`GNUmakefile`**（GNU make 的替代命名，header-only / 自定义构建项目常用）。
因此 random123 被判 m_lang=None、build_system="none"。

随后 `_source_stats` 得到 cpp 主体 69.4% < 70% 阈值，且无 manifest，
落入 generic 分支（lang_detect.py 214-216 行）：
「无 manifest 且主体占比 <70% → mixed」→ 自动写 env_unsupported 终态。

## 为什么这是误判

SKILL R47 与 lang_detect.py 头部边界规则明确：

- 「C/C++ 混编 → 按主体判 c 或 cpp（不算 mixed，E13）」
- 「c↔cpp 视为兼容族不迁移（conan 流程通吃）」；`_COMPAT_FAMILY = {"c", "cpp"}`
- D.4：bash 等辅助脚本不参与主体占比

random123 的 36 个实源文件全部是 C/C++ 族（cpp 25 + c 11），主体为 cpp，
按边界规则应判 cpp 而非 mixed；c↔cpp 兼容族内不触发语言迁移。

## 解决方案（执行端处理口径）

不修改框架的前提下：

1. 复核源码语言构成：确认全部实源属于 C/C++ 族、bash 仅为辅助脚本；
2. 按 R47/E13 边界规则以主体语言 cpp 继续主流程（不触发迁移、不停止）；
3. 记录分析日志（命令、检测结果、复核依据、决定）作为审计证据。

### 同任务关联：Conan 2 header-only 配方要点（conan-verify G2 修复）

header-only 库（无 CMake）的 Conan 2 配方：

```python
package_type = "header-library"

# Conan 2 没有 self.copy —— 需显式导入并传 self 作为第一个参数
from conan.tools.files import copy

def package(self):
    copy(self, "*",
         os.path.join(self.source_folder, "include"),
         os.path.join(self.package_folder, "include"), keep_path=True)
```

- 直接写 `self.copy(...)` → `AttributeError: object has no attribute 'copy'`
- `copy(self, "*.h", src="include", dst="include")`（相对串相同）→
  `ConanException: copy() 'src' and 'dst' arguments must have different values`
- fnmatch 按文件相对路径匹配，需用 `"*"` 整目录拷贝并 `keep_path=True`

## 验证

- lang-preflight 误判分析：`.ohc-logs/lang_preflight_analysis.log`
  （SHA-256 12c55dc7839d1725d99b6daccce396a32890607880eef50ea52ad51820bf90c6）
- 以 cpp 口径完成全量适配：13 项独立上游用例构建运行
  （kat_c / kat_cpp / ut_ars / ut_carray / ut_Engine / ut_features /
  ut_ReinterpretCtr / ut_ua / ut_uniform / ut_gsl 通过，ut_M128 / ut_aes 为
  上游文档化 no-op stub，ut_uniform_IEEEkat 为上游记载的 ARM/FMA 已知失败）
- conan-verify G0-G4/L2/L4/L5 全 PASS；test_package 与独立消费者程序通过

## 适用边界 / 反例

- 适用：仅有 GNUmakefile 的 C/C++ 库；cpp 主体占比 [50%, 70%) 的无 manifest C/C++ 混编库
- 反例：主体语言确为非 C/C++（如 python/rust）时，仍按 R47 交平台语言迁移，
  不得以本条目绕过真实语言不匹配

## 关系

- similar_to: DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect
  （同为 lang-preflight 误判，但根因不同：emio=辅助 Cargo.toml 干扰 manifest 扫描
  优先级；本条目=GNUmakefile 未识别 + 无 manifest 主体占比边界）
- prerequisite_of: 无
- caused_by: lang_detect manifest 识别集合缺 GNUmakefile（框架侧建议补充）
