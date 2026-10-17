# draft-delaunay-triangulation-2.1-install-headers-missing-referenced-header

## 症状

delaunay-triangulation 2.1 消费者用例（`reports/consumer-case.cpp`，仅用库已安装公开头
`#include <dt/delaunay.h>` 编译）报：

```
In file included from .../include/dt/delaunay.h:4:
.../include/dt/vector2.h:4:10: fatal error: 'numeric.h' file not found
#include "numeric.h"
         ^~~~~~~~~~~
1 error generated.
```

构建周期与打包周期行为分离：`meson setup + ninja`（源码树内）成功——头文件在源码树
存在；`conan create` 的 install 阶段也成功——列表里没有的文件自然"不报错"；只有
消费者从 **package 后的 include/** 目录读公开头时才暴露缺头。

## 根因

上游 `meson.build` 的 `install_headers()` 列表：

```meson
install_headers(
	'include/vector2.h',
	'include/edge.h',
	'include/triangle.h',
	'include/delaunay.h',
	subdir: 'dt',
)
```

漏掉 `include/numeric.h`。而 `vector2.h` 与 `triangle.h` 都 `#include "numeric.h"`
（`almost_equal` / `half` 模板）。安装清单不完整 → 已发布头自引用断裂 → 任何下游
消费者编译失败。构建系统安装头列表"编译时没问题、安装后才暴露"是此类缺陷的共同
特征——构建目标只看源码树，安装清单是独立声明。

## 修复

补丁 `patches/0001-meson.build.patch`：`install_headers(...)` 列表补加
`'include/numeric.h'`。

应用后 conan create 安装日志出现：

```
Installing .../include/numeric.h to .../p/include/dt
```

## 验证

1. `conan create`（G2）PASS，`test_package` ctest PASS（test.cpp 用
   `#include "dt/delaunay.h"` 并三角剖分面积断言）。
2. 消费者用例仅用已安装公开头编译链接运行：64/1000/10000 点
   （欧拉公式 V−E+T==1 校验）全 rc=0。
3. `reports/conan-verify-report.md` G1-G4/L2/L4/L5 全过，`.ci-result.json` exit_code=0。

## 适用范围与边界

- **适用**：Meson `install_headers()` / CMake `install(FILES)` / make install 规则
  遗漏被公开头引用的头文件；尤其 header 依赖链（A include B）且 A/B 同目录安装
  的场景。检测手段（跨库可复用）：package 后对每个已安装头做自包含编译，任意
  一个头 `#include` 的其他头必须同时存在于安装目录。
- **边界/反例**：如果缺头是构建期生成产物（`configure_file`/config header），那是
  E309 的领域（生成头拷贝），不是本条目；如果头文件本身不存在于源码树（上游缺失），
  属于补头/改 include 的另一方向，勿用本方案掩盖。

## 关系

- `similar_to`：E309（生成头未随包拷贝——同涉"package 后头文件缺失"，根因不同：
  列表遗漏 vs 生成物拷贝）。
- 同族：E217（CMake includedirs/安装路径）观察面部分重叠。

## 查重

按 `install_headers` / `numeric.h` / `public header missing` / `header self-reference`
检索 `knowledge/graph/` 与 `knowledge/drafts/`：

- E309：根因=直拷源码漏掉**构建期生成**公共头（configure_file/config header）；
  本条=**静态源码头安装清单遗漏**。触发场景相邻、机制不同 → 非重复，建立新草稿。
- E255：资源/数据包 cpp_info 清空，不相关。
- E370：meson test fixture 台账，不相关。
- `knowledge/drafts/` 无同主题条目。

⚠️ **签名家族提示**：`fatal error: '<X>.h' file not found` 是 E217/E169 等大类的
通用字面量，本条辨别指纹必须是「安装清单遗漏 + install_headers/install(FILES) +
自包含编译暴露」语境，勿劫持泛化头文件缺失节点。