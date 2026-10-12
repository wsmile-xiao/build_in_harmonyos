# 消费者图中依赖二进制被跳过（Skipped binaries / package_folder=None）

- **草稿 ID**: DRAFT-SCHROOT-1613-CONAN-DEP-BINARY-SKIP
- **条目文件**: `knowledge/drafts/schroot-1.6.13-conan-dep-binary-skip.kv`
- **来源事件**: schroot 1.6.13 `conan create` 的 test_package 阶段（2026-10-01）
- **严重程度**: 🔴 blocking

## 1. 现象

配方本体 `conan create` 编译成功、`package()` 也正常，但 **test_package（消费者）**
编译时报找不到 boost / libuuid 的头或库：

```
conan create 日志：
  Skipped binaries
      boost/1.84.0, libuuid/2.40.4, zlib/1.3.1, cppunit/1.15.1
```

而配方里明明 `requires("boost/1.84.0")`、`requires("libuuid/2.40.4")`。

## 2. 根因

conan 2 在解析**消费者图**时会裁剪掉"仅用于构建期"的依赖二进制：日志出现
`Skipped binaries ...`，这些包在图中 `package_folder is None`。后果：

- 配方 `generate()` 里能定位到的 Boost 路径（构建图完整），在消费者图里取不到；
- CMakeDeps 生成的 `<pkg>-data.cmake` 中 `INCLUDE_DIRS` / `LIBS` 为空
  （schroot 实测：`schroot_INCLUDE_DIRS_RELEASE`、`schroot_LIBS_RELEASE` 均为空，
  `FIND_DEPENDENCY_NAMES` 只剩 `linux-pam gettext`）；
- 消费者编译立刻失败。

仅靠配方侧声明 `transitive_headers` / `transitive_libs` **不足以**修复——单独加转发关系后本包
仍报缺头（实证）。

## 3. 诊断方法（先用探针定性）

写一个最小消费者配方，只 require 被测包并打印图中各依赖的 `package_folder`：

```python
# tmp/probe-consumer/conanfile.py
def generate(self):
    for dep in self.dependencies.values():
        self.output.info(f"{dep.ref}: pf={dep.package_folder}")
```

输出形如（schroot 实测）：

```
boost/1.84.0: pf=None          <-- 被跳过
libuuid/2.40.4: pf=None        <-- 被跳过
linux-pam/1.7.2: pf=/…        <-- 正常
BOOSTNODES=6  SKIP=Skipped binaries boost/1.84.0, libuuid/2.40.4, zlib/1.3.1, cppunit/1.15.1
```

`pf=None` 的包就是消费者缺失的头/库来源。

## 4. 解决方案

在 **test_package/conanfile.py**（以及任何真实消费者）中**显式声明**这些依赖：

```python
def requirements(self):
    self.requires("boost/1.84.0")
    self.requires("libuuid/2.40.4")
```

声明后 schroot 的 `HASREQ=1`，重新 `conan create`：

```
ALL CHECKS PASSED     ERROR=0
```

即消费者图重新包含完整二进制。若上游（非测试）使用者同样需要这些头/库，应在配方
`package_info()` / `requirements()` 中把关系上升为使用关系，而不仅是"构建期需要"。

## 5. 禁止做法

- ❌ 在探针/测试里 `if pf is None: pass` 跳过校验——问题只是推迟到下游/CI 才爆。
- ❌ 只在 test_package 里塞绝对路径的缓存目录当 workaround 后就不再管配方——
  真实下游仍缺依赖（假绿）。

## 6. 验证

```bash
conan create .                       # 期望：无 "Skipped binaries" 或消费者仍能编译/链接
grep -n "Skipped binaries" create.log
```
