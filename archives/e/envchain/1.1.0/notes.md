# envchain 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built
- RPATH: $ORIGIN/../lib（相对路径）

## 编译步骤

1. 使用 git clone 从 GitHub 获取源码（网络下载 tar.gz 超时）
2. 打包源码为 tar.gz 格式
3. 使用 ohc-run.py init-build 初始化编译环境
4. 安装依赖预编译包：readline 8.2, libsecret 0.21.7, glib 2.88.0, pcre2 10.40
5. 修正依赖包 pkg-config 路径问题
6. 修改 Makefile：
   - 添加 PKG_CONFIG_PATH export（解决 pkg-config 子 shell 问题）
   - 添加 PREFIX 变量支持标准 DESTDIR 模式
   - 修复 install 目标路径 $(DESTDIR)/./bin → $(DESTDIR)$(PREFIX)/bin
7. 运行 make 编译（设置 RPATH）：
   `make LDFLAGS="-Wl,-rpath,$PREFIX/lib -Wl,--enable-new-dtags"`
8. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging 目录
9. 使用 patchelf 设置相对 RPATH：
   `patchelf --set-rpath '$ORIGIN/../lib' envchain`
10. 进行 ELF 签名
11. 手动制作预编译包（包含 envchain 二进制）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 git clone 替代 |
| 2 | readline.pc 路径错误 | 预编译包 prefix 指向临时目录 | 修正 .pc 文件中的 prefix |
| 3 | pkg-config 找不到 libffi | .pc 文件命名为 ffi.pc 而非 libffi.pc | 创建 libffi.pc 别名 |
| 4 | pkg-config 子 shell 找不到包 | Makefile export 未生效 | 在 Makefile 中添加 export PKG_CONFIG_PATH |
| 5 | 预编译包仅空目录 | Makefile install 使用 $(DESTDIR)/./bin 非标准路径 | 改为 $(DESTDIR)$(PREFIX)/bin |
| 6 | 缺少 RPATH | 编译时未指定 LDFLAGS | 编译时设置 LDFLAGS + patchelf 修正相对路径 |
| 7 | envchain 动态链接问题 | 依赖库未设置 RPATH | 设置 $ORIGIN/../lib 相对 RPATH |

## 源码修改

**0001-Makefile.patch**: 修复 Makefile 的三个问题：

```diff
# 1. 添加 PKG_CONFIG_PATH 环境变量（解决 pkg-config 子 shell 问题）
+PKG_CONFIG_PATH = /storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig
+export PKG_CONFIG_PATH

# 2. 添加 PREFIX 变量支持标准 DESTDIR 模式
-DESTDIR ?= /usr
+PREFIX ?= /storage/Users/currentUser/usr/local
+DESTDIR ?=

# 3. 修复 install 目标路径
-	install -d $(DESTDIR)/./bin
-	install -m755 ./envchain $(DESTDIR)/./bin/envchain
+	install -d $(DESTDIR)$(PREFIX)/bin
+	install -m755 ./envchain $(DESTDIR)$(PREFIX)/bin/envchain
```

## RPATH 设置方法

1. **编译时设置**：`make LDFLAGS="-Wl,-rpath,$PREFIX/lib -Wl,--enable-new-dtags"`
2. **安装后修正**：`patchelf --set-rpath '$ORIGIN/../lib' envchain`
3. **验证**：`readelf -d envchain | grep RUNPATH`

最终 RPATH: `$ORIGIN/../lib`（相对路径，确保预编译包可移植）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| readline | 8.2 | cmd-pkgs 预编译包 |
| libsecret | 0.21.7 | cmd-pkgs 预编译包 |
| glib | 2.88.0 | cmd-pkgs 预编译包 |
| pcre2 | 10.40 | cmd-pkgs 预编译包 |

## 验证结果

```bash
# 本地运行验证
~/usr/local/bin/envchain
# 输出: envchain version 1.1.0

# staging 目录验证
$TEST_PREFIX/$DEFAULT_PREFIX/bin/envchain
# 输出: envchain version 1.1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| envchain-1.1.0-ohos-aarch64.tar.gz | 30KB | 预编译包（包含 envchain 二进制） |
| 0001-Makefile.patch | 1KB | Makefile 补丁 |

## 预编译包内容

```
bin/
bin/envchain    # 22KB（已 strip）
lib/            # 空目录（用于依赖库安装）
```

## 注意事项

1. envchain 不支持 --version/--help 选项，无参数运行显示版本和用法
2. envchain 需要动态链接 libsecret-1.so.0 等库，用户安装后需安装依赖库
3. envchain 需要 D-Bus Secret Service (GNOME keyring/KeePassXC) 作为后端
4. RPATH 使用 $ORIGIN/../lib 相对路径，确保预编译包可移植
5. 纯 Makefile 项目需手动处理 PREFIX/DESTDIR 支持

---

**编译结束**: 2026-06-05 19:42
**最终状态**: built
---

**编译结束**: 2026-06-05 19:43
**最终状态**: built
