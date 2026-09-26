# libomxil 0.9.3 — 鸿蒙 PC conan 制品

上游：Bellagio open source implementation of the Khronos OpenMAX
Integration Layer API（libomxil-bellagio），
<https://sourceforge.net/projects/omxil/>。
`os=OHOS, arch=armv8`（= aarch64）的 conan 包，交付 OpenMAX IL 运行时全套件：

| 产物 | 说明 |
|---|---|
| `lib/libomxil-bellagio.so` | IL 核心库（OMX_Init / OMX_GetHandle / OMX_ComponentNameEnum …） |
| `lib/omxloaders/libomxdynamicloader.so` | 动态组件加载器插件（核心 dlopen 加载） |
| `lib/bellagio/*.so` | Bellagio 组件集：audio_effects（volume + audiomixer）、clocksrc、videoscheduler |
| `bin/omxregister-bellagio` | 组件注册表生成工具（部署必备，见下） |
| `include/OMX_*.h`、`include/bellagio/*.h` | Khronos IL 公共头 + Bellagio 扩展头 |
| `lib/pkgconfig/libomxil-bellagio.pc` | pkg-config 元数据 |

无外部依赖（核心库仅链接 libc/pthread/dl，musl 已折叠后两者）。

## 出包（鸿蒙 PC CI）

```bash
conan create . -pr:h=<ohos-aarch64 profile> -pr:b=<同一 profile>
```

> CI 为设备原生构建：`-pr:h` 与 `-pr:b` 均为 `ci/conan/profiles/ohos-aarch64`。
> 源码由 `conandata.yml` 的官方 URL 下载并校验 sha256。

## 消费

```bash
# conan 工程
conan install --requires=libomxil/0.9.3 -pr:h=<ohos-aarch64 profile>
# CMake:  target_link_libraries(app PRIVATE omxil-bellagio)
# pkg-config: pkg-config --cflags --libs libomxil-bellagio

# 裸程序（部署到 ~/usr/local 后直接链接/dlopen）
conan install --requires=libomxil/0.9.3 -pr:h=<ohos-aarch64 profile> \
    --deployer-folder=$HOME/usr/local
```

### 部署前必须生成组件注册表

Bellagio 是注册表驱动的：`OMX_Init()` 需要 `$OMX_BELLAGIO_REGISTRY`
（默认 `~/.omxregister`）存在，否则返回 ENOENT：

```bash
omxregister-bellagio ~/usr/local/lib/bellagio     # 写入默认注册表
# 或
export OMX_BELLAGIO_REGISTRY=/path/to/registry
omxregister-bellagio ~/usr/local/lib/bellagio
```

组件目录与 loader 目录（`${libdir}/bellagio`、`${libdir}/omxloaders`）
在 configure 期烧进二进制，包内布局自洽，勿单独搬动 `lib/`。

## 测试

`test_package/` 以消费者身份编译探针并在目标上执行，14 项断言全绿：

- 消费者 6 项：注册表生成 → `OMX_Init` → 组件枚举（4 组件）→
  `OMX_GetHandle`/`OMX_FreeHandle` → `OMX_Deinit`；
- 鸿蒙特有 8 项（H1~H8）：产物均为 AArch64 ELF64 DYN、`omxregister-bellagio`
  指向 OHOS 加载器、无 glibc 专属 soname（core 仅 `libc.so`）、
  loader 插件与全部组件库 `dlopen()` 成功并导出
  `setup_component_loader`/`omx_component_library_Setup`。

上游 `test/` 目录（X11 + 真实音视频设备依赖）不适配交叉环境，记为不随构建执行。

## 适配要点

详见同目录 `notes.md`。6 个补丁全部只做平台移植性修复：config.guess/config.sub
的 HarmonyOS/ohos 三元组支持（同 libm17n-core）、configure 辅助目录
umask 077→022（HMDFS）、去 `-Werror`（clang 15）、`src/base/rm.h` 全局变量
改 extern（lld `-fno-common`）、loader 插件补 `LIBADD` 指向 IL core
（musl 上 dlopen 对象只从自身依赖链解析符号，缺 `DT_NEEDED` 则 `RM_Init` 未解析）。另在 configure 预置
`ac_cv_func_malloc/realloc_0_nonnull`（musl 语义满足，规避 `rpl_malloc`
假阳性）；`package()` 清理上游 Makefile.am docdir/DESTDIR bug 产生的嵌套目录；
ELF 代码签名在 `package()` 末尾按 E135/E077/E489 执行（工具仅设备 worker
存在，其余环境自动跳过、由设备流水线补签）。
