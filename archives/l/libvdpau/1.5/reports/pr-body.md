## PR 信息
- **三方库名称**：libvdpau
- **上游版本**：1.5
- **上游仓库地址**：https://gitlab.freedesktop.org/vdpau/libvdpau/-/archive/1.5/libvdpau-1.5.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | dlclose（test/dlclose.c，FD 泄漏回归：dlopen 包装库 + X 显示连接 + vdp_device_create_x11 + dlclose） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **1** | `meson test --list` 清点 |

### 是否存在对上游测试用例的修改？
否（补丁只修复构建系统依赖声明，不触及测试用例本身）

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 一致 | dlclose 以 conanrun 环境真实执行：dlopen(libXext.so.6)✅ → dlopen(libvdpau.so)✅ → XOpenDisplay 返回 NULL（OHOS 无 X server）→ 上游自身 return SKIP(77)；meson 汇报 Ok:0 Fail:0 Skipped:1 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.c：链接真实 libvdpau.so 调用唯一导出符号 vdp_device_create_x11，断言完整 dlopen 分发链返回 VDP_STATUS_NO_IMPLEMENTATION，5/5 断言通过（CI L1e 反向破坏验证证实真实依赖） |
| **合计** | **2** | | |

---

## 上游测试用例修改说明
patches/0001-trace-declare-x11-dependency.patch（1 行，可移植性修复，
非平台裁剪）：trace/meson.build 的 `dependencies : libdl` →
`dependencies : [libdl, x11]`。vdpau_trace.cpp 经 vdpau_x11.h 间接包含
X11/Xlib.h，上游未声明该依赖（假定系统头文件在默认搜索路径）。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: meson
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: meson, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 上游 dlclose: SKIP(77)（无 X server，上游内置出口）; test_package: 5/5 断言通过; 跳过原因均有技术说明（R51） |
| 动态依赖 | PASS | 依赖: libx11/6.4.0, libxext/6.4.0.1, xorgproto/2025.1 |

### 补丁说明
- `0001-trace-declare-x11-dependency.patch`: 0001-trace-declare-x11-dependency.patch (修改文件: b/trace/meson.build)

### 依赖
- libx11/6.4.0
- libxext/6.4.0.1
- xorgproto/2025.1

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=meson 依赖探测 x11/xext/dri2proto, 解决方案=交叉/设备环境无系统 X11
- **2**: 根因=meson 可能按裸名 llvm-ar 探测归档器, 解决方案=CI PATH 不含 SDK bin
- **4**: 根因=meson install 重写 .so（剥 build rpath）→ 链接器 OHOS 自签失效 → XPM 拒绝加载（dlopen 与 DT_NEEDED 均报 Permission denied）, 解决方案=meson minstall 的 rpath 重写破坏 .codesign 完整性（cairo ML-0043 同场景）
- **5**: 根因=meson 找不到 dri2proto 依赖, 解决方案=MesonToolchain 在 machine file 写死 pkg_config_path=generators 目录，meson 用它**替换**（非追加）env PKG_CONFIG_PATH（mesonbuild pkgconfig.py _get_env: env.set），xorgproto 经 buildenv_info 注入的 share/pkgconfig 被遮蔽
- **6**: 根因=trace/vdpau_trace.cpp 报 X11/Xlib.h not found, 解决方案=上游 trace/meson.build 未声明 x11 依赖（依赖系统头文件默认路径），meson 只给声明了依赖的目标传 -I
- **7**: 根因=meson test 默认 conanbuild 环境缺 host 依赖 libdir → dlclose 测试在第一步 dlopen(libXext) 即跳过, 解决方案=conanbuild 不携带 host 依赖 libdirs

### 验证命令
```
```bash
conan create archives/l/libvdpau/1.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit 0
# meson test: Ok:0 Fail:0 Skipped:1（dlclose 无 X server，上游自身 return 77）
# test_package: libvdpau wrapper dlopen dispatch OK: status=1 (no backend, as expected)
# 包内容: lib/libvdpau.so{,.1,.1.0.0}(SONAME=libvdpau.so.1) lib/vdpau/libvdpau_trace.so*
#         include/vdpau/{vdpau.h,vdpau_x11.h} lib/pkgconfig/vdpau.pc etc/vdpau_wrapper.cfg
# 全部 .so 经 binary-sign-tool 自签，dlopen 实测通过
```

```
