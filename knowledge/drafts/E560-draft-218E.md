# E560-draft-218E — R47 lang-preflight 盲区：Debian 源码包 / blend 元包被误判 detected=c

## 错误面（现象）

- **触发**：lang-preflight（`scripts/ohc/lang_detect.py`）对纯打包元数据型源码包做语言预检
- **阶段**：configuration（checkout 后、进入适配主流程前的 R47 预检）
- **签名**：`detected_language: "c"` + `source_stats: 无源文件可统计` + `include /usr/share/blends-dev`

实测（debian-pan 0.4，35 文件）：

```json
{ "expected": "cpp", "detected_language": "c",
  "language_evidence": { "build_system": "make",
    "manifest": "顶层 Makefile（无更强 manifest）",
    "source_stats": "无源文件可统计" } }
```

`find . -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' \) | wc -l` → `0`

## 识别

- severity: 2（🟡medium —— 检测器盲区，非编译失败，但会误导"是否可适配"决策）
- category: detection, build-system, make, packaging, ohos

## 诊断

`lang_detect.py` 三级判定（manifest > 构建系统 > 源码统计 ≥70%）中，
Debian 源码包 / blend 元包的顶层 `Makefile` 只有一行：

```make
#!/usr/bin/make -f
include /usr/share/blends-dev/Makefile
```

被识别为 make 构建系统 → 推入 c/cpp 兼容族；而源码统计为零
（无任何 .c/.cpp/.h 可统计文件）→ 命中"构建系统优先"路径，
**输出 `detected_language=c` 且 exit 0 通过预检**。

但这类包的二进制产物是 18 个 `Architecture: all` 的 pan-* 元包与
tasksel 任务（纯描述文本），**零 C/C++ 源码、零可执行程序、零测试框架**。

## 处置口径（本条的核心修正）

检测器盲区只影响**语言标签**，不决定**可交付性**。两个方向的误判都要避免：

| 误判方向 | 错误动作 | 后果 |
|---|---|---|
| ① 把 detected=c 当真 | 硬编 C/C++ 配方（空壳 stub / 假 bin / 假 .so） | R34/R8 违规，W3/CI 必然失败，审计按欺骗一票否决 |
| ② 把"零 C/C++ 源码"当不可适配 | 一律 `env_unsupported` 终止 | 路线误判：blend 元包有可交付形态，任务被无谓终止 |

**正确路径 = metadata/registry Conan 包**（本条早期结论只写了方向 ②，已由
实测推翻）：

```python
package_type = "unknown"                     # Conan 2.29 无 meta-package 枚举
settings = "os", "compiler", "build_type", "arch"   # CI L0 门禁；数据包无真实语义
# requirements() 为空：Debian Depends/Recommends/Suggests 是 OS 包选择，禁止机械复制
# package(): 装真实上游产物（tasks/* + tasksel desc + 官方依赖快照
#            + build() 纯解析派生的 registry.json + licenses/copyright）
# package_info(): cpp_info.includedirs/libdirs/bindirs = []，resdirs = ["share"]
```

验证命令（与 CI 的 L1 门禁同一命令）：

```bash
conan create archives/d/debian-pan/0.4 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# 实测 RC=0；test_package checks: 48, failures: 0 ==> ALL PASSED (100.0%)
```

## 判定辅助证据（分流用，非猜测）

| 证据 | 命令 | debian-pan 0.4 实测 |
|---|---|---|
| 二进制包数（全 arch:all） | `grep -c '^Package:' debian/control` | 18（`grep -c '^Architecture: all'` → 18） |
| 任务文件数 | `ls tasks/ \| wc -l` | 18 |
| tasksel desc 段落 | `grep -c '^Task:' debian-pan-tasks.desc` | 17 |
| tasksel Key 数 | `grep -c '^Key:' debian-pan-tasks.desc` | 16 |
| 可编译单元 | `find . -name '*.c' -o -name '*.cpp' -o -name '*.h'` | 0 |

## 禁止

- ❌ 硬编 C/C++ 空壳配方（R34/R8）——零 API/二进制可调用，硬做=造假
- ❌ 把 446 条 OS 包选择（`python3-*`/`lib*-dev` 等 Debian 专有命名）写成
  Conan `requires` —— 会造出虚假且不可满足的依赖图（PF4 依赖闸亦会拦）
- ❌ 不加分析地把"零 C/C++ 源码"等同于"不可适配"而终止任务

## 关联

- 同族大型实例的分流口径：E564（debian-science 1.15，其 45 个 science-* 二进制包）
- 无测试上游的本地验证补充模板：E563（本包 test_package 48 项断言即其落地）
