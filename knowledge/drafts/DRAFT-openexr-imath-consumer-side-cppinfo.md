# DRAFT：CMakeDeps 消费侧补丁依赖包组件 includedirs 的三个时序/路径坑（imath→openexr 实战）

> 草稿状态：待主编审核（DRAFT-E5xx-openexr-imath-consumer-side-cppinfo）
> 来源：openexr 3.3.4 适配（j669539，2026-09-10）

## 现象

编译上游 OpenEXRCore（及其消费者）报：

```
src/lib/OpenEXRCore/openexr_config.h:12:10: fatal error: 'ImathConfig.h' file not found
```

主包编过、test_package 再爆一次；消费者（openvdb 等）也会爆。

## 根因

上游 OpenEXR 的公开头直接 `#include <ImathConfig.h>`（不是 `<Imath/ImathConfig.h>`）。
上游 Imath 的安装接口（ImathTargets.cmake `Imath::ImathConfig`）同时暴露
`include/` 与 `include/Imath` 两个 INTERFACE 目录。本仓库已发布的 imath/3.2.2
conan 配方 cpp_info 只声明 `include/`，CMakeDeps 生成的 ImathConfig.cmake 缺
`include/Imath` 子目录 → 编译期 file not found。

## 修法（下游消费侧，无需改已发布依赖）

三个坑全踩过才通：

1. **必须绝对路径**：`info.includedirs.append("include/Imath")`（相对路径）会被
   CMakeDeps 序列化丢弃，生成文件不含该目录；要 `os.path.join(d, "Imath")` 基于
   已有绝对路径构造。
2. **必须改组件级**：imath 配方声明了 `components["imath"]`，CMakeDeps 用组件级数据；
   只改包级 `cpp_info.includedirs` 生成的 `imath_Imath_Imath_INCLUDE_DIRS_RELEASE`
   纹丝不动。包级+组件级都改最稳。
3. **必须在 CMakeDeps 构造前**：`deps = CMakeDeps(self)` 实例化时读取依赖元数据，
   先构造再改无效。

```python
# 下游配方 generate()
imath_info = self.dependencies["imath"].cpp_info
for info in [imath_info] + list(imath_info.components.values()):
    dirs = list(info.includedirs)
    if not any(d.endswith("include/Imath") for d in dirs):
        for d in dirs:
            if d.endswith("include"):
                dirs.append(os.path.join(d, "Imath"))
                break
        info.includedirs = dirs
deps = CMakeDeps(self)   # 构造在修改之后
deps.generate()
```

配套要点：
- `self.requires("imath/3.2.2", transitive_headers=True)`（公开头直引依赖头）
- 组件 requires 如实声明上游 PUBLIC 依赖：`OpenEXRCore.requires` 必须含
  `"imath::imath"`，否则消费者编不过（错误同款）
- test_package 消费侧 generate() 同款补丁（test 也是消费者）

## 兜底

消费侧不可行时（依赖是间接传递），给依赖包配方补组件 includedirs
（递增依赖版本走独立 PR；参考 conan-center-index imath 配方的 imath_config 组件
`includedirs.append(os.path.join("include", "Imath"))`）。

## 适用面

所有 imath 下游（openvdb、alembic、USD、MaterialX…）以及一切"上游公开头直引依赖
子目录头"的 C++ 库组合。查重说明：E217/E498 讲 install 子目录与 headerless 场景，
E383/E330 讲 SONAME——本条聚焦"消费侧改依赖 cpp_info 的三个时序/路径坑"为空白增量。

## 验证

- openexr 3.3.4 本地 conan create 全绿（2026-09-10）
- 上游 135 项测试 100% 通过
- verify_builds：openexr PR CI（待建后补构建号）
