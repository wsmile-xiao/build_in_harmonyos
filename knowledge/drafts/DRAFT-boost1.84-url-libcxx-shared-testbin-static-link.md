# DRAFT（草稿）：OHOS C++ 测试二进制运行期加载 libc++_shared.so 失败（rc=127）——静态打入或自省注入两流派

> 本文为 `DRAFT-boost1.84-url-libcxx-shared-testbin-static-link.kv` 的人类可读配套文档（kv/md 成对，W5 规范）。
> 来源：boost1.84-url 1.84.0 适配（PR #8436），关联 issue #2698。

## 错误特征

```
Error loading shared library libc++_shared.so
Error relocating ./test_unit: __cxa_pure_virtual: symbol not found
Error relocating ./test_unit: _ZSt9terminatev: symbol not found
Error relocating ./test_unit: _ZNSt4__n1::cout ... symbol not found
# conan create / ctest 阶段：所有 C++ 测试二进制退出码 rc=127，无编译/链接报错
```

## 根因

OHOS clang（`-stdlib=libc++`）默认把 C++ 可执行文件动态链接 `libc++_shared.so`（写入 DT_NEEDED），但该库
不在系统默认加载路径、也不在 conan profile buildenv 的 LD_LIBRARY_PATH 前置路径（`<SDK>/llvm/lib`）内——
实际位于 `<SDK>/llvm/lib/aarch64-linux-ohos/` 子目录。musl 加载器按 NEEDED 找不到库时以 rc=127 退出，
且 libc++ 运行时符号（`__cxa_pure_virtual` / `_ZSt9terminatev` / `_ZNSt4__n1::cout` 等）全部 undefined
而逐符号打印 `Error relocating`。

**关键迷惑性**：编译链接期零报错、纯运行期失败。boost/1.84.0 底稿当年在设备 shell 环境侥幸通过（继承了
SDK 环境变量），干净 conan build 环境即暴露。

**影响面**：所有在 OHOS 上编译并运行 C++ 测试二进制的配方——conan create build() 内手动编译运行上游
C++ 测试（绕过 b2/ctest）、test_package 的 CMake 测试产物、任何 `clang -stdlib=libc++` 产物需在无 SDK
环境注入的 shell 中直接运行的场景。

## 解法

**流派 A（推荐，测试二进制首选）**：`-static-libstdc++` 静态打入
- conanfile 手动编译测试：cxxflags 追加 `-static-libstdc++`
- test_package（CMake）：`target_link_options(<tgt> PRIVATE -static-libstdc++)`
- 效果：NEEDED 仅剩 libc.so，产物在任意干净环境（CI worker、裸 shell）直接运行，无需环境变量配合；
  测试二进制是短命产物，静态打入无体积包袱

```cmake
# test_package/CMakeLists.txt
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_xxx PRIVATE -static-libstdc++)
endif()
```

**流派 B（必须动态链接时）**：`clang++ -print-file-name=libc++_shared.so` 自省定位 SDK 内 libc++ 真实
目录（clang 找到输出绝对路径；找不到原样回显），注入运行子进程的 LD_LIBRARY_PATH。运行命令须用双引号
包裹 `LD_LIBRARY_PATH="{}:${LD_LIBRARY_PATH:-}"`——既处理含空格路径，又保证变量为空时展开为空串不
残留空段（boost1.84-date_time PR #8455 实证）。先例：boost/1.85.0 元包、boost1.84-thread、
boost1.84-date_time、boost/1.90.0.2.1 同款修复。

```python
# conanfile.py 内运行测试子进程
probe = subprocess.run(f"{cxx} -print-file-name=libc++_shared.so", shell=True, capture_output=True)
if probe.stdout.strip().startswith("/"):
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.path.dirname(probe.stdout.strip()) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    subprocess.run([exe], env=env)
```

## 禁止策略（第二层坑）

```cmake
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")   # ❌ 永不触发
```

OHOS 适配版 conan 把 `settings.os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，单判 `"OHOS"` 的分支
永不触发，修复静默失效——boost1.84-url test_package 第二轮踩坑实证（条件块内 `-static-libstdc++` 从不
生效，ctest 阶段仍 rc=127）。判定一律 `MATCHES "HarmonyOS|OHOS"` 或双判。

## 验证命令

```bash
readelf -d <test_bin> | grep NEEDED && LC_ALL=C <test_bin> && echo rc=$?
# 修复前：NEEDED 含 libc++_shared.so 且运行 rc=127
# 流派 A 修复后：NEEDED 仅 libc.so 且 rc=0
```

## 跨库复现实证（五个独立任务）

1. **boost/1.85.0 元包**（2026-09-02）：4 库上游测试 rc=127 → 流派 B（print-file-name 自省注入）
2. **boost1.84-thread**（2026-09-05）：同坑，引用 1.85.0 先例 → 流派 B
3. **boost1.84-serialization**（2026-09-05）：同坑 → 流派 A（-static-libstdc++）
4. **boost1.84-url**（2026-09-05，本条来源，PR #8436）：19 上游测试 + test_package 全 rc=127，两轮修复
   （conanfile + CMakeLists，含 CMAKE_SYSTEM_NAME 第二层坑）→ 流派 A
5. **boost1.84-date_time**（2026-09-05，PR #8455）：同坑 → 流派 B'（print-file-name 定位 +
   `LD_LIBRARY_PATH="{}:${LD_LIBRARY_PATH:-}"` 双引号包裹运行命令 + OHOS 签名，同 boost/1.90.0.2.1 先例）

五个独立任务均各自独立发现并修复，无一入库固化——本条为首个沉淀。

## 查重对照

draft-review TOP1 相似度 0.51（E316 OpenBLAS SONAME，根因不同）；E212（hmmac 安全标签 Permission
denied，库在但被策略拒）、E019/E120/E132/E191/E298/E452 及 date_time 引号细节（知识库无条目，已纳入
fallback）均未覆盖此运行期场景。

## 原则引用

- R33（禁止裸 shell 环境变量——本条修复用链接旗标而非环境变量）
- R34（测试必须真实运行）
