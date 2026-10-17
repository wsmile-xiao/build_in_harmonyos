# xapian-bindings 1.4.26 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, python3 绑定)
- 编译日期: 2026-08-10
- 编译器: clang 15.0.4 (SDK, -stdlib=libc++)
- Python: 3.12.9
- 状态: built

## 编译步骤
1. 源码: `https://oligarchy.co.uk/xapian/1.4.26/xapian-bindings-1.4.26.tar.xz`
   (SHA256: 550873573ee0401199f835fef51ddf89ca7bc26f7b8d1bdcca59da643fb3ca81)
2. configure --with-python3（E011 umask 修复 + 完整工具链 AR/RANLIB/NM/LD）
3. 链接修复: `-lstdc++` → `-lc++`，PYTHON3_LIBS 追加 `-L{lib} -lpython3.12`
4. make -C python3 _xapian.la + 生成 xapian/__init__.py（跳过 import 验证目标，
   CI 的 HNP python 在 conan build 目录加载 .so 报 Permission denied）
5. 绑定安装到 python site-packages（package: lib/python3.12/site-packages/xapian）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure config.status Permission denied | HMDFS umask 077 (E011) | 补丁 0001-configure.patch: umask 077→022 |
| 2 | configure C compiler 测试失败 | CI 干净 PATH 无 ar/ranlib/nm/ld | 显式传 AR/RANLIB/NM/LD（参照 xapian-core 配方） |
| 3 | 链接 `-lstdc++` not found | OHOS SDK 无 libstdc++ | Makefile `-lstdc++` → `-lc++` + `-stdlib=libc++` |
| 4 | 链接 `-lpython3.12` 找不到 | CI HNP python 的 sysconfig LIBDIR 指向不存在路径 | 从 include 推导 prefix/lib 多候选探测 |
| 5 | make 内 import _xapian Permission denied | CI HNP python 沙箱限制 conan build 目录 | 跳过 pycache 验证目标，安装到 site-packages 后由 test_package 验证；上游 make check 不在 build() 内执行（CI 报 ImportError: Permission denied） |
| 6 | HMDFS 覆盖 site-packages 文件 Operation not permitted | HMDFS 覆盖限制 | 安装前 rm -rf 目标目录 |
| 7 | conan G2 报 python-require 不能依赖 shared-library | conan 类型规则 | 移除 package_type="python-require"（参照 internetarchive） |
| 8 | configure 原生 conftest 执行失败 | OHOS CI 沙箱(SELinux/AppSpawn)无法执行用户编译的 ELF（E009/E064） | configure 的 cross-compiling 探测改为直接判定 no（build==host==aarch64-unknown-linux-ohos 原生构建，非交叉编译；禁止 --host 伪造） |
| 9 | test_package import xapian 报 Error loading shared library ... Permission denied | CI musl 动态链接器加载 .so 校验 .codesign 签名（E077/P-SIGN-001），未签名 .so 被拒 | package() 中对 _xapian.so 执行 llvm-objcopy 移除旧签名 + binary-sign-tool -selfSign 1（参照 ffmpeg _sign_binaries，CI 已验证） |

## 源码修改
- 补丁 0001-configure.patch: configure 中 umask 077 → 022（E011, HMDFS 权限）

## 依赖版本
- xapian-core 1.4.26 (制品仓 ohpcd 已发布, 提供头文件 + libxapian.so + xapian-config)

## 验证结果
```bash
# conan create (干净构建, 依赖 xapian-core/1.4.26)
conan create ... # PASS (G1-G4 + L2/L4/L5)
# test_package 功能测试
import xapian → PASS (1.4.26)
内存数据库创建 + 文档添加 + 检索 → PASS
```

## 注意事项
- xapian-bindings 是 Python 绑定库（`import xapian`），供 xapers 等 Python 工具依赖
- tarball 预生成 xapian_wrap.cc，构建无需 swig
- 产物: _xapian.cpython-312-aarch64-linux-ohos.so + xapian/ 纯 Python 包
- package_info 设置 PYTHONPATH（runenv）供消费者 `import xapian`

## 结束
编译结束，状态: closed（built）
---

**编译结束**: 2026-08-12 11:14
**最终状态**: built
