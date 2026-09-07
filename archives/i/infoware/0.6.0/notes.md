# infoware 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 原生，C++14）
- 状态: built

## 编译步骤

```bash
# as-is 探索（设备，源码包 SHA256 见 conandata.yml）
cmake -B b -DCMAKE_BUILD_TYPE=Release \
  -DINFOWARE_EXAMPLES=ON -DINFOWARE_TESTS=ON \
  -DINFOWARE_PCI_IDS_PATH=$HOME/tmp/uc2/infoware/pci.ids.pin
cmake --build b -j2
ctest --test-dir b                 # 官方 4 用例套件
```

配方 generate() 设 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64
（CMake 无 OHOS 模块）、INFOWARE_PCI_IDS_PATH 指向 conandata 第二源下载的
pci.ids、INFOWARE_EXAMPLES/TESTS=ON，build() 内 cmake.test() 使官方套件在
CI 同样实跑。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译失败：`invalid output constraint '=a' in asm`（cpuid.h/__cpuid/xgetbv，src/detail/cpuid_non_windows.cpp） | 上游该文件用 x86 专有 CPUID/XGETBV 内联汇编，无 ARM 路径；aarch64 上必然编译失败 | 补丁 0001：用架构宏 `__x86_64__`/`__i386__` 守卫 x86 实现，非 x86 主机提供零值回退（cpuid 零叶、xgetbv 返回 0）。核验全部消费方（instruction_set/vendor_id）只做位测试，零值安全无除零路径 |
| 2 | 配置失败：pci.ids 缺失，CMake 要求 git clone pciutils/pciids | 上游构建期需要 pci.ids 生成 pci_data.hpp，默认 clone GitHub 仓库，CI worker 无 git/网络条件 | conandata.yml 第二源钉定官方 pciutils/pciids 快照（commit 347ba64b），INFOWARE_PCI_IDS_PATH 指向下载文件 |
| 3 | CMake 无法识别 OHOS 平台 | CMake 官方无 OHOS 模块 | CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（abcmidi/cbmconvert 同款模式） |

## 源码修改

- `patches/0001-src-detail-cpuid_non_windows.cpp.patch`：唯一源码修改。
  仅使用架构宏（非平台宏，符合 R8/PF5）；x86 路径语义不变，非 x86 主机
  报告"无特性"而非编译失败。

## 依赖版本

无 Conan 依赖（pci.ids 为构建期数据文件，非链接依赖）。

## 验证结果

```bash
$ ctest --test-dir b               # 官方套件（补丁后），设备实测 2026-09-06
100% tests passed, 0 tests failed out of 4
# example_cpu / example_gpu / example_pci / example_system 全部通过
```

- 上游静态用例总数：4（CMakeLists.txt 中 foreach 为 4 个 example 各注册
  1 个 add_test，静态计数；INFOWARE_EXAMPLES+INFOWARE_TESTS 均为 ON）
- 实际执行：4；通过：4；失败：0；跳过：0
- 消费者测试（test_package）：编译链接安装产物，真实调用
  `iware::cpu::quantities()`、`iware::system::memory()`、
  `iware::cpu::endianness()`，断言逻辑核心数≥1、物理内存总量非零、
  小端序，3 项断言全部通过

## 注意事项

- 库为静态包（package_type=static-library）；CMake config 由上游导出
  （无命名空间），消费者测试用 CMakeDeps 生成 `infoware::infoware` 目标。
- gpu 检测的后端（D3D/OpenGL/OpenCL/X11）全部保持默认 OFF，OHOS 上
  走无后端路径；pci.cpp 依赖生成的 pci_data.hpp，已由 pci.ids 驱动生成。
---

**编译结束**: 2026-09-06 02:46
**最终状态**: built
