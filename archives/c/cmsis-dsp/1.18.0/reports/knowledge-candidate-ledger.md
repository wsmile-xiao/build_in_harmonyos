# cmsis-dsp 1.18.0 — 知识候选台账 + 七轴查重 + 路径判断

task_id: cmsis-dsp-1.18.0-r01-pc7-5-20260920T123932Z · executor: pc7-5
任务类型: 知识库扩展（路径 B）· 查重依据: 当前 worktree ./SKILL.md、knowledge/graph/index.tsv、
knowledge/doc/、knowledge/graph/、knowledge/drafts/（四范围），ohc-run.py graph/engine 辅助

## 候选 C1: lang-preflight 将纯 C 库 cmsis-dsp 误判为 python（辅助 pyproject.toml 干扰）

- **真实错误**: `ohc-run.py lang-preflight cmsis-dsp 1.18.0 --src <src>` 判定
  `detected_language=python`（build_system=setuptools, manifest="pyproject.toml 存在（python 打包 manifest）"），
  自动写终态 `env_unsupported`（draft:false），exit 2。
- **根因**: lang_detect.py `_manifest_scan` 对 pyproject.toml/setup.py 使用全树文件名集合
  （`names = {p.name for p in files}`，rglob 全部文件，未限定源码根顶层），源码树 PythonWrapper/、
  cmsisdsp/、Testing/、Examples/ 等子目录的 4 个 pyproject.toml（均辅助工具/测试/绑定）被当作主库
  manifest；叠加"统计无 ≥70% 主体（c 69%）按 manifest 判 python"——`_source_stats` 未把 c+cpp 合并
  （C 69% + C++ 23% = 92.6% ≥ 70%），导致判 python 而非 c/cpp 兼容族。
- **修复（本轮已验证）**: 按 R47 D.4 边界规则以主库主体判定——主库主体为 C/C++（Source/ 660 个 .c、
  Include/ 49 个 .h，占 92.6%），辅助 Python 工具不参与主体语言判定 → detected=c/cpp（c↔cpp 兼容族不迁移），
  记录证据后继续适配主流程；conan-verify G0-G4/L2/L4/L5 全 PASS + 消费者/专项测试实证为可正常适配的 C 库。
- **验证**: lang-preflight 原始输出（detected=python）存档；后续门禁全绿（见 test-report.md §2）。
- **适用范围**: 源码树含 PythonWrapper/cmsisdsp/Testing 等辅助 pyproject.toml 的 C/C++ 库
  （DSP 库、带 Python 绑定的 C 库、测试工具用 Python 的库）；任何依赖 lang-preflight 终态判定的任务。

### 四范围查重（C1）
| 范围 | 结果 |
|------|------|
| 正式知识 doc/E*.md | E220（perl Configure hardlink）、E154/E358（Rust 工具链）、E379（上游测试闭合输入）——均与本候选无实质重叠 |
| 图谱 graph/E*.kv | 无 pyproject.toml→python 误判变体条目 |
| 草稿 drafts/ | DRAFT-exr_image-...-lang-preflight-aux-manifest（Cargo.toml→mixed(cargo) 变体）、DRAFT-dshlibs-...-pure-script-package-misdetect（纯脚本包→c 变体）、DRAFT-E586-libyal-...（根目录绑定 manifest→mixed，status=pending-editor-review）、DRAFT-cl-unicode-lisp-...——同家族不同变体，均未覆盖 pyproject.toml→python + c/cpp 未合并计数这一变体 |
| 知识候选台账（既往任务） | 无 cmsis/pyproject 变体记录 |

### 七轴查重（C1）
| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | ❌ 否 | 无任何条目描述 pyproject.toml→python 误判（既有为 Cargo.toml→mixed、bash→c） |
| causal_duplicate | 部分 | 与 DRAFT-exr_image/DRAFT-E586 同根因族（_manifest_scan 全树扫描未顶层锚定），但本候选新增 c/cpp 未合并计数（69%<70% 而非 92.6%）+ python 判定路径 |
| trigger_overlap | 高 | 同为 lang-preflight/lang_detect.py，同 trigger（子目录辅助 manifest 被当主库 manifest） |
| solution_overlap | 高 | 同为 R47 D.4 边界规则主库主体判定 + 框架侧顶层锚定回退方案 |
| combination_novelty | 中 | "C/C++ 合计占比应合并计数"是本轮新增差异（既有条目均为单一语言统计），可跨库复用 |
| boundary_novelty | 中 | pyproject.toml/setuptools→python 判定边界为既有条目未显式覆盖点 |
| test_migration_novelty | 无 | 不涉及测试迁移 |

关系: similar_to=[DRAFT-exr_image-...-lang-preflight-aux-manifest, DRAFT-E586-libyal-...],
caused_by=[], prerequisite_of=[], conflicts_with=[]

