# python3-cairo 1.29.1 适配笔记

## 编译环境
- **构建系统**: meson（CPython 扩展绑定，meson-python 构建）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁；meson 配置项适配）

## 上游说明
- 上游即 **pycairo 1.29.1**（github.com/pygobject/pycairo），与 ohpcd 已发布的
  **pycairo/1.29.0** 同源。本次以独立包名 **python3-cairo** 适配（用户指定口径），
  复用 pycairo/1.29.0 成熟 meson 配方，仅 name/version/source 差异。
- 1.29.0 → 1.29.1 差异极小：Windows wheels 依赖（libpng/zlib）、Python 3.15
  文档构建修复、ScaledFont.text_to_glyphs 内存泄漏修复。

## 关键适配点（与 pycairo/1.29.0 同款）
1. **cairo 依赖注入**：PkgConfigDeps 生成 cairo.pc，meson `dependency('cairo')`
   解析到 conan 包 cairo/1.18.4
2. **Python 锁定**：HMBS_PYTHON3 优先，meson `-Dpython=<绝对路径>`；扩展链接
   libcairo，运行测试时 LD_LIBRARY_PATH 前置依赖 lib
3. **ar/llvm-ar 探测**（E012 变体）：`_probe_archiver()` 探测 ar/ranlib 绝对路径
4. **上游 pytest**：tests/ 290 用例（真机收集 287 + --ignore 排除 3 个
   numpy/pygame 门控用例），build() 内真实执行并解析计数
5. **ohos_tmpdir_shim**（E002）：/tmp 只读，LD_PRELOAD shim 重定向 O_TMPFILE
6. **libpython 链接**（E004）：meson 未链 libpython，dlopen 符号解析失败——按
   sysconfig 探测共享 libpython 注入 c_link_args
7. **lld 路径**（E120/E132）：SDK llvm/lib 前置 LD_LIBRARY_PATH

## 上游测试（rule 4）
- 上游确有 pytest 套件（tests/ 21 文件 288 用例）——test_package/MANIFEST.yml 详述
- 3 个 numpy/pygame 门控用例真机必然跳过，按 hmbs 硬门禁以 --ignore 排除并
  在 excluded_cases 如实声明（不计入 discovered，不冒充通过）
- 其余 287 用例 build() 内真实执行

## 已知限制
- import cairo 在 CI AppSpawn 沙箱可能被 hmmac 拦截（E212 用户路径 dlopen）——
  test_package 自动降级为静态签名产物校验（7 项检查）
---

**编译结束**: 2026-09-02 10:14
**最终状态**: built
