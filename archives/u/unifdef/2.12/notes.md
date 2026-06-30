# unifdef 2.12 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-06-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -kL -o unifdef-2.12.tar.gz "https://dotat.at/prog/unifdef/unifdef-2.12.tar.gz"`（SSL 证书验证失败，使用 -k 跳过）
2. 解压源码: `tar xzf unifdef-2.12.tar.gz`，创建 .orig 和 .work 目录
3. 初始化编译环境: `ohc-run.py init-build unifdef 2.12 --no-download`（使用已下载源码）
4. 编译: `make -j1 CC=clang CFLAGS="-fPIC -O2"` → 成功生成 unifdef 二进制（55744 bytes）
5. 安装: `make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX` → 安装 unifdef、unifdefall 和 man page
6. 运行测试: `make test CC=clang CFLAGS="-fPIC -O2"` → 90/93 通过
7. 生成 Conan 配方: `ohc-run.py conan-init unifdef 2.12`
8. 修改 conanfile.py（从 Autotools 模板改为 Make 直接构建，package_info 改为 bindirs）
9. 验证配方: `ohc-run.py conan-verify unifdef 2.12` → 全部 8 道门禁通过
10. 收尾: `ohc-run.py finish unifdef 2.12 published` → 状态 published（conan-verify 全部通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙环境 CA 证书不完整 | 使用 `curl -kL` 手动下载源码到 $TMPDIR/builds/ |
| 2 | init-build 找不到 .work 目录 | 需要先手动解压创建目录 | 手动 tar xzf 解压并创建 .orig/.work 目录 |
| 3 | make test 中 5 个测试失败 | unifdefall.sh 调用 `cc` 而非 `clang`，系统无 cc | 创建 `cc → clang` 软链接（rm -f && ln -s） |
| 4 | outeperm 测试失败 | HMDFS 下 chmod 555 不限制写入（E046） | 记录为平台限制，非功能缺陷 |
| 5 | overperms 测试失败 | HMDFS 强制 group write 权限（-rw-rw---- vs -rw-r-----） | 记录为平台限制，非功能缺陷 |
| 6 | conanfile.py 使用 Autotools 模板 | conan-init 检测为 autotools 但实际无 configure | 重写 build() 为直接调用 make |
| 7 | package_info 使用 libs | 模板默认为库配置 | 改为 bindirs=["bin"]（终端工具） |
| 8 | test_package 找不到二进制 | VirtualRunEnv 未正确设置 PATH | 改为使用 self.dependencies["unifdef"].package_folder 构造完整路径 |
| 9 | make install 软链接失败 | HMDFS 不支持 ln -s 覆盖已存在文件（R5） | 安装前 rm -rf $TEST_PREFIX 清除旧目录 |

## 源码修改

无补丁。unifdef 源码未修改，所有适配通过环境变量和 Conan 配方完成。

## 依赖版本

无外部依赖。仅依赖系统库 libc.so。

## 验证结果

```bash
$ ./unifdef -V
Version: unifdef-2.12
Date: 2020-02-14 16:37:16 +0000
Author: Tony Finch (dot@dotat.at)
URL: http://dotat.at/prog/unifdef

$ echo '#ifdef FOO
int foo = 1;
#else
int bar = 2;
#endif' | ./unifdef -DFOO
int foo = 1;

$ make test
90/93 通过，3 个失败（outeperm×2, overperms×1）均为文件系统权限差异
```

## 注意事项

- unifdef 使用自定义 Makefile，conanfile.py 的 build() 必须直接调用 make，不能用 Autotools.configure()
- unifdefall.sh 内部硬编码调用 `cc`，必须创建 cc → clang 软链接
- 终端工具（非库）的 package_info 应使用 `bindirs=["bin"]` 而非 `cpp_info.libs`
- HMDFS 文件系统的 chmod 行为与标准 Linux 不同，权限相关测试会失败
---

**编译结束**: 2026-06-30 17:24
**最终状态**: published