## 候选 C2: CMSIS 家族库免 CMSIS-Core 的 standalone 构建模式（HOST=ON → __GNUC_PYTHON__）

- **真实错误**: CMake 构建 cmsis-dsp 1.18.0 首错 `fatal error: 'cmsis_compiler.h' file not found`
  （arm_math_types.h:126）；消费者/ test_package 直接编译同类报错。
- **根因**: CMSIS-DSP standalone（无 CMSIS-Core 提供 cmsis_compiler.h）时，arm_math_types.h 的
  `#include "cmsis_compiler.h"` 无头文件可解析；上游唯一免 CMSIS-Core 路径是定义 `__GNUC_PYTHON__`
  （源码注释明示 "the only way to build on a target not supported by CMSIS Core"），
  configDsp.cmake 以 `HOST=ON` 选项统一注入；消费者（含 test_package）编译必须同样定义该宏，
  否则安装头仍引用 cmsis_compiler.h。
- **修复（本轮已验证）**: 配方 conanfile.py `generate()` 设 `HOST=ON`（→ __GNUC_PYTHON__）；
  `package_info()` 用 `self.cpp_info.defines = ["__GNUC_PYTHON__"]` 向消费者（含 test_package）传播，
  与上游安装包 INTERFACE_COMPILE_DEFINITIONS 行为一致。修复后 conan-verify G2 PASS、test_package、
  消费者、鸿蒙专项测试全部通过。
- **验证**: 修复前 G2 FAIL（cmsis_compiler.h 缺失日志存档）；修复后 conan create + 消费者 + 专项测试全绿。
- **适用范围**: CMSIS 家族库（CMSIS-DSP/CMSIS-NN/CMSIS-Core 下游）在无 CMSIS-Core 平台（OHOS/x86 host）
  的 standalone 构建；任何同时提供库本体与 Python 绑定/工具子树的 ARM CMSIS 系仓库。

### 四范围查重（C2）
| 范围 | 结果 |
|------|------|
| 正式知识 | 无 CMSIS/__GNUC_PYTHON__/cmsis_compiler 条目 |
| 图谱 | index.tsv 检索 cmsis/GNUC_PYTHON/cmsis_compiler 零命中 |
| 草稿 | 零命中 |
| 既有归档 | archives/ 无其他 CMSIS 库适配记录 |

### 七轴查重（C2）
| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | ❌ 否 | 知识库完全无 CMSIS 家族条目 |
| causal_duplicate | ❌ 否 | 无同根因条目 |
| trigger_overlap | 无 | 无重叠条目 |
| solution_overlap | 无 | 无重叠条目 |
| combination_novelty | 高 | CMSIS 家族 standalone 构建 + 消费者宏传播为全新组合知识 |
| boundary_novelty | 高 | "库本体为 C、Python 绑定为辅助、__GNUC_PYTHON__ 免 CMSIS-Core"边界全新 |
| test_migration_novelty | 无 | 不涉及测试迁移 |

关系: similar_to=[], caused_by=[], prerequisite_of=[], conflicts_with=[]

## 路径判断（最终）

- C1: 查重为**部分覆盖**（同根因族、新增 c/cpp 合并计数 + pyproject→python 变体，已由本轮真实日志验证，
  可跨库复用）→ 满足"部分重复且新增差异已由本轮真实日志验证并可跨库复用"→ **new_draft（路径 B）**
- C2: 查重为**未命中**（完全无覆盖），已验证、可跨库复用 → 必须走路径 B → **new_draft（路径 B）**
- 决定: `new_draft` × 2（C1、C2），建立同 stem 的 .md/.kv 草稿对，随本库归档同 PR 交付
- 非噪声候选共 2 项；噪声排除: NEON 测试模式数据缺口（上游数据问题，非本库适配知识，见台账 §4 不上知识）、
  E225 知识引擎误命中（G2 真实根因是 __GNUC_PYTHON__ 传播缺失，已由 C2 覆盖）

---

# R02 返工新素材（2026-09-20）追加

R02 将 NEON 变体 1332 项全部实例化运行后，产生两项新的真实技术素材，
需在 R02 任务内完成查重并维持草稿配对（任务第 6 条：素材变化时修订 DRAFT 内容，维持同 stem .md/.kv 配对）。

## 候选 C3: NE10 动态 Q31 CFFT（arm_cfft_init_dynamic_q31）因子 5（radix-5）路径在 clang 15 aarch64 上输出错误/段错误

- **真实错误**: NEON 配置 180 个用例失败（TransformNeonCQ31 套件全部含因子 5 尺寸：
  20/40/60/80/100/120/160/180/200/240/300/320/360/400/480，90 CFFT + 90 CIFFT，SNR 均 <100，3.4~41.7 dB）；
  独立 20 点动态 Q31 CFFT 直接段错误（Signal 11 / core dumped）。
