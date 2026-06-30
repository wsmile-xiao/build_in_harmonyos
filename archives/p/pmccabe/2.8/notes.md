# pmccabe 2.8 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure 脚本)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: published (conan-verify 8/8 PASS)

## 编译步骤

```bash
source .build-context-pmccabe-2.8
cd $BUILD_SRC_DIR

# 无 configure 脚本，直接 make
make CC=clang CXX=clang++

# 安装到测试目录（覆盖 INSTALL 避免 -o root -g root）
make install DESTDIR=$TEST_PREFIX INSTALL="install"

# 运行测试套件
make test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitLab SSL 证书验证失败 | 鸿蒙环境缺少 CA 证书 | curl -kL 手动下载到 $TMPDIR，init-build 用 file:// URL |
| 2 | /tmp 只读 | 鸿蒙 E002 陷阱 | 使用 $TMPDIR (/storage/Users/currentUser/tmp) |
| 3 | make -j2 mkfifo 失败 | HMDFS 不支持 FIFO | 改用单线程 make（去掉 -j2） |
| 4 | INSTALL=-o root -g root 失败 | 鸿蒙无 root 用户 | make install 时覆盖 INSTALL="install" |
| 5 | conan create make 找不到 Makefile | basic_layout 使用 build-release 子目录 | build() 使用 cwd=self.source_folder |
| 6 | test_package pmccabe 不在 PATH | VirtualRunEnv 未正确设置 PATH | test_package 使用完整路径 self.dependencies[...].package_folder |
| 7 | pmccabe 无参数时挂起 | 读 stdin 等待输入 | 测试时传文件参数 |

## 源码修改

无源码修改。pmccabe 源码可直接编译，无需补丁。

## 依赖版本

无外部依赖。pmccabe 是纯 C 工具，仅依赖系统 libc。

## 验证结果

### make test
```
cd tests && ./testsuite
EXIT_CODE=0
```
所有 28 个测试用例通过。

### conan-verify (8 道门禁)
```
G0: ✅ PASS (预构建风险评估)
G1: ✅ PASS (配方完整性)
G2: ✅ PASS (conan create 干净构建)
G3: ✅ PASS (静态链接验证 R26)
G4: ✅ PASS (产物完整性检查)
L2: ✅ PASS (smoke test)
L4: ✅ PASS (静态安全扫描 checksec)
L5: ✅ PASS (产物基线对比)
```

### 二进制检查
```
pmccabe: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
readelf -d: NEEDED libc.so (仅系统库，无非系统动态依赖)
```

## 产物路径

| 类型 | 路径 |
|------|------|
| bin/ | pmccabe, codechanges, decomment, vifn |
| share/man/man1/ | pmccabe.1, codechanges.1, decomment.1, vifn.1 |

## 注意事项

- pmccabe 构建系统标注为 autotools 但实际是纯 Makefile（无 configure 脚本）
- conanfile.py 使用 self.run("make ...", cwd=self.source_folder) 而非 Autotools 工具
- package() 方法将 Makefile 安装的 usr/bin/ 重整为 Conan 标准的 bin/ 布局
- test_package 使用 VirtualRunEnv + 完整路径方式测试二进制
---

**编译结束**: 2026-06-29 19:24
**最终状态**: published
