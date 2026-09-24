# DRAFT-augustus-module-findsdl2-cache-vars：MODULE 模式自带 FindSDL2 不消费 CMAKE_PREFIX_PATH，需经缓存变量注入依赖路径

> Status: **Draft**（待审核 promote）| severity: `2` | category: `cmake, find-module, sdl2, conan, dependency-injection` | Updated: 2026-08-26
> 来源: augustus-game 4.0.0 适配：MODULE 模式 FindSDL2 配方注入实战
> 对应: `knowledge/drafts/DRAFT-augustus-module-findsdl2-cache-vars.kv`

---

## 触发面

- trigger_tool: `cmake|conan|CMakeToolchain`
- phase: `configuration`

**匹配关键词**：FindSDL2, MODULE mode, CMAKE_PREFIX_PATH, SDL2_INCLUDE_DIR, SDL2_LIBRARY_TEMP, FIND_LIBRARY, sdl2 package folder, cache variable injection, CMakeToolchain, tc.variables

## 错误签名（error_signature）

```text
Could NOT find SDL2|find_package\(SDL2 REQUIRED\).*CONFIG.*MODULE| SDL2_INCLUDE_DIR.*NOTFOUND|SDL2_LIBRARY.*NOTFOUND| Could not find SDL2_mixer
```

## 根因（root_cause）

部分上游项目（augustus、Julius 系）在 cmake/ 目录自带 FindSDL2.cmake / FindSDL2_mixer.cmake（MODULE 模式），其 FIND_PATH/FIND_LIBRARY 只认自身 缓存变量与环境变量（SDL2DIR 等），不消费 CMAKE_PREFIX_PATH 与 Conan CMakeDeps 生成的 *Config.cmake。Conan 依赖即使就绪，configure 仍报 "Could NOT find SDL2"。

## 推荐方案（rec_approach: `cmake-cache-var-injection`）

在配方 generate() 中用 CMakeToolchain 的 tc.variables 预置模块读取的缓存变量， 指向依赖包内路径：SDL2_INCLUDE_DIR=<sdl2>/include、 SDL2_LIBRARY=<sdl2>/lib/libSDL2.a、SDL2_MIXER_INCLUDE_DIR=<mixer>/include/SDL2、 SDL2_MIXER_LIBRARY=<mixer>/lib/libSDL2_mixer.a。关键细节： FindSDL2 尾部以 SDL2_LIBRARY_TEMP 回写 SDL2_LIBRARY，若只注入 SDL2_LIBRARY， FIND_LIBRARY(SDL2_LIBRARY_TEMP) 可能意外命中系统同名库并回写覆盖注入值 —— TEMP 必须一并预置。静态链接时链接顺序须被依赖库在后（mixer 先于 SDL2）。

## 修复命令（rec_command）

```text
tc.variables["SDL2_INCLUDE_DIR"] = os.path.join(sdl2.package_folder, "include"); tc.variables["SDL2_LIBRARY"] = os.path.join(sdl2.package_folder, "lib", "libSDL2.a"); tc.variables["SDL2_LIBRARY_TEMP"] = <同 SDL2_LIBRARY>; tc.variables["SDL2_MIXER_INCLUDE_DIR"] = os.path.join(mixer.package_folder, "include", "SDL2"); tc.variables["SDL2_MIXER_LIBRARY"] = os.path.join(mixer.package_folder, "lib", "libSDL2_mixer.a")
```

## 兜底方案（fallback_approach: `patch-find-module`）

补丁修改上游 Find 模块加入 HINTS 路径；侵入性更高，仅当缓存变量注入与 上游模块逻辑冲突时使用。

## 验证方式（verification_cmd）

```text
grep -n "SDL2_LIBRARY" build/*/CMakeCache.txt
```

## 关联

- **相似**：E285

---

*本文件由 `knowledge/drafts/DRAFT-augustus-module-findsdl2-cache-vars.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
