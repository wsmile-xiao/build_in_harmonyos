# E580 — 原生 OHOS 构建下 `IF(CMAKE_CROSSCOMPILING)` 守卫失效，缓存绝对路径泄漏进 `.pc`

- **状态**: 草稿 (draft)
- **严重度**: 3 🔴 blocking（制品不可重定位）
- **分类**: cmake, build-system, portability, ohos, conan
- **来源**: libosmosdr 0.1.8.effcaa7 适配（AtomCode）

## 现象

打包后安装出来的 `libosmosdr.pc` 的 `Cflags` 行包含构建机私有目录的绝对路径：

```ini
prefix=/storage/Users/currentUser/builds/libosmosdr-manual/stage
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: OsmoSDR Library
Description: C Utility Library
Version:
Cflags: -I${includedir}/ -I/storage/Users/currentUser/.conan2/p/libus04e54d4f229a5/p/include/libusb-1.0
Libs: -L${libdir} -losmosdr -lusb-1.0
```

`-I/storage/.../.conan2/p/libus04e54d4f229a5/...` 是 **libusb 依赖在构建机的 conan 缓存路径**，
它随制品一起发布；下游在另一台机器上 `pkg-config --cflags libosmosdr` 会拿到不存在的目录。

## 根因

上游 `CMakeLists.txt`（libosmosdr 为 119–123 行）把"剥离构建机路径"的逻辑包在
`IF(CMAKE_CROSSCOMPILING)` 里，**意图是仅在交叉编译时清理**。

但 ohpcd 的 OHOS 构建是 **原生构建（native build）**：conan 的 `ohos-aarch64` profile 不下发
`CMAKE_SYSTEM_NAME` / `CMAKE_SYSROOT`，CMake 判定 `CMAKE_CROSSCOMPILING` 为 **假**，
于是该守卫分支**永不执行**，剥离逻辑被整个跳过。

> 结论：**上游的意图是对的，守卫条件在本平台不成立**——因此不应改上游源码，
> 而应在 `package()` 阶段补齐清理。

## 判别方法

```bash
# 打包后检查制品内 .pc / *Config.cmake 是否残留构建机路径
grep -rE "/storage/|/\.conan2/p/|/usr/local" <package_folder>/lib/pkgconfig/*.pc
grep -E "^(prefix|Cflags|includedir)" <package_folder>/lib/pkgconfig/*.pc
```

命中 `/storage/`、`/.conan2/p/`、`/usr/local` 即视为泄漏。

## 推荐方案（priority 1）

在 `conanfile.py` 的 `package()` 中做**后处理**，不动上游源码：

```python
def package(self):
    cmake = CMake(self)
    cmake.install()
    self._drop_build_host_paths_from_pkgconfig()

def _drop_build_host_paths_from_pkgconfig(self):
    """上游以 IF(CMAKE_CROSSCOMPILING) 守卫路径剥离，原生 OHOS 构建下守卫恒假，
    故在此复核并删除 .pc 中指向构建机的绝对 -I 项。"""
    pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
    if not os.path.isdir(pc_dir):
        return
    for name in os.listdir(pc_dir):
        if not name.endswith(".pc"):
            continue
        path = os.path.join(pc_dir, name)
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        cleaned = []
        for line in lines:
            if line.startswith("Cflags:"):
                flags = [t for t in line.split() if t != "Cflags:"]
                flags = [t for t in flags if not self._is_build_host_path(t)]
                line = "Cflags: " + " ".join(flags) + "\n" \
                    if flags else "Cflags:\n"
            cleaned.append(line)
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(cleaned)
```

判断"是否构建机路径"时，应排除可重定位的 `${includedir}` / `${prefix}` 形式，
只删除以 `/` 开头的绝对路径。

参考实现：`archives/l/libosmosdr/0.1.8.effcaa7/conanfile.py`

## 回退方案（priority 2）

若 `.pc` 之外还存在 `*Config.cmake` 泄漏，则打补丁把剥离逻辑改为**无条件执行**
（去掉 `IF(CMAKE_CROSSCOMPILING)` 包裹），并在 PR 中说明理由。
注意：`patches/` 中默认禁止平台宏（R8），此方案不含平台宏，属合规修改。

## 禁止策略

| 模式 | 原因 | 后果 |
|------|------|------|
| 用 `CFLAGS=-I/storage/...` 之类 shell 变量注入构建机路径 | 路径随制品固化 | 制品不可重定位，下游编译失败 |

## 通用性

凡上游满足以下两条者，在原生 OHOS 构建下都会踩中：

1. 在 `.pc` / `*Config.cmake` 中写入构建期路径；
2. 用 `IF(CMAKE_CROSSCOMPILING)`（或等价的"仅交叉编译时"条件）守卫其剥离。

因此**打包后必查制品内的绝对路径**，这一点也应纳入 W4 审计 / L5 检查。
