# cogl 1.22.8 上游测试分析（本地实测）

## 测试布局（上游 cogl-1.22.8/tests/ 清点）

| 目录 | 构建方式 | 用例数 |
|------|----------|--------|
| conform/ | `test-conformance` 单二进制 + test-launcher.sh 逐用例 | 注册 52（ADD_TEST）+ 未移植 12（UNPORTED_TEST，源码在 Makefile.am unported_test_sources） |
| unit/ | `test-unit` 单二进制 + gmodule 反射，用例 = 库内 `UNIT_TEST()` 宏（白盒，编译进 libcogl 内部，需 ENABLE_UNIT_TESTS） | 7 |
| micro-perf/ | `test-journal` 独立程序（glib 定时器渲染循环） | 1 |
| data/ | 仅测试图片资源 | 0 |

**合计 72 个上游测试用例。**

### conform 注册 52 用例（test-conform-main.c）

test_pipeline_user_matrix, test_blend_strings, test_blend, test_premult,
test_path, test_path_clip, test_depth_test, test_color_mask,
test_backface_culling, test_layer_remove, test_sparse_pipeline,
test_npot_texture, test_sub_texture, test_pixel_buffer_map,
test_pixel_buffer_set_data, test_pixel_buffer_sub_region, test_texture_3d,
test_wrap_modes, test_texture_get_set_data, test_atlas_migration,
test_read_texture_formats, test_write_texture_formats, test_alpha_textures,
test_wrap_rectangle_textures, test_primitive, test_just_vertex_shader,
test_pipeline_uniforms, test_snippets, test_custom_attributes, test_offscreen,
test_framebuffer_get_bits, test_point_size, test_point_size_attribute,
test_point_size_attribute_snippet, test_point_sprite, test_point_sprite_orientation,
test_point_sprite_glsl, test_version, test_alpha_test, test_map_buffer_range,
test_primitive_and_journal, test_copy_replace_texture,
test_pipeline_cache_unrefs_texture, test_pipeline_shader_state,
test_gles2_context, test_gles2_context_fbo, test_gles2_context_copy_tex_image,
test_euler_quaternion, test_color_hsl, test_fence, test_texture_no_allocate,
test_texture_rg

### conform 未移植 12（UNPORTED_TEST，不注册）

test_object, test_fixed, test_materials, test_readpixels, test_multitexture,
test_texture_mipmaps, test_texture_rectangle, test_texture_pixmap_x11,
test_vertex_buffer_contiguous, test_vertex_buffer_interleved,
test_vertex_buffer_mutability, test_viewport

### unit 白盒 7（cogl/*.c 内 UNIT_TEST 宏）

check_bitmask_api（cogl-bitmask.c）、check_blend_constant_ancestry +
check_uniform_ancestry（cogl-pipeline-state.c）、check_pipeline_pruning
（cogl-pipeline-cache.c）、check_point_size_shader
（driver/gl/cogl-pipeline-vertend-glsl.c）、check_gl_blend_enable
（driver/gl/cogl-pipeline-opengl.c）、check_mesa_driver_package_parser
（cogl-gpu-info.c）

## 分类：纯 CPU vs 需 GL（逐文件判定）

**关键事实（本机实测）：** OHOS aarch64 设备无 `/dev/dri`（无 GPU 节点）、
无显示服务。实测 `cogl_context_new(NULL)` 直接 SIGSEGV（rc=139，无任何
stdout 输出）——cogl 所有 52 个 conform 注册用例的入口 `test_utils_init()`
第一步就是 `cogl_context_new(NULL)`（test-fixtures/test-utils.c L176），
随后 `cogl_offscreen_new_with_texture()` + `cogl_framebuffer_allocate()`，
因此**全部 conform 注册用例在本机不可运行**（即便个别用例体内只用
CPU 数学函数）。

### 纯 CPU 子集（3 例，源文件零改动归档在 upstream_unit/）

| 用例 | 源文件 | 判定依据 |
|------|--------|----------|
| test_color_hsl | tests/conform/test-color-hsl.c | 仅调 `cogl_color_init_from_4ub`/`cogl_color_to_hsl`/`cogl_color_init_from_hsl`/`cogl_color_get_*`——纯颜色空间数学，不引用 test_ctx/test_fb/任何渲染 API；本地实跑 rc=0 |
| test_no_gl_header | tests/conform/test-no-gl-header.c | 空函数体，唯一作用是 `#include <cogl/cogl.h>` 后 `#ifdef GL_TRUE → #error`（验证公共头不泄漏 GL 头）；本地实跑 rc=0 |
| test_version | tests/conform/test-version.c | 仅 `COGL_VERSION_*` 宏静态断言 + 版本串比较（`g_strdup_printf`），不引用 test_ctx/test_fb；本地实跑 rc=0 |

注意：这 3 例虽经 test-launcher 注册（其 test_utils_init 会建 GL
context），但**用例函数体本身是纯 CPU**。本归档绕过 test_utils_init、
用最小 main 桩直接调用例函数，只验证用例逻辑本身——这是对安装包
（--disable-unit-tests 构建）可复现的最大真实子集。

### 需 GL 清单（逐条：测试名 + 具体依赖）

以下用例函数体或 harness 依赖 GL 渲染环境（cogl_context_new /
framebuffer / texture 渲染 / GL 驱动状态），本机 cogl_context_new 即
segfault，全部如实记录省略：

