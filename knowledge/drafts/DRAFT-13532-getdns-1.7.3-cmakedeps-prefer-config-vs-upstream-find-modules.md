# DRAFT-13532-getdns-1.7.3: CMakeDeps PREFER_CONFIG vs 上游 Find 模块 target 失配

> 草稿（B 类知识库贡献候选）。关联任务：#13532（getdns 1.7.3）。
> 关联正式条目：E473（同根因不同解法分支）。

## 错误现场

getdns 1.7.3（上游自带 cmake/modules/FindCheck.cmake 等 Find 模块，
target 名 `Check::Check`）在 Conan 2.29.1 CMakeDeps 下配置：

```
CMake Error at CMakeLists.txt:996 (target_link_libraries):
  Target "check_getdns" links to:
    Check::Check
  but the target was not found.
```

同款报错变体：`Libev::Libev`、`Libevent2::Libevent_core`、`Libuv::Libuv`。

## 根因

1. Conan 2 CMakeToolchain 的 conan_toolchain.cmake 在 find_paths block
   **无条件** `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`（有 CMakeDeps
   生成文件时的固定行为）
2. 该 set 晚于 `-DCMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF` 的 cache 注入
   （cache_variables 方式无效，最终 cache 显示 UNINITIALIZED=OFF 但实际
   生效值为 toolchain 的 ON）
3. conf 键 `tools.cmake.cmaketoolchain:find_package_prefer_config=False`
   只认消费者 profile 的 [conf]；recipe 内 `self.conf_info.define()`
   不会回灌到自身构建
4. PREFER_CONFIG=ON → `find_package(Check)` 命中 CMakeDeps 的
   check-config.cmake（target `Check::check`，小写）→ 上游大写
   `Check::Check` 悬空

## 解法：CMAKE_PROJECT_INCLUDE 注入

CMAKE_PROJECT_INCLUDE 在 project() 之后、find_package 之前执行——
恰好晚于 toolchain 的强制 ON、早于依赖查找：

```python
def generate(self):
    CMakeDeps(self).generate()
    tc = CMakeToolchain(self)
    inject = os.path.join(self.generators_folder,
                          "conan-disable-prefer-config.cmake")
    save(self, inject, "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n")
    tc.variables["CMAKE_PROJECT_INCLUDE"] = inject
    tc.variables["OPENSSL_ROOT_DIR"] = \
        self.dependencies["openssl"].package_folder
    tc.generate()
```

翻回 OFF 后 find_package 走 MODULE 模式命中上游 Find 模块，模块的
`<NAME>_DIR` 提示变量注入 Conan 依赖路径：

```python
def _find_hint_vars(self):
    deps = {"CHECK_DIR": "check", "LIBIDN2_DIR": "libidn2",
            "LIBEV_DIR": "libev", "LIBEVENT2_DIR": "libevent",
            "LIBUV_DIR": "libuv"}
    return {var: self.dependencies[d].package_folder
            for var, d in deps.items() if d in self.dependencies}

def build(self):
    cmake = CMake(self)
    cmake.configure(variables=self._find_hint_vars())
    cmake.build()
```

## 与 E473 的关系

E473（libwebp/SDL2_image）：PREFER_CONFIG=ON 引发个别 target 缺失 →
cmake_build_modules 注入缺失 target（轻量补丁式）。
本条：上游 Find 模块完整、target 名成套不同 → 整体切换查找模式
（CMAKE_PROJECT_INCLUDE 翻 OFF）。两者同根因（PREFER_CONFIG 强制 ON）
不同分支，按场景选用：缺个别 target 用 E473，整套失配用本条。

## 附带发现（本任务 patch 0001）

上游 getdns 1.7.3 FindLibuv.cmake 有独立 typo：
`find_library(LIBUV_LIBRARIES ...)` 后 guard 检查未定义的
`LIBUV_LIBRARY` → `Libuv::Libuv` target 永远不创建 → getdns_ext_uv
链接失败。一行修复（LIBUV_LIBRARY → LIBUV_LIBRARIES）。

## 验证

- getdns 1.7.3 conan create（ohos-aarch64，clang 15）全绿
- 4 个 Check 测试变体 + test_package 冒烟全过
- CI 构建号：PR 合并后回填
