# VERIFY_RESULT — luaposix 36.3

## 1. 编译状态

**成功** ✅

`conan create` 从本地源码完整编译，产出 28 个 `.so` 制品 + 9 个 `.lua` 文件，exit code = 0。

---

## 2. 本地编译证据

完整日志：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.luaposix-verify.log`（375 行）

### 2.1 luke 构建命令（日志第 205 行）

```
luaposix/36.3.1: RUN: /storage/Users/currentUser/.conan2/p/b/lua267ffce303b29/p/bin/lua
  /storage/Users/currentUser/.conan2/p/b/luapob14a97eb5187f/b/build-aux/luke
  PREFIX=/storage/Users/currentUser/.conan2/p/b/luapob14a97eb5187f/b
  LUA_INCDIR=/storage/Users/currentUser/.conan2/p/b/lua267ffce303b29/p/include
  LUA_LIBDIR=/storage/Users/currentUser/.conan2/p/b/lua267ffce303b29/p/lib
  CC=/data/service/hnp/bin/clang
```

luke 调用 build tool_requires 的 `lua` 解释器（`lua267ffce303b29/p/bin/lua`），使用 host lua 的 include/lib 目录，编译器为 `clang`。

### 2.2 clang 编译 .c 源文件 → .so 制品（日志第 208–235 行）

共 28 条 clang 编译命令，逐个将 `ext/posix/*.c` 编译为 `unix/posix/*.so`。示例：

**第 208 行**（socket.so）：
```
/data/service/hnp/bin/clang -O2 -shared -fPIC -D_FORTIFY_SOURCE=2 -D_POSIX_C_SOURCE=200809L
  -D_XOPEN_SOURCE=700 -DPACKAGE='"luaposix"' -DHAVE_LINUX_NETLINK_H=0 -DVERSION='"100"'
  -DNDEBUG -DHAVE_NET_IF_H -DHAVE_LINUX_IF_PACKET_H -Iext/include
  -I/storage/Users/currentUser/.conan2/p/b/lua267ffce303b29/p/include
  ext/posix/sys/socket.c -o unix/posix/sys/socket.so
```

**第 212 行**（signal.so — test_package 验证的 C 制品）：
```
/data/service/hnp/bin/clang -O2 -shared -fPIC -DPACKAGE='"luaposix"' -DVERSION='"100"'
  -D_FORTIFY_SOURCE=2 -DNDEBUG -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700
  -Iext/include -I/storage/Users/currentUser/.conan2/p/b/lua267ffce303b29/p/include
  ext/posix/signal.c -o unix/posix/signal.so
```

**第 235 行**（最后一条，sys/times.so）：
```
/data/service/hnp/bin/clang -O2 -shared -fPIC -DPACKAGE='"luaposix"' -DVERSION='"100"'
  -D_FORTIFY_SOURCE=2 -DNDEBUG -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700
  -Iext/include -I/storage/Users/currentUser/.conan2/p/b/lua267ffce303b29/p/include
  ext/posix/sys/times.c -o unix/posix/sys/times.so
```

### 2.3 .so 制品产出确认（日志第 243 行）

```
luaposix/36.3.1: package(): Packaged 28 '.so' files
luaposix/36.3.1: package(): Packaged 9 '.lua' files
```

### 2.4 依赖 lua/5.5.0 本地编译（日志第 109–160 行）

lua/5.5.0 也从源码本地构建（`Building from source`），使用 `/data/service/hnp/bin/clang` 编译全部 .c 文件（第 123–159 行），证明 `--build=lua` 生效。

### 2.5 无远程下载确认

日志中 `Download`、`ohpcd`、`Retrieving package ... from remote` 出现次数：**0**

`-nr` 标志确保完全本地构建，未从任何远程仓库拉取预编译包。

---

## 3. conan create 结果

| 项目 | 值 |
|------|-----|
| 命令 | `conan create archives/l/luaposix/36.3.1 -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 --build=luaposix --build=lua --build=missing -nr` |
| exit code | **0**（日志第 293 行） |
| Full package reference | `luaposix/36.3.1#f6012b40845eecad0878b817a9023192:5798f3b2ee7052037569a303fbbfd75875cb4022#528414d7f7d8765b1f2071d5f490f22b`（日志第 247 行） |
| Recipe revision | `f6012b40845eecad0878b817a9023192` |
| Package ID | `5798f3b2ee7052037569a303fbbfd75875cb4022` |
| Package revision | `528414d7f7d8765b1f2071d5f490f22b` |
| Package folder | `/storage/Users/currentUser/.conan2/p/b/luapob14a97eb5187f/p` |

### conan 缓存验证

```
$ conan list luaposix
Local Cache
  luaposix
    luaposix/36.3.1

$ conan list "luaposix/*:*"
Local Cache
  luaposix
    luaposix/36.3.1
      revisions
        f6012b40845eecad0878b817a9023192 (2026-08-10 04:03:51 UTC)
          packages
            5798f3b2ee7052037569a303fbbfd75875cb4022
              info
                settings: arch=armv8, build_type=Release, compiler=clang,
                          compiler.cppstd=17, compiler.libcxx=libc++,
                          compiler.version=15, os=OHOS, os.version=6.0
                requires: lua/5.5.0#b376f0ee48d296b7b83296c6b4c4b529
```

---

## 4. test_package 执行结果

### 4.1 conan create 内嵌 test_package（日志第 288–290 行）

```
=== luaposix test ===
posix module + posix.signal C artifact loaded from package
luaposix OK
```

### 4.2 独立 conan test 验证（日志第 370–375 行）

```
luaposix/36.3.1 (test package): RUN: export PATH=.../lua267ffce303b29/p/bin:$PATH && /data/service/hnp/bin/bash test.sh
=== luaposix test ===
posix module + posix.signal C artifact loaded from package
luaposix OK

conan test exit code: 0
```

### 4.3 测试通过率

| 指标 | 值 |
|------|-----|
| 测试用例总数 | 1（test.sh） |
| 通过用例数 | 1 |
| 通过率 | **100%** |
| assertion_count | 2（LUA_CPATH 非空 + posix/posix.signal 加载成功） |
| conan test exit code | 0 |

---

## 5. 失败分析

**无失败**。编译、链接、测试全通过。

---

## 6. 是否需要打回重做

**否**。编译成功 ✅，本地编译（非远程下载）✅，测试通过率 100% ✅，缓存已建立 ✅。

---

## 7. 验证流程摘要

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. 清理缓存 | `conan remove luaposix -c` | Removed（日志第 2 行） |
| 2. 本地构建 | `conan create ... --build=luaposix --build=lua --build=missing -nr` | exit 0，28 .so + 9 .lua |
| 3. 测试验证 | `conan test ... --build=missing` | exit 0，luaposix OK |
| 4. 缓存确认 | `conan list luaposix` | luaposix/36.3.1 in Local Cache |

完整日志路径：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.luaposix-verify.log`
