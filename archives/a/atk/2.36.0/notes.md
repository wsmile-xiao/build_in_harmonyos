# atk 2.36.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build atk 2.36.0
   ```

2. 设置环境变量：
   ```bash
   export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
   ```

3. 配置：
   ```bash
   meson setup builddir --prefix=$DEFAULT_PREFIX --wrap-mode=nofallback -Dintrospection=disabled -Ddocs=false
   ```

4. 编译：
   ```bash
   ninja -C builddir -j2
   ```

5. 安装到 staging：
   ```bash
   meson install -C builddir --destdir=$TEST_PREFIX
   ```

6. 测试：
   ```bash
   ninja -C builddir test
   # 5/5 tests passed
   ```

7. 安装到本地：
   ```bash
   meson install -C builddir
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | meson fallback 尝试克隆 glib | glib 2.84.0 已通过 Conan 可用，不需要 fallback | 使用 --wrap-mode=nofallback | — |
| 2 | g-ir-scanner 执行权限问题 | _giscanner.cpython-312.so 未签名 | 禁用 introspection（-Dintrospection=disabled） | — |
| 3 | 链接失败：undefined symbol: g_libintl_* | libintl.h 将 gettext 函数宏定义为 g_libintl_*，但 libintl.so 只导出 libintl_* 符号 | 创建 intl-wrapper.c wrapper 库，将 g_libintl_* 映射到 libintl_* | E107 |
| 4 | Meson 检测 HarmonyOS 为 harmonyos，导致 Linux 特有链接器选项缺失 | meson.build 中有 host_machine.system() == 'linux' 判断 | 修改为 host_machine.system() in ['linux', 'harmonyos'] | E090 |

## 源码修改

### intl-wrapper.c（source() 内联写入，非补丁）
- source() 方法通过 shutil 直接内联写入 atk/intl-wrapper.c（避 Conan 2.x patch 路径解析炸）
- 实现：g_libintl_* wrapper 用 (char*) 转型返回 msgid/m 避 g_strdup 内存泄漏（aireview P2 已修）
- 解决 glib 静态库引用 g_libintl_* 符号但 libintl.so 只导出 libintl_* 的问题（E107）

### patches/0002-atk-meson.build.patch
- 将 intl-wrapper.c 加入 atk 源文件列表

### patches/0003-meson.build.patch
- 修改第 67 行：`if host_machine.system() == 'linux'` → `if host_machine.system() in ['linux', 'harmonyos']`
- 目的：启用 Linux 特有的链接器选项（-Wl,-Bsymbolic, -Wl,-z,relro, -Wl,-z,now）（E090）

## 依赖版本

- glib-2.0: 2.84.0（Conan 制品仓已发布）
- gobject-2.0: 2.84.0（随 glib）
- libintl: 已安装（系统库）
- pcre2-8: 已安装
- ffi: 已安装

## 验证结果

```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
pkg-config --modversion atk
# 2.36.0

pkg-config --libs atk
# -L/storage/Users/currentUser/usr/local/lib -latk-1.0 -lgobject-2.0 -lintl -lglib-2.0 ...

# 测试结果
ninja -C builddir test
# Ok: 5, Fail: 0
```

## 知识引用

1. **E090**：Meson host_system == 'linux' 不匹配 HarmonyOS
   - 适用软件：所有使用 meson 且有 Linux 特有判断的项目
   - 已在 patches/0003-meson.build.patch 中应用
   - 知识图谱正式条目：knowledge/graph/E090.kv + knowledge/doc/E090.md

2. **E107**：g_libintl_* 符号缺失
   - libintl.h 将 gettext 函数宏定义为 g_libintl_*，但 libintl.so 只导出 libintl_* 符号
   - 解决方案：创建 wrapper 库（intl-wrapper.c）将 g_libintl_* 映射到 libintl_*
   - 适用软件：所有静态链接 glib 且依赖 libintl 的项目
   - 知识图谱正式条目：knowledge/doc/E107.md + knowledge/graph/E142.kv

## 路径 B 申报

本库适配过程中引用了 3 个通用问题知识条目（均为已入知识图谱的正式条目）：
- E090：Meson 平台检测通用问题
- E107：glib 静态库与 libintl 符号不匹配通用问题
- E318-draft-A7F3：GNOME 生态 glib 静态链接 + meson host_machine 综合条目草稿（intl-wrapper + Meson host_system 检测 + pkg-config 传播，本 PR 新增，正式编号由主编合并时分配）
  - 知识图谱草稿：knowledge/drafts/E318-draft-A7F3.md + knowledge/drafts/E318-draft-A7F3.kv（正式条目由主编合并 PR 时自动生成）

---

**编译结束**: 2026-07-30
**最终状态**: built
