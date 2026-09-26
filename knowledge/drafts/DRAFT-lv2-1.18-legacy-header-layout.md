# DRAFT-lv2-1.18-legacy-header-layout — LV2 1.18 头布局迁移

**severity**: 2（🟡medium） ｜ **phase**: compilation ｜ **类别**: build-system, headers, portability, compat

## 错误特征

```
src/casynth/casynth.h:4:9: fatal error: 'lv2.h' file not found
src/envfollower/envfollower.c:10:10: fatal error: 'lv2/lv2plug.in/ns/ext/urid/urid.h' file not found
```

## 触发条件

- 构建系统: cmake / autotools / 纯 Makefile 皆可复现
- 阶段: 编译（`#include` 解析）
- 依赖: 现代 LV2（本仓 `lv2/1.18.11-git`，即 LV2 1.18 布局）

## 根因分析

LV2 1.18 的安装布局只有 `include/lv2/<spec>/<header>.h`（`core/ atom/ urid/ midi/ time/ ui/ options/ buf-size/ …`），
而 2012 年前后写成的 LV2 插件源码用的是旧写法：

- `#include <lv2.h>` —— 扁平 lv2core 头
- `#include "lv2/lv2plug.in/ns/ext/<spec>/<header>.h"` —— 旧 URI 风格路径
- `#include "lv2/lv2plug.in/ns/extensions/ui/ui.h"`

**这不是 conan 包漏装文件**：LV2 上游 v1.14.0 / v1.16.0 / v1.18.0 的源码树里都**不存在** `include/lv2.h`
（`https://gitlab.com/lv2/lv2/-/raw/<tag>/include/lv2.h` 全部 404），上游在 1.x 时代就把头文件收敛到
`lv2/<spec>/` 目录树。依赖头是齐的，只是**路径不同** —— 对同一时期的 LV2 插件源码普遍成立。

## 影响范围

| 受测包 | 受影响文件数 | 说明 |
|--------|-------------|------|
| infamousPlugins 0.3.2 | 23 | 15 处 `<lv2.h>`；10 个文件用 `lv2/lv2plug.in/ns/...`（含 4 个 DSP 源文件） |
| archives/a/artyfx 1.3.1 | 少量 | 同仓旧做法（依赖包内符号链接） |
| archives/b/boops 1.0.0 | 少量 | 同仓旧做法（依赖包内符号链接） |

## 解决方案

### 推荐方案：构建期兼容头目录（private compat include root），上游源码零改动

```python
def generate(self):
    compat = os.path.join(self.build_folder, "lv2-legacy-include")
    for legacy, modern in self._LV2_LEGACY_HEADERS.items():   # 见 .kv rec_command
        save(self, os.path.join(compat, legacy), f"#include <{modern}>\n")
    tc.extra_cflags.append("-I" + compat)
    tc.extra_cxxflags.append("-I" + compat)
```

参考实现：`archives/i/infamousplugins/0.3.2/conanfile.py`

备选：源码补丁批量替换为现代路径（本例会产出 20+ 个补丁文件，噪音大）。

### 验证诊断正确

```bash
grep -rhoE '#include *[<"][^>"]*lv2[^>"]*[>"]' src/ | sort -u      # 列出全部 LV2 头写法
curl -s -o /dev/null -w '%{http_code}\n' \
  https://gitlab.com/lv2/lv2/-/raw/v1.18.0/include/lv2.h          # 404 → 上游无扁平头
nm -D <plug>.so | grep lv2_descriptor                             # 产物符号存在
```

### 禁止做法

- ❌ **在依赖包 `package_folder` 里创建符号链接或写文件**（artyfx/boops 旧做法）。
  理由：修改共享依赖包 → 本地缓存被污染、并发构建互相影响、CI 干净环境与本地结果不一致；
  HMDFS 下软链接覆盖还有额外限制。
