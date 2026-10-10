# DRAFT — OpenGL-Registry main 快照缺 khrplatform.h：头文件包须随包 vendor 官方 Khronos 平台头

> 状态: 草稿（基于 opengl 4.6 R01 真实证据，2026-10-01，pc2-5）。
> 查重: E321/E257/E322 部分覆盖（header-only 打包机制）；本条目新增"registry 快照
> 缺头-头依赖平台头时随包 vendor 官方文件"场景与补丁位。

## 真实问题（场景）

opengl 4.6（Khronos OpenGL-Registry 头文件包, 知识库扩展, 官方来源
https://github.com/KhronosGroup/OpenGL-Registry）按 main 分支快照打包后，
消费者测试编译失败：

```
clang -c -I<package>/include xml/testesext.c
$B/xml/testesext.c:...: fatal error: 'KHR/khrplatform.h' file not found
```

根因定位: 官方 `api/KHR/khrplatform.h` 在 OpenGL-Registry main 分支已不存在——
`https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/api/KHR/khrplatform.h`
返回 404；而 `api/GL/glcorearb.h:63`、`api/GL/glext.h:37`、`api/GLES/gl.h:34`、
`api/GLES2/gl2.h:42`、`api/GLES3/gl3.h:42`、`api/GL/glplatform.h` 等全部
`#include <KHR/khrplatform.h>`。这是 Khronos 头文件体系内部的"头-头依赖"，
头文件包不自包含即编不过。

## 根因

OpenGL-Registry 主分支快照（2026 年中后内容, SHA-256 45dfcb6974…）不再包含
api/KHR/khrplatform.h（该文件由 EGL-Registry 仓库 `api/KHR/khrplatform.h` 维护,
MIT）。khrplatform.h 定义 KHRONOS_APICALL/KHRONOS_APIENTRY（调用约定）与
khronos_int8_t/int16_t/int32_t/int64_t/ssize_t/float_t 等平台抽象类型，是
GL/GLES/GLSC 全部头文件的公共依赖。上游 xml/Makefile 注释也明确 gl.h/glx.h/wgl.h
等平台头"experimental and not supported by Khronos, OS vendors provide them"——
registry 仓库只保证 api/ 下脚本生成头，不保证目录结构自包含，头-头依赖缺件风险
由此产生。

E321/E257/E322 覆盖 header-only 配方机制（package_type、cmake_layout、INTERFACE、
G1 完整性），但均在"上游 tarball 结构完整"前提下；本条目是 tarball 结构缺件的
**content 依赖链**场景，修复位在补丁（新增文件）而非配方字段。

## 推荐方案（验证命令）

**方法: vendor-official-khrplatform-in-header-package**

1. 从 EGL-Registry 获取官方 khrplatform.h:
   `curl -sS -L 'https://ghfast.top/https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/api/KHR/khrplatform.h' -o khrplatform.h`
   （11131 字节, sha256 7b1e01aaa7ad8f6fc34b5c7bdf79ebf5189bb09e2c4d2e79fc5d350623d11e83）
2. 生成 git 补丁 `patches/0001-add-khrplatform.h.patch`（new file api/KHR/khrplatform.h,
   index 行用 `git hash-object` 计算）, conandata.yml `patches:` 列表登记,
   conanfile.py `build()` 调 `apply_conandata_patches(self)`。
3. `package()` 复制整棵 api/ 树 → include/（含 KHR/khrplatform.h）。
4. 验证:
   ```
   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   # RC=0; 上游入口 testesext.c 编译通过; 消费者用例 9/9、鸿蒙专项 10/10 断言通过
   ```

## 适用边界

- 适用: Khronos GL/GLES/GLSC（及 Vulkan/EGL）头文件打包为 conan header-library；
  平台头由 OS vendor 提供、registry 只给"脚本生成头"的仓库（OpenGL-Registry 风格）。
- 反例: 有完整 include 目录与 CMake install 的上游头文件项目（如 glew/glad 自带
  KHR/khrplatform.h），或 OS SDK 已提供 KHR/khrplatform.h 的纯系统头消费场景，
  无需 vendor。

## 查重差异（七轴）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无同题条目 |
| causal_duplicate | false | E321/E257/E322 根因为 Conan API/配方机制, 本条目为上游快照结构缺件 |
| trigger_overlap | false | 触发面: include 解析失败 vs G1 配方完整性检查 |
| solution_overlap | partial | E321 也处理 header-only 打包, 不含 vendor 缺件平台头 |
| combination_novelty | true | "registry 快照缺 khrplatform.h + 补丁 vendor 官方文件"组合无既有条目 |
| boundary_novelty | true | 头文件包源码完整性依赖链（头-头 include 缺件） |
| test_migration_novelty | false | 无测试迁移维度 |

关系: similar_to=E321; caused_by=上游注册表仓库结构; prerequisite_of=后续 Khronos
头文件包（Vulkan/EGL）可复用本方; conflicts_with=无。

## 验证结果（本轮真实日志）

- 404 验证: `raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/api/KHR/khrplatform.h` → HTTP 404
- 修复前: `clang -c -I<package>/include xml/testesext.c` → fatal error 'KHR/khrplatform.h' file not found
- 修复后: 同命令 RC=0；conan create RC=0；ctest: consumer 1/1 + harmonyos 1/1 通过
  （消费者 9/9、鸿蒙 10/10 断言）；上游入口 testglext.c 因缺平台 GL/glx.h（X11/GLX,
  OHOS 无）记录为硬阻塞（台账内, 与本草稿无关）