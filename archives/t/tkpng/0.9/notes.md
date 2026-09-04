# tkpng 0.9 适配笔记

## 编译环境
- **构建系统**: autotools（TEA —— Tcl Extension Architecture）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/tkpng/0.9 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 SourceForge 官方发行下载并 strip_root
（目录 tkpng0.9）。

### 2. 构建（build()）
- 纯 C Tcl/Tk 扩展（generic/tkImgPNG.c + tkImgPNGInit.c），无编译障碍
- TEA autotools：`./configure --with-tcl=<tclConfig.sh 目录>` + make
- 产物：tkpng0.9.so

### 3. 打包（package()）
- 产物拷到 `lib/libtkpng0.9.so`
- 依赖 tk/9.0.3.2（自动带 tcl/9.0.3.2，均已发布）+ zlib/1.3.1.1.1（已发布）

## 上游测试（rule 4）
- 上游无测试套件（纯 C Tcl 扩展，仅 generic/*.c + ChangeLog）——rule 1.2 如实声明
- 适配后：test_package R34 真实产物校验——libtkpng0.9.so 存在 + 有效 ELF
  shared object + 导出 tkImgFmtPNG 符号（1/1 = 100%）；OHOS 沙箱无法运行
  tclsh9.0（tcl 包自身 libtcl9.0.so E212 类 dlopen 限制），故用 ELF 产物校验

## 已知限制
- 无（依赖链全就绪）
---

**编译结束**: 2026-09-02 01:42
**最终状态**: built
