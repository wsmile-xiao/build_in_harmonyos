# E545 — CMake install 重写 ELF 使 `.codesign` 失效，制品包内二进制 exec 报 Operation not permitted

> **Status**: DRAFT（待主编审核） | **贡献者**: 82B8 | **更新**: 2026-09-29
> **来源**: qdiskinfo 0.4-git20251119 HarmonyOS PC 适配（`archives/q/qdiskinfo/0.4-git20251119`，Qt6/C++17，`package_type=application`）

## 错误特征

`conan create` 全部通过（含 test_package），但执行**制品包**里的可执行文件失败：

```text
$ <pkg_folder>/bin/QDiskInfo --version
timeout: exec <pkg_folder>/bin/QDiskInfo: Operation not permitted
rc=126
```

对照现象（判别要点）：

```text
# 同一份代码、同一编译器，构建树里的二进制可以直接跑
$ ls build/Release/QDiskInfo && ./build/Release/QDiskInfo --version
QDiskInfo 0.4          # rc=0

# install / package 之后的那一份不能跑
$ <pkg_folder>/bin/QDiskInfo --version
Operation not permitted  # rc=126
```

`conan create` 的构建日志里可见 CMake 的 install 阶段在改写 RPATH：

```text
-- Set non-toolchain portion of runtime path of ".../bin/QDiskInfo" to ""
```

## 触发条件

- 构建系统: cmake（Conan 的 `CMake` 助手 + `cmake.install()`）
- 阶段: installation / `package()`
- 平台: OHOS（aarch64-linux-ohos，内核强制 ELF 自签名校验）
- 关键共性: 构建期 ELF 由 OHOS 工具链链接时写入 `.codesign`，而 **install 阶段会为了去掉构建期绝对 RPATH 重写该 ELF**（`CMAKE_INSTALL_RPATH` / `CMAKE_INSTALL_RPATH_USE_LINK_PATH` 引起的 "Set non-toolchain portion of runtime path ... to ''"）
- 与 E077 的关系: E077 描述"任何 ELF 改写都使签名失效"的四步补救流程；本条目补充 **CMake install 是常见的隐式改写来源**，且症状出现在"构建树可跑、制品不可跑"的对照上，极易被误判为权限位/文件系统问题

## 根因分析

OHOS 内核只加载 `.codesign` 段有效的 ELF（见 E077）。任何字节级改写——包括 `patchelf`、`strip`、`objcopy`，**以及 CMake install 阶段为去除构建 RPATH 而做的二进制重写**——都会使链接器写入的签名与内容不再匹配，内核随即拒绝 `exec`，返回 `EPERM`（`Operation not permitted`，shell 记为 rc=126）。

`readelf -S` / `ls -l` 检查时文件看起来完全正常（属主、权限位、段表都在），因此该问题不会被常规权限检查发现；唯一的判别信号是"同一二进制在构建树可执行、install 之后不可执行"。

`conan create` 的 G2 与 W3 之所以也能通过，是因为 `test_package()` 用 `env="conanrun"` 运行，且它执行的是自己构建（并在 build() 中签名）的测试二进制；**制品包内的 ELF 是否可执行，需要单独验证**。

## 解决方案

### 推荐方案

把自签名作为 `package()` 的**最后一步**，在 `cmake.install()` 以及任何其它 ELF 改写之后执行（四步顺序不可变，见 E077）：

1. `llvm-objcopy --remove-section .codesign <file>` —— 必须先移除旧签名（否则 `binary-sign-tool` 报 `section already exists`）
2. `binary-sign-tool sign -inFile <file> -outFile <file> -selfSign 1`
3. `chmod <file> +x`（签名工具会把权限位归零）
4. 只对 `os == "OHOS"` 生效；遍历 `self.package_folder` 时跳过符号链接与非 ELF（先读文件头 `\x7fELF` 判断）

工具路径：`llvm-objcopy` 与 `binary-sign-tool` 均在 `/data/service/hnp/bin/`（可用 `shutil.which` 探测，失败时给出明确报错而不是静默跳过）。

参考实现（qdiskinfo 0.4-git20251119）：

```python
def package(self):
    cmake = CMake(self)
    cmake.install()
    self._sign_ohos_elfs()      # ★ 必须是最后一步
```

### 禁止做法

- ❌ 只给制品加执行位（`chmod +x`）——签名失效与权限位无关，问题依旧
- ❌ 在 `build()` 里签名、`install()` 之后再不改动——install 会覆盖/重写该文件
- ❌ 把构建期绝对 RPATH 烘进制品以图绕开 install 改写（发布机绝对路径属红线，且不改变签名失效问题）
- ❌ 跳过 `--remove-section .codesign` 直接重签

## 验证

```bash
# 1) 构建并打包
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 2) 直接执行制品包内的二进制（不要经 conanrun，L2 冒烟即等价场景）
PKG=$(conan cache path qdiskinfo/0.4-git20251119)
"$PKG/bin/QDiskInfo" --version; echo "rc=$?"     # 期望: QDiskInfo 0.4 / rc=0

# 3) 确认签名段在场
readelf -S "$PKG/bin/QDiskInfo" | grep -i codesign
```

## 关联条目

- 前置/相关: E077（OHOS ELF 自签名与四步补救流程，含 `section already exists`、权限归零等细节）
- 相关: E472（test_package 内测试二进制同样需要签名）
- 易混: E374（签名工具可用性/能力校验）
