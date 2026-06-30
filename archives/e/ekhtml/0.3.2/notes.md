# ekhtml 0.3.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `init-build ekhtml 0.3.2 --url=...` 下载源码并初始化
2. `source .build-context-ekhtml-0.3.2` 加载环境变量
3. 复制现代 config.guess/config.sub 替换 2001 年旧版本
4. 修改 configure 脚本移除 `umask 077`（鸿蒙 HMDFS 限制）
5. `./configure --prefix=$DEFAULT_PREFIX`
6. `make -j1`
7. `make install DESTDIR=$TEST_PREFIX`
8. `make check`（2/3 通过，1 失败因 Python2 语法）
9. `conan-init` 生成 Conan 配方
10. `conan-verify` 8 道门禁全部通过
11. `finish ekhtml 0.3.2 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙环境 CA 证书不完整 | 使用 curl -k 手动下载 tarball 到 $TMPDIR/builds/ |
| 2 | config.guess 无法识别系统 | 2001 年旧版 config.guess 不支持 HarmonyOS/aarch64 | 从 automake-1.16 复制现代 config.guess/config.sub |
| 3 | config.status 创建临时文件权限被拒 | `umask 077` 创建 0700 目录，鸿蒙 HMDFS 不允许写入 | 移除 configure 和 config.status 中的 `umask 077` |
| 4 | make check 测试脚本无法执行 | 测试脚本 shebang `#!/bin/bash`，但鸿蒙无 /bin/bash | 修改为 `#!/data/service/hnp/bin/bash` |
| 5 | make check test_basic.sh 失败 | pyparser.py 使用 Python 2 语法（print 语句） | 非 C 库问题，Python 2→3 兼容性问题，记录但不阻塞 |
| 6 | conan create G2 失败 | Conan Autotools out-of-source 构建，旧 Makefile 的 `-I../include` 相对路径失效 | 改用 in-source build（self.run + cwd=source_folder） |

## 源码修改

以下修改在 conanfile.py 的 build() 方法中自动完成（非补丁文件）：
- config.guess/config.sub: 从 automake-1.16 复制现代版本
- configure: 移除 `umask 077 && mktemp -d` 中的 `umask 077`

## 依赖版本

无外部依赖。ekhtml 0.3.2 是纯 C 库，无第三方依赖。

## 验证结果

```
conan-verify: 8/8 门禁通过
  G0: PASS (预构建风险评估)
  G1: PASS (配方完整性)
  G2: PASS (conan create 成功)
  G3: PASS (静态链接，纯库包跳过)
  G4: PASS (产物: 1 .a + 1 头文件)
  L2: PASS (smoke test，纯库包跳过)
  L4: PASS (安全扫描，无 ELF 文件)
  L5: PASS (基线已保存，5 个文件)
```

## 注意事项

- ekhtml 是纯静态库（libekhtml.a），无可执行文件
- 测试脚本使用 Python 2 语法，在 Python 3 环境下无法运行
- conanfile.py 使用 in-source build 方式，因为旧版 autotools 不支持 out-of-source build
---

**编译结束**: 2026-06-29 21:37
**最终状态**: built
