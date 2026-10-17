# DRAFT：Bio++ 家族（libbpp-*）CMake 配方骨架

> 草稿（B 类知识库贡献候选）。触发：libbpp-seq-omics 2.4.1（任务 contrib-13073，
> 分支 feat/libbpp-seq-omics-2.4.1）。同族已合入/在途：libbpp-core、libbpp-seq、
> libbpp-phyl（E543）、libbpp-raa。

## 错误特征

同一套骨架、四类报错，随成员不同而出现：

```text
The imported target "bpp-core-shared" references the file ".../lib/libbpp-core.so"
  but this file does not exist.                                  # 依赖 CMake 导出与裁剪 .so 不一致
ld.lld: error: .../bpp-phyl-shared.dir/....cpp.o is incompatible with aarch64linux  # 静默宿主架构
Error loading shared library ../src/libbpp-seq.so                # OHOS 加载器斜杠相对 DT_NEEDED
CMake Error ... policy CMP0091 / cmake_minimum_required(2.8.11)  # 老 CMake 策略
```

## 触发条件

- 构建系统：CMake（Bio++ 家族统一骨架）
- 阶段：configure / compile / link / test
- 场景：Linux 交叉编译到 OHOS/aarch64（原生构建只暴露其中一部分）

## 根因分析

Bio++ 家族（`libbpp-core/seq/phyl/raa/seq-omics` 等）共用同一套 CMake 写法：

1. `cmake_minimum_required(VERSION 2.8.11)` —— 老策略，新版 CMake 需 `CMAKE_POLICY_VERSION_MINIMUM`。
2. 上游 `set(CMAKE_CXX_FLAGS "-std=c++11 …")` —— **覆盖** Conan 注入的 `--target`/`--sysroot`（详见 E543）。
3. `src/CMakeLists` 硬编码 `add_library(...-static)` + `add_library(...-shared)` 双目标，
   链接 `BPP_LIBS_STATIC` / `BPP_LIBS_SHARED` 两个变量。
4. 依赖包（如 libbpp-seq）按 `shared=False` 裁剪 `.so` 后，其 CMake 导出文件仍引用 shared 目标。
5. `find_package(bpp-seq 12.0.0 REQUIRED)` 需要上游 `lib/cmake/bpp-seq/bpp-seq-config.cmake`，
   而 CMakeDeps 生成的是 `libbpp-seq-config.cmake`，名字不匹配。

## 解决方案（五步骨架，全族复用）

```python
# generate()
tc = CMakeToolchain(self)
tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"          # ① 老 cmake_minimum_required
# ② 交叉目标（E543）：从 profile 解析 --target/--sysroot，注入编译器目标变量
cxxflags = self.conf.get("tools.build:cxxflags", default=[], check_type=list) or []
target = next((f.split("=",1)[1] for f in cxxflags if f.startswith("--target=")), None)
if target:
    tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = target
    tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = target
# ③ 依赖 CMake 导出 shim：复制依赖包到构建目录，剔除 shared imported target
#    （_prepare_cmake_shim / _strip_shared_target / _strip_shared_from_config），
#     再把 BPP_LIBS_SHARED 重定向到 static 目标、注入 bpp-seq_DIR/bpp-core_DIR  # ⑤
```

```diff
# patches/0001-ohos-test-link-static.patch —— ④ 测试改链静态归档
-  target_link_libraries (${test_name} ${PROJECT_NAME}-shared)
+  target_link_libraries (${test_name} ${PROJECT_NAME}-static)
```

## 验证

```bash
# 产物架构
readelf -h <pkg>/lib/libbpp-*.a | grep Machine        # → AArch64
# 上游测试真实执行（由官方 CI 设备原生给出；本地交叉环境 can_run()=False 时如实记为 skipped）
ctest --output-on-failure
```

## 关联条目

- 根因细化：E543（CMAKE_CXX_FLAGS 覆盖交叉目标）
- 同族成员：libbpp-core / libbpp-seq / libbpp-phyl / libbpp-raa / libbpp-seq-omics，
  剩余 libbpp-popgen / libbpp-phyl-omics 可照此骨架直接适配
