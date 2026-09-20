# Draft: shared conan dep breaks configure sanity conftest (native build)

**ID**: libtheora-1.2.0-alpha1-shared-dep-conftest-runtime-path
**Severity**: 3 | **Category**: build-system|conan|linking|ohos
**Status**: DRAFT

## 症状

conan create（ohos-aarch64 原生 profile）在 configure 最初阶段失败：

```
checking whether the C compiler works... configure: error: cannot run C compiled programs.
# config.log:
configure:3377: ./a.out
Error loading shared library libogg.so.0: (needed by ./a.out)
```

## 根因

AutotoolsDeps 把共享依赖的 `-L<conan cache>/lib -l<dep>` 放进全局 LDFLAGS/LIBS，
configure 的第一个 sanity conftest 就链接了共享依赖；conanbuild 环境不含依赖
libdir 的 LD_LIBRARY_PATH，动态加载器找不到 libogg.so.0。表面上像工具链坏了，
实际是运行期库路径问题。

## 修复

build() 开头把所有直接依赖的 package libdir 注入 os.environ["LD_LIBRARY_PATH"]
（conanbuild 环境是前置叠加，注入值存活）。代码见
`archives/l/libtheora/1.2.0-alpha1/conanfile.py::_inject_runtime_lib_path`。

不要用 --host/--build 交叉模式绕过（参见姊妹草稿
libtheora-1.2.0-alpha1-cross-mode-assumed-optional-deps）。

## 验证

libtheora 1.2.0-alpha1：注入前 conan create 死在 "cannot run C compiled
programs"；注入后 configure + make + 9/9 上游测试 + test_package 编解码往返全绿。

*2026-09-18 — libtheora 1.2.0-alpha1 适配过程中实测*
