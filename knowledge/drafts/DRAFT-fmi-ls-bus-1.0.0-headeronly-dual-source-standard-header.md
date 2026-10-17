# Header-only 库公开头依赖未入 registry 的配套标准头 — 配方以第二官方源固定提交打包

> 草稿编号：DRAFT-fmi-ls-bus-1.0.0-headeronly-dual-source-standard-header
> 来源：fmi-ls-bus 1.0.0 适配（modelica/fmi-ls-bus @ v1.0.0，FMI-LS-BUS 规范 C-API）
> 生成日期：2026-09-22

## 问题描述

header-only C API 库的公开头 include 了来自**另一个官方仓库**的配套标准头（平台类型头），
而该配套头在 ohpcd registry 中**没有对应的 Conan 包**。直接打包自身头文件时消费者编译
公开头报 `fmi3PlatformTypes.h file not found`。

实例：`fmi-ls-bus/headers/fmi3LsBus.h` 第 54 行 `#include "fmi3PlatformTypes.h"`，该头来自
`sources` 之外的独立官方仓库 `modelica/fmi-standard`（FMI 3.0 标准头）。上游 tests/CMakeLists.txt
显式加入 `-I ../fmi-standard/headers`，上游 GitHub Actions 用 `actions/checkout` 单独拉取
fmi-standard 仓库——即上游自身也是"双仓库"工作流，但 Conan 干净构建无此上下文。

## 根因

1. 上游拆仓：标准头仓库（fmi-standard）与库头仓库（fmi-ls-bus）分离，公开头直接跨仓 include；
2. registry 无配套头包：`conan list "fmi*" -r=ohpcd` → 0 匹配，无法用 `requires()` 声明依赖；
3. 若仅打包库自身头文件，消费者 include 链断裂；若把依赖写成 `requires("fmi-standard/x")` 而包不存在，
   CI 下载/解析必失败（PF4 依赖闸前置探测会拦截）。

## 方案（第二官方源固定提交打包）

conanfile.py `source()` 双 `get()` + `package()` 合并拷入 `include/`：

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)          # 库官方 tarball
    get(self, **self.conan_data["fmi_standard"], strip_root=True,     # 配套标准头官方 tarball
        destination="fmi-standard")

def package(self):
    copy(self, "*.h", src=os.path.join(self.source_folder, "headers"),
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "fmi3PlatformTypes.h",
         src=os.path.join(self.source_folder, "fmi-standard", "headers"),
         dst=os.path.join(self.package_folder, "include"))
```

conandata.yml 双源各带官方 URL 与 SHA-256：

```yaml
sources:
  url: "https://github.com/modelica/fmi-ls-bus/archive/refs/tags/v1.0.0.tar.gz"
  sha256: "c72ea6bc..."
fmi_standard:
  url: "https://github.com/modelica/fmi-standard/archive/5365a49654d2f6e5b0bc7c75b5176b495dd72ac5.tar.gz"
  sha256: "de94e769..."
```

配套纪律：
- 第二源必须**固定提交**（不能用 `main`/`master` 移动标签），保证可复现；
- SHA-256 必须取**声明 URL 实际字节**（GitHub archive URL 与 api.github.com tarball 端点对同一
  ref 返回不同 gzip 字节——源码内容一致但哈希不同，见验证），并做解压内容 diff 确认源码等价；
- 与 DRAFT-EA-headeronly-dependency-chain 的差异：该草稿针对"依赖已有 conan 包 + cpp_info.requires/
  includedirs 传播"；本方案针对 **registry 完全没有该头包**时，以官方第二源打进包内。

## 验证

- conan-verify G2 `conan create`（ohos-aarch64 profile）通过；
- 消费者 test_package 仅经已安装公开头 `#include <fmi3LsBus.h>` + 调用 CAN API，
  编译链接运行成功，8/8 断言通过（无私有头、无内部符号）；
- 鸿蒙专项测试 7/7 通过；
- 上游头测试（MODULE_LIST=can）130/130 通过；flexray 104 为明确上游排除条件
  （v1.0.0 发布版不含 fmi3LsBusFlexRay.h，上游 CI 输入声明 "Available is 'can'"），
  按双口径 130/234 全量口径、130/130 可执行集合口径上报。

## 适用边界

- 适用：header-only C/C++ 库的公开头 include 独立官方仓库的配套标准头/平台头，且 registry 无该头包；
  FMI 族（fmi-ls-bus/fmi-standard、Modelica 体系）、标准组织头（如 X 协议族配套头）等；
- 反例/不适用：依赖头已有 conan 包 → 走 `requires()` + DRAFT-EA 传播方案；
  依赖是可编译库 → 应逐层适配发布（R36 拓扑序），不应直接打包二进制；
  移动标签第二源 → 不可复现，禁止。

## 查重差异（相对既有条目）

- 正式 E321/E322：覆盖 header-only Conan 2 配方骨架（package_type/cmake_target），未涉及"第二官方源
  打包缺失标准头"；
- 正式 E257：header-only G1 需显式 no-op build()，普通前置坑；
- 正式 E282：多源码配方的 patches base_path 路由，面向补丁而非打包；
- 正式 E406：SHA-256 多网络路径交叉验证（代理 vs 直连语境）；本方案新增边界=两个**官方**端点
  也会字节不同，哈希必须绑定声明 URL；
- 草稿 DRAFT-EA-headeronly-dependency-chain：前提是依赖已入 registry，与"无包可依赖"场景互补。