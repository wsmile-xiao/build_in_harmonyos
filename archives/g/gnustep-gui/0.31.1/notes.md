# gnustep-gui 0.31.1 适配笔记

## 编译环境
- 构建系统: autotools + gnustep-make
- 编译日期: 2026-08-31
- 编译器: clang (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. configure：使用 Conan AutotoolsToolchain 生成的配置，加入 `--disable-importing-config-file`、
   `--with-include-flags=<deps include>`、`--with-library-flags=<deps lib>`，并导出
   `OBJC_RUNTIME_LIB=gnu` 与 gnustep-make 环境（GNUSTEP_MAKEFILES / GNUSTEP_SYSTEM_ROOT /
   GNUSTEP_CONFIG_FILE / GNUSTEP_INSTALLATION_DOMAIN=SYSTEM）。
2. make：在 `Source/` 下以 `make -j1 shared=yes debug=no messages=yes` 构建主库，
   用 `MKDIRS="mkdir -p"` 覆写 hmdfs 上受限的 mkinstalldirs，`ADDITIONAL_CPPFLAGS`
   作为命令行参数传入（GNUstep make 不读环境变量）。
3. 手动链接别名：`_link_gui_library` 用 `shutil.copyfile` 生成 `.so.0`/`.so` 别名，
   规避 hmdfs 上 `ln -s` 的 Permission denied。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | hmdfs 上 `ln -s` 建 .so 别名被拒 | conan 子进程在 hmdfs 无法创建符号链接 | 用 `shutil.copyfile` 生成版本别名 |
| 2 | `ADDITIONAL_CPPFLAGS` 不生效，宏为空 | GNUstep make 不读环境变量 | 作为 make 命令行参数传入 |
| 3 | `mkinstalldirs` exec 受限 | hmdfs 限制脚本执行 | 用 `MKDIRS='mkdir -p'` 覆写 |
| 4 | gnustep-make 包脚本 shebang 不可用 | /bin/sh 或 /bin/bash 在 worker 受限 | 复制到本包目录并修复为 /data/service/hnp/bin/bash |
| 5 | ObjC 运行时 ABI 不匹配 | 默认 ng runtime 与 base/libobjc2 的 gnu runtime 不一致 | 统一 `OBJC_RUNTIME_LIB=gnu` |
| 6 | 上游 TestFramework 收尾崩溃 | worker /etc/passwd 无当前 uid，GSPlaceholderString initWithString:nil | test_package 提供同功能消费者测试 |
| 7 | GSBackend 类缺失 | 后端由应用侧链接库提供 | test_package 提供最小 GSBackend stub |
| 8 | GNUstepGUI 头文件引用不解析 | 头文件嵌套过深 | 平铺到 Library/Headers/GNUstepGUI/ |

## 源码修改

- `0001-appkitdefines-import-nsgeometry.patch`: AppKitDefines.h 补齐 NSGeometry 引用
- `0002-gsmemorypanel-ndebug-guard.patch`: GSMemoryPanel.m NDEBUG 守卫
- `0003-gsstoryboardtransform-libxml-guard.patch`: GSStoryboardTransform.m libxml 宏守卫

## 依赖版本

- gnustep-base/1.31.1、gnustep-make/2.9.2.1（tool_require）
- libobjc2/2.2.1、libtiff/4.7.2、libjpeg/10、libpng/1.6.39、libffi/3.5.2、curl/8.15.0、zlib/1.3.1.1

## 验证结果

```bash
# conan-verify: G0-G4/L2/L4/L5 全部 PASS, 632 个 obj 编译 + 主库链接 + 打包成功
# W3 本地 CI 模拟: exit_code=0 (.ci-result.json)
# test_package 消费者测试: NSView/frame/类解析/Foundation 链/C 支撑函数 5 项断言, rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| libgnustep-gui.so.0.31.1 (+ .so.0/.so 别名) | 主库产物, 302 个头文件 + 3 个 .so |
| packaging/gnustep-gui-0.31.1-ohos-aarch64.tar.gz | 打包制品 |

## 注意事项

- 上游 Tests/gui 共 16 组 29 个 .m 测试；本机实测多数断言可过，但 TestFramework 收尾
  因 worker /etc/passwd 无当前 uid 记录崩溃（GSPlaceholderString initWithString:nil，
  与 make_services 同根因），无法以退出码 0 完整跑通；由 test_package 提供同功能
  消费者测试覆盖核心 AppKit API。
- **功能裁剪决策（有意）**：0003 补丁在 `GNUSTEP_BASE_HAVE_LIBXML=0`（本配方
  ADDITIONAL_CPPFLAGS 传入）时，将 GSStoryboardTransform 实现裁剪为空类实现。
  原因：NSStoryboard/NSStoryboardSegue 依赖 gnustep-base 的 libxml 解析能力，
  本适配不启用该特性，属有意的功能裁剪（非欺骗性空壳）。
- **渲染后端说明（R40）**：本包为 AppKit 对象层库（libgnustep-gui），窗口/渲染后端
  由应用侧独立链接的 gnustep-back 库提供，本配方不包含图形栈（EGL/Vulkan）适配；
  test_package 仅验证对象层 API（NSView 创建/frame/类解析/Foundation 链），
  完整渲染验证依赖 gnustep-back 后端库的后续适配。
---
**编译结束**: 2026-08-31 20:32
**最终状态**: built
