# DRAFT: conan build 目录复用 × CMakeCache 无 FORCE 的调参验证假象

*来源 PR: !9046（flatbuffers/25.12.19）· 2026-09-09*

## 错误特征

修改 conanfile.py 的 `tc.variables["X"]` 后重跑 `conan create`，构建行为仍按旧值执行；
读构建目录发现：

```
CMakeCache.txt:  X:STRING=ON        <- 上一轮的旧值
flags.make:      CXX_DEFINES = -DX=1
```

## 根因分析

- conan 对相同 package_id（settings/options/deps 不变，recipe 内容不参与）复用同一
  `p/b/<pkgid>/b` build 文件夹；
- CMakeToolchain 将变量以 `set(X "<值>" CACHE ...)` 写入，**CACHE 变量已存在且无 FORCE
  时不覆盖**；
- 于是"显式 OFF"被上一轮"ON"的 CACHE 残留压制，验证轮次之间互相污染。

实证：flatbuffers 第 3 轮显式 `FLATBUFFERS_LOCALE_INDEPENDENT=OFF`，第 2 轮的
`ON` 仍在 CMakeCache（`STRING=ON`），flattests 仍按 =1 编译 → hex-float 用例假失败；
清空 `p/b/flatb*` 后同配方第 4 轮全绿。

## 推荐方案

1. 凡改 `CMakeToolchain.variables`/`cache_variables` 的每一轮 create 前：
   `rm -rf $CONAN_HOME/p/b/<pkgid 前缀>*`；
2. 核验读实际产物：`CMakeCache.txt` 与 `CMakeFiles/<target>.dir/flags.make`；
3. 同包多轮失败会产生多个平级包目录（如 `flatb8ca*`/`flatbdd*`），用 `ls -dt` 取最新。

## 反例与边界

- 未改 CMake 变量、只改 package()/package_info() 的轮次无需清缓存；
- 与 E311（source isolation）、E522（libtool 任务级缓存遮蔽）机制不同源，不互相替代。
