# atk 2.38.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build atk 2.38.0 --url=file://$HOME/tmp/atk-2.38.0.tar.xz
   ```

2. 设置环境变量：
   ```bash
   export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
   ```

3. 配置：
   ```bash
   meson setup builddir --prefix=$DEFAULT_PREFIX --wrap-mode=nofallback -Dintrospection=false
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

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson fallback 尝试克隆 glib | glib 2.88.0 已通过 pkg-config 可用，不需要 fallback | 使用 --wrap-mode=nofallback |
| 2 | g-ir-scanner 执行权限问题 | _giscanner.cpython-312.so 未签名 | 禁用 introspection（-Dintrospection=false） |
| 3 | 链接失败：undefined symbol: g_libintl_* | libintl.h 将 gettext 函数宏定义为 g_libintl_*，但 libintl.so 只导出 libintl_* 符号 | 创建 intl-wrapper.c wrapper 库，将 g_libintl_* 映射到 libintl_* |
| 4 | Meson 检测 HarmonyOS 为 harmonyos，导致 Linux 特有链接器选项缺失 | meson.build 中有 host_machine.system() == 'linux' 判断 | 修改为 host_machine.system() in ['linux', 'harmonyos']（E090） |

## 源码修改

### meson.build
- 修改第 74 行：`if host_machine.system() == 'linux'` → `if host_machine.system() in ['linux', 'harmonyos']`
- 目的：启用 Linux 特有的链接器选项（-Wl,-Bsymbolic, -Wl,-z,relro, -Wl,-z,now）

### intl-wrapper.c（新增）
- 创建 wrapper 库，将 g_libintl_* 符号映射到 libintl_* 符号
- 解决 glib 静态库引用 g_libintl_* 符号但 libintl.so 只导出 libintl_* 符号的问题

### build.ninja（临时修改）
- 添加 libintl-wrapper.a 到链接命令

## 依赖版本

- glib-2.0: 2.88.0
- gobject-2.0: 2.88.0
- libintl: 已安装
- pcre2-8: 已安装
- ffi: 已安装

## 验证结果

```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
pkg-config --modversion atk
# 2.38.0

pkg-config --libs atk
# -L/storage/Users/currentUser/usr/local/lib -latk-1.0 -lgobject-2.0 -lintl -lglib-2.0 ...

pkg-config --cflags atk
# -DG_INTL_STATIC_COMPILATION -pthread -I/storage/Users/currentUser/usr/local/include/atk-1.0 ...

# 测试结果
ninja -C builddir test
# Ok: 5, Fail: 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libatk-1.0.so.0.23809.1 | ~4.6MB | 动态库 |
| atk.pc | pkg-config 文件 |
| 头文件 | atk-1.0/atk/*.h |

## 注意事项

1. **必须设置 PKG_CONFIG_PATH**：编译和链接时都需要设置 PKG_CONFIG_PATH 包含 ~/usr/local/lib/pkgconfig
2. **必须禁用 introspection**：g-ir-scanner 的 Python 扩展需要 ELF 签名才能在 HarmonyOS 上执行
3. **intl-wrapper 问题**：glib 静态库与 libintl 符号不匹配，需要 wrapper 库
4. **E090 知识点**：Meson 构建系统需要修改 host_machine.system() == 'linux' 为 in ['linux', 'harmonyos']

## 知识提取记录

1. **E090**：Meson host_system == 'linux' 不匹配 HarmonyOS
   - 适用软件：所有使用 meson 且有 Linux 特有判断的项目
   - 已在 meson.build 中应用

2. **g_libintl_* 符号问题**：
   - libintl.h 将 gettext 函数宏定义为 g_libintl_*
   - 但 libintl.so 只导出 libintl_* 符号
   - 解决方案：创建 wrapper 库或修改 libintl.h
   - 需要记录到知识图谱
---

**编译结束**: 2026-05-26 21:13
**最终状态**: built
