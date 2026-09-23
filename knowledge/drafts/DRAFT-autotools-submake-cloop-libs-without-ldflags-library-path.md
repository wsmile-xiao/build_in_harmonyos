# DRAFT-autotools-submake-cloop-libs-without-ldflags-library-path

## 可复现症状与稳定错误签名

主工程 configure 已成功找到全部依赖（`checking for tomcrypt.h... yes`、`checking for
sha1_init in -ltomcrypt... yes` 等），`make` 早期在链接内嵌子工程 `extern/cloop` 时失败：

```
/data/service/hnp/bin/clang++ <cloop objects> -o .../gen/Release/cloop/release/bin/cloop \
    -ltomcrypt -lgmp -ltommath -lz -licui18n -licuuc -licudata -lpthread -ldl -lm
ld.lld: error: unable to find library -ltomcrypt
ld.lld: error: unable to find library -lgmp
ld.lld: error: unable to find library -ltommath
ld.lld: error: unable to find library -licui18n
ld.lld: error: unable to find library -licuuc
ld.lld: error: unable to find library -licudata
clang-15: error: linker command failed with exit code 1
make[4]: *** [Makefile:97: .../cloop] Error 1
make[3]: *** [Makefile:200: external] Error 2
```

稳定签名：**一次出现多条 `unable to find library -l<dep>`，且这些 `-l` 都来自 `$(LIBS)`**，
同时主工程 configure 的依赖探测全部 `yes`（说明依赖确实存在、只是链接期搜不到）。

## 根因与最小复现

- 上游子工程链接规则（Firebird `extern/cloop/Makefile:97`）：

  ```make
  $(LD) $^ -o $@ $(LIBS)          # 只有 $(LIBS)，没有 $(LDFLAGS)/-L
  ```

- 上游在系统库目录（`/usr/lib` 等）安装依赖，所以 `-l` 天然可解析，问题从不暴露。
- Conan 场景：依赖位于各自 package 前缀（`~/.conan2/p/<hash>/p/lib`）。主工程用的注入
  （`AutotoolsDeps` 生成的 `CPPFLAGS/LDFLAGS/LIBS`）只作用于主 make；子 make 只继承 `LIBS`
  与 `LIBRARY_PATH`，不继承 `-L`。因此链接期全部 `-l` 落空。
- 最小复现：`cd extern/cloop && make`（无 `LIBRARY_PATH`）→ 上述 6 条错误；
  `LIBRARY_PATH=<dep lib dirs> make` → 成功。

## 修复（不改上游 makefile）

在 conanfile 的 `generate()` 中把宿主依赖的 libdirs 导出为 `LIBRARY_PATH`：

```python
env = tc.environment()
libdirs = []
for dep in self.dependencies.host.values():
    for libdir in dep.cpp_info.aggregated_components().libdirs:
        if libdir and libdir not in libdirs:
            libdirs.append(libdir)
if libdirs:
    env.append("LIBRARY_PATH", os.pathsep.join(libdirs))
tc.generate(env=env)
```

`LIBRARY_PATH` 被 clang/gcc 驱动用于 `-l` 链接期搜索，等价于对所有子 make 隐式补 `-L`，
且不需要给上游打补丁（保持源码零改动、补丁集最小）。

## 适用范围

- 上游 build 阶段调用内嵌子工程/第三方 vendored 库的 `make`（Firebird `extern/cloop`、
  `extern/libtomcrypt`、`extern/decNumber` 等均属此列）；
- 这些子工程的链接规则只转发 `$(LIBS)`（或干脆硬编码 `-l`）；
- 依赖来自包管理器前缀（Conan/vcpkg）而非系统库目录。

## 证据

- 未设置 `LIBRARY_PATH`：`make -j4` 在 cloop 链接处失败（6 条 `unable to find library`），
  日志中 cloop 的编译阶段全部成功，仅链接失败。
- 设置 `LIBRARY_PATH`（值 = `LDFLAGS` 中的 `-L` 目录）后：同一 `make -j4` 全程 rc=0，
  `gen/Release/firebird/lib/libfbclient.so.5.0.4` 生成（`DT_NEEDED` 仅 `libc.so`，
  说明依赖被静态吸收），后续 `conan create` / W3 本地 CI 全绿。
