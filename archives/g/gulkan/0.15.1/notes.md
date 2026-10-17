# gulkan 0.15.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-29
- 编译器: clang/clang++（OHOS aarch64 profile）
- 状态: built

## 编译步骤
1. `conan create archives/g/gulkan/0.15.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. MesonToolchain + PkgConfigDeps；关键：`[binaries] glib-compile-resources = <host glib>/bin/...`
3. generate() 手写 `vulkan.pc`（Cflags 指向已发布 vulkan-headers，Libs 指向系统 `/system/lib64 -lvulkan`）
4. build(): meson.configure()+build()，build_tests=false 关闭上游 GPU 测试子目录
5. package(): meson.install() + **_self_sign_elfs()**（对 bin/lib 内 ELF 做 binary-sign-tool selfSign）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 版本冲突 zlib/1.3.1 vs 1.3.1.1（originates glib2/2.88.0） | graphene 拉 glib2（钉 1.3.1 无 -fPIC），gdk-pixbuf/cairo 拉 1.3.1.1（-fPIC，E005/E234） | `requires("zlib/1.3.1.1", override=True)`，同已合并 awf-gtk/4.2.0 |
| 2 | `meson: libintl_gettext: symbol not found`（meson 自身崩） | 曾 tool_requires(glib) 取 glib-compile-resources；VirtualBuildEnv 把 glib 的 proxy libintl.so.8（只导出 g_libintl_*）前插 LD_LIBRARY_PATH，遮蔽 hnp python 需要的真 gettext libintl（musl: LD>RUNPATH） | **移除 glib 的 tool_requires**；改用 `MesonToolchain.binaries["glib-compile-resources"]` 从 host glib 包注入 |
| 3 | `gnome.compile_resources: Could not get pkg-config variable` | conan 生成的 gio-2.0.pc 无 glib_compile_resources pkgvar，meson find_tool 在 pkgconfig 分支抛异常（未走 PATH 兜底） | 用 `[binaries]` 注册工具（find_tool 第一优先级即命中） |
| 4 | `gulkan-texture.c:50 VkFormat from void* [-Wint-conversion]` | 上游 bug：`self->format = VK_NULL_HANDLE`（VK_NULL_HANDLE 是 `((void*)0)`，VkFormat 是枚举） | patch 改 `VK_FORMAT_UNDEFINED` |
| 5 | test_package dlopen `libgulkan-0.15.so.0: Permission denied`（errno13）；glib-compile-resources exec `Operation not permitted` | OHOS 设备对安装包目录未签名 ELF 施加强制代码签名（手册 §7 ELF 签名；chmod 无效=SELinux 域） | package() 末尾 `binary-sign-tool sign -selfSign 1` 给产物补签名段；全 guard（非 OHOS/无工具/失败均跳过），CI 安全 |
| 6 | test() `self.run([exe])` → sh 127；相对路径 cwd 不对 | 列表被 shell 当字面量；basic_layout 产物在 build 根但 cwd 非该目录 | 绝对路径字符串 + `env="conanrun"`（VirtualRunEnv 在 generate 期聚合，test() 里 save_script 无效） |
| 7 | 库名/include 写成 gulkan-0.1 | 制品实为 api_version=0.15（`libgulkan-0.15.so`，include/gulkan-0.15） | cpp_info.libs/includedirs 用 -0.15；公共头 transitive_headers 传播 glib/gdk-pixbuf/graphene/vulkan |

## 源码修改（3 patch，refresh-patch 生成，conandata strip:1）
- `0001-meson.build.patch`：shaders/res/tests 子目录用 `get_option('build_tests')` 守卫（上游 GPU 测试，headless CI 不可运行且依赖构建期 gresource）
- `0002-meson_options.txt.patch`：新增 `build_tests` option（默认 false）
- `0003-src-gulkan-texture.c.patch`：VK_NULL_HANDLE→VK_FORMAT_UNDEFINED（见问题4）

## 依赖版本
- 在仓：glib/2.84.0.1、gdk-pixbuf/2.44.6.1、graphene/1.10.8、cairo/1.18.4、vulkan-headers/vulkan-sdk-1.4.357.0、zlib/1.3.1.1(override)
- tool：meson/1.11.0、pkgconf/3.0.5、glslang/vulkan-sdk-1.3.290.0
- vulkan loader：系统 `/system/lib64/libvulkan.so`（制品仓无 vulkan-loader，其配方在 main 但发布停滞 wish-1927）

## 验证结果
```bash
# conan-verify 8 门禁全过（G0-G4 + L2/L4/L5）
# test_package：5 断言 PASS（gulkan_instance_new / GULKAN_IS_INSTANCE /
#   get_handle==VK_NULL_HANDLE + vkEnumerateInstanceExtensionProperties==VK_SUCCESS / 扩展数>0(本机=13)）
# 设备实测：conan test 输出 "PASS: gulkan real API + loader path exercised"
# dlopen 全链：libgulkan→libcairo/libgio/libgobject/libgdk_pixbuf 加载通过（签名后）
```

## 注意事项
- 上游 gulkan 无 conan 官方配方，配方为手写
- 上游 6 个测试（test_instance/device/client/texture/texture_external/renderer）带
  g_assert 断言，但需活动 Vulkan 设备+ICD，且构建期要执行 glib-compile-resources/
  glslangValidator（gresource/shader 载荷）——headless CI 双条件均不满足 →
  build_tests=false 关闭构建（上游测试源码零删改）；消费者测试补足 loader 真实路径
  断言（vkEnumerateInstanceExtensionProperties，不依赖 ICD）回应 R40
- CI worker home 为 `.cache/conan2`（与本包已发布依赖内嵌 RPATH 一致），本地若遇 ../../bin 相对 DT_NEEDED 加载失败参考 ktextwidgets notes（本次 gulkan 未触发）
---

**编译结束**: 2026-08-29 12:04
**最终状态**: built
