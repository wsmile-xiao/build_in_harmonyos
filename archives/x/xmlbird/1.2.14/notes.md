# xmlbird 1.2.14 适配笔记

## 编译环境
- 构建系统: custom（python configure + build.py，Vala 项目）
- 编译日期: 2026-08-31
- 编译器: clang 15.0.4（gcc 不可用）
- Vala 编译器: valac 0.56.18（cmd-pkgs 预编译包）
- 状态: published

## 编译步骤

```bash
# 1. 安装预编译工具链（用户级）
#    vala 0.56.18 / glib 2.88.0 / pcre2 10.40 / libffi 3.4.6
#    注意：libffi 3.4.4 预编译包为损坏 stub（10KB, bad shoff），需用 3.4.6 并修正软链接

# 2. configure（指定 clang 编译器）
python3 configure --prefix=/storage/Users/currentUser/usr/local -c clang

# 3. 编译
python3 build.py
# 产物: build/bin/libxmlbird.so.1 + build/xmlbird/xmlbird.h + build/xmlbird.vapi

# 4. 测试（上游 doit test 对应 test.py）
python3 test.py   # 运行 minimal + benchmark
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gcc 不可用（平台仅 clang） | OHOS 无 gcc | configure -c clang；scripts/tests.py 硬编码 gcc → 改用 scripts/config.py 的 CC 变量 |
| 2 | libffi pkg-config 缺失 / libvala 加载失败 | glib-2.0 依赖 libffi，cmd-pkgs libffi 3.4.4 为损坏 stub（bad shoff） | 安装 libffi 3.4.6，修复 libffi.so.8 软链接指向完整库 |
| 3 | valac 编译测试 C 代码后崩溃（Signal 5 SIGTRAP） | valac 0.56.18 在本平台生成 C 代码后进程退出时触发 glib 崩溃（平台运行时问题，非 xmlbird 代码问题）；C 代码已完整生成 | 直接复用已生成的 C 文件 + clang 编译链接测试 |
| 4 | 测试程序运行时退出时 SIGTRAP (rc=133) | glib/gobject 运行时退出清理路径在 OHOS 上触发 SIGTRAP（最小 GObject 程序亦复现）；功能断言在崩溃前全部通过 | 记录为平台限制；测试功能逻辑已验证通过（Xml encoding passed 等） |
| 5 | `-lxmlbird` 在编译时被当作未用参数警告 | 编译命令中 -l 放在 -c 阶段 | 仅警告，不影响产物 |

## 源码修改

- scripts/tests.py: `gcc` → `scripts.config.CC`（clang），使测试编译使用平台编译器

## 依赖版本

- vala/0.56.18（编译期，tool_requires 或预编译包）
- glib/2.84.0.1（运行时 + 编译期，conan 配方 requirements 声明；本地探索阶段曾用 cmd-pkgs glib 2.88.0 预编译包，两者 API 兼容，配方以 glib/2.84.0.1 为准并与 manifest.yaml 一致）
- libffi/3.4.4（glib 传递依赖，conan 制品仓版本）
- pcre2/10.45（glib 传递依赖，conan 制品仓版本）

## 验证结果

```bash
# 库产物
build/bin/libxmlbird.so.1  → 2443712 bytes
build/xmlbird/xmlbird.h    → C 头文件
build/xmlbird.vapi         → Vala API

# 测试功能验证（minimal/benchmark 均编译链接成功）
./build/bin/minimal → "Xml encoding passed: '<>& == '<>&"（后续测试断言均通过）
# 注：进程退出时 glib 运行时 SIGTRAP（平台限制，见问题 4）

# 消费者功能验证（test_package，conan create 内执行）
ALL xmlbird tests passed  # 11 项断言：parse/validate/tag/attr/encode-decode
```

## 注意事项

1. 本项目为 Vala 语言（编译目标 C），lang-preflight 工具因 `_EXT_LANG` 无 `.vala` 扩展名映射而误判为 mixed/python——属工具缺陷，Vala→C 属 c/cpp 兼容族，可正常适配。
2. 测试退出 SIGTRAP 为 glib/gobject 运行时在 OHOS 的平台限制，不影响库本身功能与下游使用。

### SIGTRAP 平台限制最小复现（R40 证据）

用最小 GObject 程序独立复现，证明与 xmlbird 代码无关：

```c
/* gobjtest.c — 最小 GObject 程序 */
#include <glib-object.h>
#include <stdio.h>
int main(void) {
    GObject *o = g_object_new(G_TYPE_OBJECT, NULL);
    printf("gobject new ok\n");
    g_object_unref(o);
    printf("gobject unref ok\n");
    return 0;
}
```

编译运行：
```bash
clang gobjtest.c $(pkg-config --cflags --libs glib-2.0 gobject-2.0) -o gobjtest
./gobjtest
# 输出 "gobject new ok" / "gobject unref ok" 后：
# Trace/breakpoint trap (core dumped)   ← 进程退出清理路径 SIGTRAP (rc=133)
```

结论：glib/gobject 进程退出清理在 OHOS 触发 SIGTRAP（Signal 5），与业务代码无关。xmlbird 测试程序改用 `_exit()` 显式结束进程绕过该路径，功能断言 11/11 通过。
---

**编译结束**: 2026-09-01 00:30
**最终状态**: published
