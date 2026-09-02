# DRAFT-conan-shared-pkgconfig-requires-drop — Conan 2 shared-library 包的 STATIC 依赖被 Skipped，PkgConfigDeps 静默丢弃 .pc Requires 链

> **Contributor**: Awstme | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: blocking (2) | **Category**: conan / pkg-config / packaging / static-linking
> **Audience**: 所有 package_type="shared-library" 且公共头传递 include 静态依赖头文件、消费链走 pkg-config 流的 Conan 配方

## 触发（trigger）

- libaudclient/3.5-rc2（audacious D-Bus 客户端库）OHOS 适配：`package_type="shared-library"`，
  公共头 `audctrl.h`/`dbus.h` 经 `dbus/dbus-glib.h` 传递 include `<glib.h>`。
- OHOS 依赖制品 static-only（glib/dbus/dbus-glib/pcre2/zlib 全静态，E236 la-free 内嵌进 .so）。
- test_package 消费者以 pkg-config 流编译：`$(pkg-config --cflags --libs audclient)`。

## 症状（symptom）

```
test_audclient.c:24:10: fatal error: 'glib.h' file not found
```

同一 conan create 日志上方可见：

```
Skipped binaries: glib/2.88.0, pcre2/10.45, zlib/1.3.1
```

修复前生成的 `audclient.pc`：`Requires: dbus-glib-1 dbus`——glib 链静默消失，
pkg-config 与 Conan 全程无告警。

## 机制（root cause）

从设备 conan 2.29.1 源码逐层定位（requires.py / dependencies.py / pkgconfigdeps.py）：

1. `conan/internal/model/requires.py` `transform_downstream`（约 289 行）：
   `package_type="shared-library"` 的包消费 STATIC 依赖时，向下游传播的
   require 被强制 `headers=False, libs=False`。static-library 中间人只丢
   headers、保留 libs（姊妹草稿 DRAFT-conan-staticlib-transitive-headers 的
   at-spi2-core 情形）；shared-library 消费者情形两者全丢。
2. `conan/internal/model/dependencies.py` `get_transitive_requires` 按
   `{"skip": False}` 过滤 → 下游图里 glib/pcre2/zlib 节点被标记 Skipped binaries。
3. `conan/tools/gnu/pkgconfigdeps.py` `_get_component_requirement_names` 对
   skip 依赖的组件引用直接剔除 → `audclient.pc` 的 `Requires:` 链截断。
4. 独立叠加坑：`cpp_info.requires` 组件引用只允许指向 recipe 的**直接**依赖，
   引用传递依赖组件在 `package_info()` 阶段直接抛
   "There are '(cpp_info.components).requires' that includes package 'glib::',
   but such package is not a a direct requirement of the recipe"。

## 修复（rec）

```python
# conanfile.py requirements()：
self.requires("dbus-glib/0.114")
self.requires("dbus/1.14.10")
self.requires("glib/2.88.0", transitive_headers=True)   # glib 提为直接依赖

# package_info()：cpp_info.requires 组件引用仅列直接依赖
self.cpp_info.requires = [
    "dbus-glib::dbus-glib", "dbus::dbus", "glib::glib-2.0",
    "glib::gobject-2.0", "glib::gthread-2.0", "glib::gmodule-2.0",
    "glib::gio-2.0",
]
```

`transitive_headers=True` 使 transform_downstream 按
`headers = require.headers and require.transitive_headers` 保留头传播；
libs 保持 False **恰是正确语义**——静态链已内嵌 .so，下游不应再链接 glib
归档（重复符号/双 GType 运行时风险，E257 同类）。expat/pcre2/zlib 无消费者
可见头文件，保持传递依赖不提级。

## 查重（dedup）

- 姊妹草稿 DRAFT-conan-staticlib-transitive-headers（拟 E321，at-spi2-core）：
  static-library 中间人 × CMakeDeps INCLUDE_DIRS 为空，修复同为
  transitive_headers=True。本条目增量：**shared-library 消费者**情形
  （headers+libs 双降级 → 节点整体 Skipped）、**PkgConfigDeps 生成 .pc 的
  Requires 链静默截断**（不同生成器表面、无 INCLUDE_DIRS 症状）、以及
  cpp_info.requires 直接依赖校验这条独立报错链。两草稿互补，建议交叉引用。
- E216（CMakeDeps 不传播组件 INTERFACE_INCLUDE_DIRECTORIES，配方元数据层，
  GLOB 兜底）：不同层（图传播语义 vs 生成器元数据），同症状家族，交叉引用。
- E283（package_type 推导）：只覆盖 library/shared option 推导，未覆盖
  transform_downstream 下游降级。
- 全库 grep `Skipped binaries`/`Requires:`/`PkgConfigDeps`：无命中。

## 证据（evidence）

- 设备实跑（HarmonyOS PC aarch64，conan 2.29.1）：run7（直接依赖组件引用修复后）
  暴露 cpp_info.requires 直接依赖校验异常 → run8（glib 提直接依赖）暴露
  'glib.h' file not found + 日志 "Skipped binaries" → run9（transitive_headers=True）
  EXIT=0，test_audclient `checks=82 failures=0`，
  `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...}`。
- 配方提交链：1e68583d99（unset CONFIG_SHELL）→ 4991d32002（直接依赖组件引用）
  → 774eb98884（transitive_headers）；文档 9fb29e3185 设备复验。
- PR：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7671
  （CI #36622 全门禁通过，对应 HEAD 9fb29e3185）。

## 关系

- similar_to: E216、E221、E283、E307、DRAFT-conan-staticlib-transitive-headers
