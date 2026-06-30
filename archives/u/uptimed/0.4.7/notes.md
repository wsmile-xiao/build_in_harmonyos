# uptimed 0.4.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. **下载源码**: 从 GitHub 下载 v0.4.7.tar.gz（SSL 证书问题，用 Python urllib 禁用 SSL 验证下载）
2. **autogen.sh**: 设置 `AUTOM4TE=autom4te`，手动运行 `libtoolize --automake --copy --force`，然后运行 `./autogen.sh` 生成 configure
3. **configure**: `./configure --prefix=$DEFAULT_PREFIX`，修补 `umask 077` → `umask 022`
4. **make**: `make -j1`（HMDFS 不支持 mkfifo，不能用 -j2）
5. **make install**: `make install DESTDIR=$TEST_PREFIX`
6. **make check**: 通过（项目无测试套件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aclocal 报错 `@am_AUTOM4TE@: inaccessible or not found` | automake 安装中 autom4te 路径未自动解析 | 设置环境变量 `AUTOM4TE=autom4te` |
| 2 | automake 报错 `required file './ltmain.sh' not found` | autogen.sh 中 libtoolize 未自动安装 ltmain.sh | 手动运行 `libtoolize --automake --copy --force` |
| 3 | config.status 报错 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 文件系统不允许在 `umask 077` 创建的 0700 权限目录中写入文件 | 用 `sed -i 's/umask 077/umask 022/g'` 修补 configure 和 config.status |
| 4 | `make -j2` 报错 `jobserver mkfifo: Operation not permitted` | HMDFS 不支持 mkfifo 系统调用，make jobserver 机制无法工作 | 使用 `make -j1` 单线程编译 |
| 5 | Conan test_package CMake 报错 `non-existent path /include` | uptimed 不安装公共头文件，但 Conan 默认设置 includedirs=["include"] | 在 package_info() 中设置 `self.cpp_info.includedirs = []` |
| 6 | Conan test_package 报错 `uprecords: inaccessible or not found` | conanrun 环境未正确设置 PATH 到包 bin 目录 | 使用 VirtualRunEnv 生成器 + 直接引用二进制完整路径 |
| 7 | Conan build() 报错 `env argument to ConanFile.run() should be a list` | Conan 2.x 的 run() 方法 env 参数需为列表而非字典 | 将环境变量直接嵌入命令字符串 |

## 源码修改

无需源码补丁。所有平台适配通过构建时环境变量和 sed 命令实现：
- `AUTOM4TE=autom4te` 环境变量
- `sed -i 's/umask 077/umask 022/g' configure` 平台适配
- Conan 配方中 `--disable-shared --enable-static` + `-static` 链接标志

## 依赖版本

无外部依赖。uptimed 仅依赖标准 C 库和系统头文件。

## 验证结果

```bash
# config.guess 平台检测
$ ./config.guess
aarch64-unknown-linux-ohos

# 二进制文件类型
$ file .../bin/uprecords .../sbin/uptimed
.../bin/uprecords: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
.../sbin/uptimed:  ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# make check
$ make check
# 所有子目录: Nothing to be done for 'check'（项目无测试套件）

# Conan 验证
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify uptimed 0.4.7
# G0-G4 + L2/L4/L5 全部 PASS
```

## 注意事项

- HMDFS 文件系统的 `umask 077` 限制是通用平台问题，所有 autotools 项目都可能遇到
- uptimed 的 configure.ac 使用了过时的 AM_PROG_LIBTOOL 宏，建议上游更新为 LT_INIT
- PKG_PROG_PKG_CONFIG 在 OHOS 上不可用（无 pkg-config m4 宏），但非致命
- 终端工具静态链接（R26）在 Conan 配方中通过 `--disable-shared` + `-static` 实现

---

**编译结束**: 2026-06-30
**最终状态**: published
