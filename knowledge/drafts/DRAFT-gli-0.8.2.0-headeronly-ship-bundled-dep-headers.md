# DRAFT-gli-0.8.2.0-headeronly-ship-bundled-dep-headers

**状态**: Draft only（路径 B 知识草稿，未 promote 至 knowledge/graph）
**产生库**: gli 0.8.2.0（header-only 图像库，公开头依赖内置 GLM 0.9.8）

## 问题

gli 公开头 `gli/type.hpp` 直接 `#include <glm/glm.hpp>`，上游把 GLM 0.9.8 vendored 在
`external/glm` 并通过 `include_directories(external/glm)` 注入。Conan header-only 配方
若只打包主库头目录，消费者（find_package + `#include <gli/gli.hpp>`）编译报：

```
gli/type.hpp:11:10: fatal error: 'glm/glm.hpp' file not found
```

## 根因

header-only 库的依赖是**头文件级依赖**：公开头内嵌第三方 include。vendored 依赖头在
上游源码树内、但不在主库 include/ 布局中；配方 package() 只复制主库头时依赖头丢失。

## 方案

conanfile.py `package()` 中除复制主库头外，把 `external/<dep>/<dep>` 头一并装入
`include/<dep>`，保持与上游 vendored 布局一致；`package_info()` 只需
`includedirs=["include"]`（含依赖头自然覆盖）。

```python
copy(self, "*.hpp", src=os.path.join(self.source_folder, "external", "glm", "glm"),
     dst=os.path.join(self.package_folder, "include", "glm"))
copy(self, "*.inl", src=os.path.join(self.source_folder, "external", "glm", "glm"),
     dst=os.path.join(self.package_folder, "include", "glm"))
copy(self, "*.h",   src=os.path.join(self.source_folder, "external", "glm", "glm"),
     dst=os.path.join(self.package_folder, "include", "glm"))
```

## 验证

- `conan create archives/g/gli/0.8.2.0 ... --build=missing` → G2 PASS
- 消费者 test_package（find_package(gli) + 链接 gli::gli + 真实 API 调用）编译链接运行通过（W3 L1 pass）

## 适用边界

- 适用：带 vendored/bundled 依赖头的 header-only 库（gli、glm 同族）在 Conan 2 + OHOS。
- 反例：若依赖在制品仓已有独立配方且版本匹配，`self.requires("glm/...")` 是更优替代；
  随包分发仅当 vendored 版本与制品仓版本不同步或依赖未发布时与上游行为一致。

## 查重

- E322（header-only INTERFACE 配方：关闭上游默认测试 + 消费 CONFIG target）→ 部分覆盖，未覆盖"内置依赖头随包分发"。
- E277（vendored 依赖 build() 内编译到 staging）→ 不同（编译子项目 vs 分发包头）。
- E458（restinio bundled 依赖缺失）→ 不同（tarball 缺依赖需外部下载）。
- 结论：未命中完整条目 → new_draft（路径 B）。

## 关键词

header-only, vendored, bundled, external/glm, include, package, consumer, conan, copy