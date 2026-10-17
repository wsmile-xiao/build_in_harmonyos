# libnop 0.0-git20211103.35e800d 适配笔记

## 编译环境
- 构建系统: **无**（单头文件族的 C++ 库；上游自带 Makefile 仅用于测试/示例）
- 编译日期: 2026-09-18
- 编译器: OHOS clang / clang++（Conan profile `ohos-aarch64`）
- 上游测试依赖: `gtest/1.17.0` + `gmock/1.17.0`（`test_requires`）
- 状态: built

## 版本与源码
- 平台版本 `0.0-git20211103.35e800d` = Debian 快照 `0.0~git20211103.35e800d`
  （上游 google/libnop 2021-11-03 提交）；Conan 版本不允许 `~`，故归档目录用 `-git<date>`。
- 源码：`https://deb.debian.org/debian/pool/main/libn/libnop/libnop_0.0~git20211103.35e800d.orig.tar.xz`
  sha256 `0884e871295d53460c179efda8538242a7cb4fb86b6f226cc7058c656da713bd`

## 产物
- `include/nop/**`（62 个头文件：serializer.h、structure.h、base/、types/、rpc/、traits/、utility/…）
- `licenses/LICENSE`
- 无编译产物：`package_id()` 已清空二进制设置

## 上游测试套件（315 用例，真机全通过）

上游 `test/*.cpp`（20 个文件）是完整的 **GoogleTest/GoogleMock** 套件，由上游 Makefile 在
检测到 gtest 时构建（`out/test`）。适配做法：

```python
def build_requirements(self):
    self.test_requires("gtest/1.17.0")
    self.test_requires("gmock/1.17.0")

# build()
gtest = self.dependencies["gtest"]          # 注意：不是 self.dependencies.build[...]
make -j1 \
  CC=<clang> CXX=<clang++> \
  HOST_CFLAGS="-g -O2 -Wall -Wextra -Iinclude" \   # 去掉上游的 -Werror
  HOST_CXXFLAGS="-std=c++17" \                     # 上游写死 -std=c++14，gtest 1.17 需 C++17
  GTEST_INCLUDE="-I<gtest>/include -I<gmock>/include" \
  GTEST_LIB="-L<gtest>/lib -L<gmock>/lib"
LD_LIBRARY_PATH=<gtest>/lib:<gmock>/lib out/test
```

结果：**315 passed / 0 failed**（`[  PASSED  ] 315 tests.`），构建脚本会解析该摘要，
出现失败即让 `conan create` 失败。

| # | 问题 | 原因 | 处理 |
|---|------|------|------|
| 1 | `KeyError: 'gtest' not found in the dependency set` | `test_requires` 不在 `self.dependencies.build` 里 | 用 `self.dependencies["gtest"]`（仓库先例 `archives/a/abseil`） |
| 2 | `gtest-port.h: C++ versions less than C++17 are not supported` | 上游 Makefile `HOST_CXXFLAGS := -std=c++14`，而 gtest/gmock 1.17 要求 C++17 | 覆盖 `HOST_CXXFLAGS=-std=c++17` |
| 3 | 版本冲突 `gtest/1.17.0` vs `gtest/1.17.0.1` | `gmock/1.17.0` 依赖 `gtest/1.17.0` | 与 gmock 对齐，统一用 `gtest/1.17.0` |
| 4 | `-Werror` 下第三方 gtest 头触发告警 | 上游对自家代码严格、但把第三方头也纳入 | 保留 `-Wextra`、去掉 `-Werror`（文档记录） |
| 5 | 纯头文件包为空（`No files in this package!`） | `copy(..., dst="include")` 的相对 dst 不落到 package_folder | 用 `os.path.join(self.package_folder, "include")` 绝对路径（同 `DRAFT-picosha2` 记录） |

## 消费者测试（8 项断言）

`test_package/test_libnop.cpp` 仅使用安装后的头文件：

1-2. `int32` / `std::string` 序列化后反序列化一致
3. `std::vector<int>` 往返一致
4. `NOP_STRUCTURE` 注解类型（含私有成员的 struct）往返一致
5-6. `nop::Optional` 有值 / 空值往返一致
7. 序列化结果非空且确定（同值两次序列化字节相同）
8. 截断输入反序列化干净失败（`Read()` 返回非 Ok）

## 验证结果

```sh
conan create archives/l/libnop/0.0-git20211103.35e800d -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0
# 上游：upstream GoogleTest suite: 315 passed, 0 failed
# 消费者：ctest 1/1，8/8 断言
```
