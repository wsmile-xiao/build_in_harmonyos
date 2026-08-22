# 测试报告 — abiword-plugin-paint 3.0.8

> **项目**: abiword-plugin-paint  
> **测试日期**: 2026-08-13  
> **测试环境**: HarmonyOS HongMeng Kernel aarch64（OHOS 6.0 / armv8，clang 15）  
> **测试类型**: 适配自研端到端测试（上游无官方测试）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 23 | 100% |
| 通过 (PASS) | 23 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

> 说明：上游 AbiWord 3.0.8 的 paint 插件**无任何官方测试**
> （plugins/paint/ 仅含 AbiGeneric.{cpp,h} + AbiPaint.{cpp,h} + unix/ut_UnixProcess.cpp
>  + Makefile.am，全树无 tests 目录）。本报告所有用例均为 OHOS 适配自研
> （tests/test_paint_plugin.cpp 端到端测试 + test_package/run_test.cpp 消费者测试）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 插件模块构建成功并可通过 dlopen 加载，AbiWord 运行时兼容 shim
（XAP_App/XAP_Frame/XAP_Prefs/EV_* 等）驱动注册/注销全链路正常。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无（构建期 E114/E074 平台陷阱已在编译期解决） | 无 | 🟢 |

### 2.3 可用功能清单

```
✅ 插件模块 dlopen 加载（libabiword-plugin-paint.so → lib/abiword-3.0/plugins/）
✅ abi_plugin_supports_version(3,0,8) 版本门禁
✅ abi_plugin_register → XAP_ModuleInfo 填充（name/desc/version/author/usage）
✅ 偏好方案（_AbiPaint_ scheme）创建与默认值写入（szImageEditor / bLeaveImageAsPNG）
✅ 菜单项注册（addToMenus：Main + ContextImageT）与注销清理（removeFromMenus）
✅ EditMethod 注册（AbiPaint_PluginCallback_editImage / specify）与查找
✅ abi_plugin_unregister → XAP_ModuleInfo 清空 + 菜单清理
⚠️ 实际调用外部图像编辑程序（editImage 完整流程）依赖真实 AbiWord GUI 环境，headless 下不执行
```

### 2.4 已知限制

1. `editImage` 完整流程（启动外部编辑器、等待修改、回写图片）依赖真实 AbiWord GUI 与外部程序，headless 测试环境不执行该路径；shim 中 FV_View::saveSelectedImage/getSelectedImage 返回 0（无图像选中）。
2. 上游无测试框架，所有用例为适配自研（R34 实质依赖已通过 make check 端到端 + test_package dlopen 验证）。

---

## 三、测试详情

### 3.1 通过的测试（make check — tests/test_paint_plugin.cpp，23 项断言）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | PLUGIN_SO env set | 测试环境变量 | ✅ PASS |
| 2 | dlopen(plugin .so) | 模块加载 | ✅ PASS |
| 3 | dlsym(abi_plugin_supports_version) | 导出符号 | ✅ PASS |
| 4 | dlsym(abi_plugin_register) | 导出符号 | ✅ PASS |
| 5 | dlsym(abi_plugin_unregister) | 导出符号 | ✅ PASS |
| 6 | abi_plugin_supports_version(3,0,8) | 版本门禁 | ✅ PASS |
| 7 | abi_plugin_register() returns 1 | 注册返回值 | ✅ PASS |
| 8 | XAP_ModuleInfo.name == 'AbiPaint' | 模块信息 | ✅ PASS |
| 9 | XAP_ModuleInfo.desc mentions image editing | 模块信息 | ✅ PASS |
| 10 | XAP_ModuleInfo.version contains 3.0.8 | 模块信息 | ✅ PASS |
| 11 | XAP_ModuleInfo.author + usage filled | 模块信息 | ✅ PASS |
| 12 | XAP_App::getApp() | 应用单例 | ✅ PASS |
| 13 | XAP_App::getPrefs() | 偏好对象 | ✅ PASS |
| 14 | plugin scheme '_AbiPaint_' registered | 偏好方案 | ✅ PASS |
| 15 | getValue(szImageEditor) exists | 偏好默认值 | ✅ PASS |
| 16 | getValueBool(bLeaveImageAsPNG) exists | 偏好默认值 | ✅ PASS |
| 17 | menu items added by addToMenus() | 菜单注册 | ✅ PASS |
| 18 | edit methods added to container | EditMethod 注册 | ✅ PASS |
| 19 | editImage edit method registered | EditMethod 注册 | ✅ PASS |
| 20 | specify edit method registered | EditMethod 注册 | ✅ PASS |
| 21 | abi_plugin_unregister() returns 1 | 注销返回值 | ✅ PASS |
| 22 | XAP_ModuleInfo cleared by unregister | 注销清理 | ✅ PASS |
| 23 | menu items removed by removeFromMenus() | 菜单清理 | ✅ PASS |

### 3.2 通过的测试（test_package/run_test.cpp，消费者视角）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| dlopen 安装的插件 .so | 消费者加载 | ✅ PASS |
| abi_plugin_supports_version(3,0,8) | 版本门禁 | ✅ PASS |
| abi_plugin_register → XAP_ModuleInfo 字段非空 + name=AbiPaint + version 含 3.0.8 | 模块信息校验 | ✅ PASS |
| abi_plugin_unregister | 注销 | ✅ PASS |

### 3.3 失败的测试

无。

### 3.4 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| editImage 端到端调用外部编辑器 | headless 环境无 GUI/外部编辑器，属功能限制非测试失败 |

---

## 四、关键问题分析

### 问题1: compat/ 残留 libtool 构建产物导致 conan create 链接失败

**现象**：
```
libtool: error: 'compat/libabiword_plugin_paint_la-abiword_shim.lo' is not a valid libtool object
make: *** [Makefile:754: libabiword-plugin-paint.la] Error 1
```

**根因分析**：
explore 阶段直接在源码树（compat/）内执行过 make，残留 .lo/.o/.dirstamp/.Plo 等
libtool 构建产物；conanfile.py `export_sources()` 用 `copy(self, "*", ...)` 全量复制
compat/，把构建产物一并发布进 recipe，conan create 在干净源码树构建时混入脏 .lo。

**解决方案**：
归档前清理 compat/、tests/ 下全部构建产物（find .deps/.libs -type d -delete + *.lo/*.o/*.Plo/*.Po/*.dirstamp -delete），只保留源文件。已在 notes.md 沉淀为注意事项。

### 问题2: compat/xap_Frame.h 使用嵌套枚举报 incomplete type

**现象**：
```
compat/xap_Frame.h:23: error: incomplete type 'XAP_Dialog_MessageBox' named in nested name specifier
```

**根因分析**：
xap_Frame.h 仅前置声明 class XAP_Dialog_MessageBox，而 showMessageBox 签名引用其
嵌套类型 tAnswer/tButtons，需要完整定义。

**解决方案**：
xap_Frame.h 改为 `#include "xap_Dlg_MessageBox.h"`。

---

## 五、测试环境

```
软件: abiword-plugin-paint 3.0.8（AbiWord Paint 插件模块）
构建系统: autotools（minimal configure.ac，仅构建 paint 插件）
编译器: clang/clang++ 15（OHOS SDK, aarch64-linux-ohos）
Conan: 2.29.1（OHOS 适配版）, profile: ci/conan/profiles/ohos-aarch64
构建命令: autoreconf -fi && ./configure --prefix=$DEFAULT_PREFIX && make -j1 && make check -j1
产物: libabiword-plugin-paint.so → lib/abiword-3.0/plugins/
```

---

*报告生成时间: 2026-08-13*