- **根因**: `arm_cfft_init_dynamic_q31`（Ne10 路径，仅 NEON 可用）对含因子 5 长度的蝶形分解/旋转因子
  处理在本工具链下不可靠；源码树无 radix5 实现文件，库中无 radix5 符号（nm 0 命中）；
  通过尺寸全部为 2/3 幂（24/32/36/48/64/72/96/108/128/144），失败尺寸全部含因子 5——严格二分，
  指向 radix-5 蝶形路径缺陷。
- **验证**: run-neon-r02.log（786 执行/606 通过/180 失败，SHA-256 23705a60…）；
  R01 无宏构建 run1 同 180 失败同 SNR 值（排除注入宏干扰）；参考模式文件均存在且有效。
- **适用范围**: 任何在 aarch64 OHOS/clang 15 上运行 CMSIS-DSP NEON 动态 Q31 CFFT 因子 5 尺寸的任务。

### 四范围查重（C3）
- index.tsv/graph/doc/drafts 检索 NE10、radix5、cfft、dynamic-fft、NEON q31: **零命中**
- E506（libpng arm_neon 源选择）、E145（opus meson 变量）均不相关

### 七轴查重（C3）
| 轴 | 判定 |
|----|------|
| exact_duplicate | ❌ 否（无任何 NE10/CFFT/radix5 条目） |
| causal_duplicate | ❌ 否 |
| trigger_overlap | 无 |
| solution_overlap | 无 |
| combination_novelty | 高（NE10 动态 Q31 CFFT 因子5 缺陷为全新素材） |
| boundary_novelty | 高（"含因子5 尺寸 vs 2/3 幂尺寸"二分边界全新） |
| test_migration_novelty | 无 |

关系: similar_to=[], caused_by=[], prerequisite_of=[], conflicts_with=[]
决定: **new_draft（路径 B）** → DRAFT-cmsis-dsp-1.18.0-ne10-dynamic-q31-cfft-radix5.{kv,md}

## 候选 C4: Testing 测试框架 F16 NEON 套件编译需命令行注入守卫宏（ARM_MATH_NEON_FLOAT16 + ARM_FLOAT16_SUPPORTED）

- **真实错误**: test 目标链接失败：`undefined symbol: vtable for TransformNeonCF16 / TransformNeonCF16::test_cfft_f16()`
  （obj 仅 832 字节，类方法未被实例化）。
- **根因**: `TransformNeonCF16.cpp` 顶部守卫 `#if defined(ARM_MATH_NEON_FLOAT16) && defined(ARM_FLOAT16_SUPPORTED)`
  在 include 前求值，两宏均需命令行定义（前者不会自动定义；后者与头文件重复定义时需 `-Wno-macro-redefined`）；
  CMakeLists 未传递该守卫所需宏 → 类方法整体被条件编译排除 → 链接缺符号。
- **验证**: 注入 `-DARM_MATH_NEON_FLOAT16 -DARM_FLOAT16_SUPPORTED -Wno-macro-redefined` 后 test 链接成功（100% Built），
  NEON 配置 786 项实际运行。
- **适用范围**: 运行 CMSIS-DSP Testing 框架 F16+NEON 套件（TransformNeonCF16/BinaryTestsNeonF16）的任何任务。

### 四范围查重（C4）
- graph/doc/drafts/index 检索 ARM_MATH_NEON_FLOAT16 / ARM_FLOAT16_SUPPORTED / 守卫宏: **零命中**

### 七轴查重（C4）
| 轴 | 判定 |
|----|------|
| exact_duplicate | ❌ 否 |
| causal_duplicate | ❌ 否 |
| trigger_overlap | 无 |
| solution_overlap | 无 |
| combination_novelty | 中（CMake 测试目标守卫宏注入） |
| boundary_novelty | 高（F16+NEON 组合守卫在 include 前求值） |
| test_migration_novelty | 无 |

关系: similar_to=[], caused_by=[], prerequisite_of=[], conflicts_with=[]
决定: **new_draft（路径 B）** → DRAFT-cmsis-dsp-1.18.0-testing-f16-neon-guard-macros.{kv,md}

## R02 草稿配对总清单
| 草稿 stem | 来源 | 决定 |
|-----------|------|------|
| DRAFT-cmsis-dsp-1.18.0-lang-preflight-pyproject-python-misdetect | R01 C1（素材不变） | new_draft |
| DRAFT-cmsis-dsp-1.18.0-standalone-no-cmsis-core-gnuc-python | R01 C2（素材不变） | new_draft |
| DRAFT-cmsis-dsp-1.18.0-ne10-dynamic-q31-cfft-radix5 | R02 C3（新） | new_draft |
| DRAFT-cmsis-dsp-1.18.0-testing-f16-neon-guard-macros | R02 C4（新） | new_draft |

R02 无素材变化影响 C1/C2 草稿结论；C3/C4 为新增草稿对。
