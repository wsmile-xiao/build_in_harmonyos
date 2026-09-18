# DRAFT-scrypt-1.3.2-autotoolsdeps-ac-search-libs — Conan autotools 配方缺 AutotoolsDeps 致 AC_SEARCH_LIBS 找不到依赖

## 现象 (What happened)

对 scrypt 1.3.2 生成 Conan 配方后运行 `ohc-run.py conan-verify`：

1. **G2 conan create 失败**，configure 输出：
   ```
   checking for library containing AES_encrypt... no
   configure: error: function AES_ENCRYPT not found
   ```
2. 配方 `requirements()` 已声明 `self.requires("openssl/3.5.8.1")`，openssl
   依赖也已在 cache 中（`conan install` 验证成功），但 configure 的
   `AC_SEARCH_LIBS(AES_encrypt, crypto)` 链接探测仍找不到 libcrypto。

## 根因 (Root cause)

Conan 2 中 `AutotoolsToolchain` 与 `AutotoolsDeps` 职责分离：

- `AutotoolsToolchain(self).generate()` 只生成编译器/工具链环境
  （CC/CXX/CFLAGS/CXXFLAGS/LDFLAGS 骨架、--disable-shared 等 configure 参数），
  **不注入依赖**；
- `AutotoolsDeps(self).generate()` 才把依赖闭包的 cpp_info（include 目录 →
  CPPFLAGS，lib 目录 → LDFLAGS，库名 → LIBS）写入 configure 探测环境。

生成的 `conanautotoolstoolchain.sh` 中 CPPFLAGS 只有 `-DNDEBUG`、LDFLAGS 为空
——openssl 的 include/lib 目录从未进入 configure，`AC_SEARCH_LIBS` 的
`-lcrypto` 链接探测自然失败。scrypt 的 configure 对 openssl 是**硬性要求**
（`AC_SEARCH_LIBS(AES_encrypt, crypto)` + `openssl/aes.h` 头文件检查），
缺注入即在此处中止。

## 解法 (Fix)

`generate()` 中在 `AutotoolsToolchain(self).generate()` 之后**成对**调用
`AutotoolsDeps(self).generate()`：

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.configure_args.append("--disable-shared")
    tc.generate()
    AutotoolsDeps(self).generate()   # 依赖注入（必需，否则 AC_SEARCH_LIBS 失败）
```

## 验证 (Verification)

```bash
python3 scripts/ohc-run.py conan-verify scrypt 1.3.2
# → G1 PASS / G2 PASS (conan create 干净构建成功) / G3-G5 PASS
grep -n 'checking for library containing AES_encrypt' reports/conan-create.log
# → ... none required（依赖已注入）
grep -n 'scrypt consumer test PASSED' reports/conan-create.log   # test_package 消费者通过
```

## 适用边界 (Scope)

所有 autotools 构建系统且依赖经 `AC_SEARCH_LIBS`/`AC_CHECK_LIB`/
`AC_CHECK_HEADER` 硬性探测的 Conan 2.x 配方。判别：conan create 的 configure
阶段报 `function XXX not found` / `checking for library containing ... no`，
而配方 requirements() 已声明对应依赖。

## 与既有知识的关系

- similar_to: **E467**（相反方向：AutotoolsDeps 已注入但依赖闭包加载失败、
  configure rc=77）；**E351-draft**（pkg-config 接线，PKG_CHECK_MODULES 方向）
- 本条目特有：只生成 Toolchain、漏 AutotoolsDeps 时
  `AC_SEARCH_LIBS → function ... not found` 探针失败签名与成对修复。