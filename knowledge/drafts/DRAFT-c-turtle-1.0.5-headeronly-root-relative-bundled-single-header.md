# DRAFT-c-turtle-1.0.5-headeronly-root-relative-bundled-single-header

**状态**: Draft only（路径 B 知识草稿，未 promote 至 knowledge/graph）
**产生库**: c-turtle 1.0.5（header-only 图形库，Python Turtle 的 C++ 移植）
**台账**: archives/c/c-turtle/1.0.5/reports/knowledge-candidate-ledger.md

## 问题

c-turtle 的公开头 `CTurtle.hpp` 在**仓库根目录**相对 `#include "CImg.h"`
（CImg 3.1MB 单头被上游 vendored 在仓库根）。Conan header-only 配方若
只打包主库头，消费者（find_package + `#include "CTurtle.hpp"`）编译报：

```
fatal error: 'CImg.h' file not found
```

同一族问题在 gli（external/glm 层级）已有草稿
DRAFT-gli-0.8.2.0-headeronly-ship-bundled-dep-headers，但该草稿只覆盖
`external/<dep>/<dep>` 子目录布局；**仓库根相对 include 的单头布局**未覆盖。

## 根因

header-only 库的依赖是头文件级依赖：公开头内嵌第三方 include。当
vendored 依赖头与主库头**同处仓库根**（相对 include，非 `external/`
注入路径）时，配方 package() 若按 `copy("*.hpp", src=source_folder)` 
只复制主库头，或按子目录模式复制，依赖头都会丢失——必须把两者复制到
`include/` **同一目录**，相对 include 才能命中。

## 方案

conanfile.py `package()` 中把主库头与根级内置依赖头一并装入 `include/`
同目录，保持相对 include 布局：

```python
copy(self, "CTurtle.hpp", src=self.source_folder,
     dst=os.path.join(self.package_folder, "include"))
copy(self, "CImg.h", src=self.source_folder,
     dst=os.path.join(self.package_folder, "include"))
copy(self, "LICENSE*", src=self.source_folder,
     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
```

`package_info()` 只需 `includedirs=["include"]`（含依赖头自然覆盖）。

## 验证

- `conan create archives/c/c-turtle/1.0.5 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → G2 PASS
- 消费者 test_package（find_package(c-turtle) + CTurtle.hpp 真实 API：TurtleScreen/Turtle/forward/right/xcor/ycor/write/bye）编译链接运行通过，GIF 输出非空（12,605 B）
- 鸿蒙专项测试 test_fractal（Koch 分形递归渲染）通过，GIF 输出 907,654 B

## 无 tag 上游的附带边界（融合，不单独立项）

上游无 git tag/release：README 标 1.0.5，头文件宏 `CTURTLE_VERSION`
仍为 v1.0.4，master HEAD commit 消息为 "v1.0.5 Patch"。conandata 以
官方 GitHub **commit 归档 URL** + SHA-256 固定版本：

```yaml
sources:
  url: "https://github.com/walkerje/C-Turtle/archive/1571a06638f6fe4fed10015545c0de2f58c76cda.tar.gz"
  sha256: "619fe41db0fb20ceb10745083f7527ab302efb055ee9cc2f8df3caf65bfe88f8"
```

与 E470（tag-as-provenance-source：tag 存在但版本元数据滞后）不同：
此处 tag 完全不存在，只能以官方 commit 归档 URL 固定。

## 适用边界

- 适用：公开头在仓库根相对 include 内置单头依赖的 header-only 库
  （CImg 系、stb 系同族）在 Conan 2 + OHOS；无 tag 上游以 commit URL 固定。
- 反例：依赖在制品仓已有独立配方且版本匹配 → `requires` 更优（沿
  DRAFT-gli 边界）；非根级布局（external/ 子目录）→ 参照 DRAFT-gli 的
  include/<dep> 方案。

## 查重

- DRAFT-gli-0.8.2.0-headeronly-ship-bundled-dep-headers：部分覆盖
  （external/ 层级布局），未覆盖仓库根相对 include 单头布局 → similar_to。
- E322（header-only INTERFACE 配方）：部分覆盖（配方形态），未覆盖内置依赖头分发。
- E277（vendored 依赖 build() 内编译到 staging）：不同（编译子项目 vs 分发包头）。
- E458（restinio bundled 依赖缺失）：不同（tarball 缺依赖需外部下载）。
- E470（tag-as-provenance-source）：不同（tag 存在 vs 无 tag）。
- 结论：未命中完整条目 → new_draft（路径 B）。

## 关键词

header-only, root-level, relative include, bundled, CImg, single-header,
package, consumer, conan, commit-archive-url, no-tag, sha256