- test_pipeline_user_matrix：cogl_framebuffer_orthographic/draw_rectangle/read_pixels + cogl_texture_new_from_data + cogl_pipeline_set_layer_*（离屏渲染+读回像素）
- test_blend_strings / test_blend / test_premult：cogl_pipeline_set_blend + cogl_rectangle 渲染 + read_pixels 像素断言
- test_path / test_path_clip：cogl_path_* + framebuffer 渲染（另需 cogl-path 组件）
- test_depth_test：cogl_set_depth_test_enabled + 渲染 + 像素断言
- test_color_mask：cogl_rectangle 渲染 + 像素断言
- test_backface_culling：cogl_pipeline_set_face_culling + 渲染 + 像素断言
- test_layer_remove：cogl_pipeline_set_layer_* + 渲染
- test_sparse_pipeline / test_texture_3d / test_npot_texture / test_sub_texture：纹理创建+渲染（3D 另需 COGL_FEATURE_ID_TEXTURE_3D）
- test_pixel_buffer_map / set_data / sub_region：cogl_buffer_new + 顶点渲染
- test_wrap_modes：cogl_texture 环绕模式 + cogl_vertex_buffer_draw + 像素断言
- test_texture_get_set_data / test_atlas_migration：cogl_texture_set/get_data 经 framebuffer 往返
- test_read_texture_formats / test_write_texture_formats：cogl_texture_2d_new_from_data + set/get_data 像素格式转换（走 GL 纹理存储）
- test_alpha_textures / test_wrap_rectangle_textures / test_texture_rg / test_texture_no_allocate：纹理分配/格式（texture_no_allocate 检查 cogl_has_feature，需 context）
- test_primitive / test_primitive_and_journal / test_custom_attributes：cogl_primitive_* 几何体渲染（custom_attributes 需 GLSL）
- test_just_vertex_shader / test_pipeline_uniforms / test_snippets / test_pipeline_shader_state：GLSL shader（需 COGL_FEATURE_ID_GLSL + 驱动编译）
- test_offscreen：cogl_offscreen_new_with_size + cogl_framebuffer_finish 渲染
- test_framebuffer_get_bits：离屏 FBO 读写（需 TEST_REQUIREMENT_OFFSCREEN|GL）
- test_point_size / test_point_size_attribute / test_point_sprite(_orientation/_glsl)：渲染 + 点精灵 GL 特性
- test_alpha_test：cogl_pipeline_set_alpha_test + 渲染
- test_map_buffer_range：cogl_buffer_map 写顶点（需 MAP_BUFFER_FOR_WRITE）
- test_copy_replace_texture：纹理复制/替换渲染
- test_pipeline_cache_unrefs_texture：渲染后断言 pipeline cache 引用计数
- test_gles2_context / _fbo / _copy_tex_image：EGL 创建 GLES2 上下文/FBO（需 GLES2 设备）
- test_euler_quaternion：cogl_framebuffer_identity_matrix/rotate_euler/rotate_quaternion/get_modelview_matrix——矩阵数学虽是 CPU，但函数体直接操作 test_fb（framebuffer 对象，由 GL context 创建）
- test_fence：cogl_framebuffer_wait_fence + glib mainloop（需 FENCE 特性/GL）
- **unit 白盒 7**：编译进 libcogl 内部（--disable-unit-tests 下不导出）；其中 check_bitmask_api / check_mesa_driver_package_parser 函数体本身是纯 CPU（bitmask 位运算、Mesa 版本串解析），但依赖 `_cogl_bitmask_*`/`_cogl_gpu_info_parse_*` 内部符号与 test_ctx，无法对安装包复跑，如实记录省略
- **micro-perf 1**（test-journal）：cogl_context/framebuffer 800x600 渲染循环计时

## 实跑统计（本地，2026-08-31，OHOS aarch64 clang 15）

- 纯 CPU 子集：运行 3 / 通过 3 / 失败 0（consumer 链接检查另计 1 通过）
- 需 GL：运行 0 / 通过 0 / 失败 0 / 省略 69（系统级：无 /dev/dri，
  cogl_context_new SIGSEGV）——非测试失败，属环境不可运行，如实记录
- 本地验证日志：/storage/Users/currentUser/tmp/cogl_create4.log
  （conan create 全程 ALL PASS）、/storage/Users/currentUser/tmp/cogl_tp_sim.log
  （test_package 单独预演，ALL PASS）

## 归档最小化说明（只提必要文件）

- upstream_unit/ 仅含 3 个纯 CPU 测试源文件（零改动，sha 与上游一致）
- 不搬：test-launcher.sh/run-tests.sh（GL 驱动矩阵遍历，本机无 GL）、
  test-fixtures/（test-utils.c 的 init 全路径建 GL context，且 3 个用例
  只需 cogl_test_verbose 一个函数，运行时由 test_cogl.py 内联桩替代）、
  全部需 GL 的 test-*.c、data/ 图片
- test_cogl.py 运行时在临时目录生成 3 个最小 main 桩 + 空 config.h 桩
  + cogl-util.h 最小 shim（_COGL_STATIC_ASSERT = c11 _Static_assert，
  上游 cogl-util.h 原样展开）+ test-utils.h 最小桩（仅
  cogl_test_verbose 声明）——全部为构建胶水，不改动上游测试逻辑
