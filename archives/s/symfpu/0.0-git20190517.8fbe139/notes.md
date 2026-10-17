# symfpu 0.0-git20190517.8fbe139 适配笔记

## 源码与配方

- 上游仓库：https://github.com/martin-cs/symfpu
- 锁定提交：8fbe139bf0071cbe0758d2f6690a546c69ff0053
- 唯一源码 URL：https://codeload.github.com/martin-cs/symfpu/tar.gz/8fbe139bf0071cbe0758d2f6690a546c69ff0053
- 真机与本地复取 SHA-256：da0baeefb84fb00ad44ad6993d97c2e6cc3568f9aed0d9e8693aa6b599752e5b
- 仅打包上游 core/ 与 utils/ 的 .h 文件和 LICENSE；没有库二进制，也不提交源码 tar 包。
- 配方类型为 header-library，package ID 清空；源码快照没有构建系统，build() 只应用声明补丁（当前为空），test_package 负责编译真实消费者。

## 真机验证

- 设备：HarmonyOS AArch64
- Conan：2.29.1
- CONAN_HOME：/storage/Users/currentUser/work/psj/ch-symfpu
- Host/build profile：ohos-aarch64
- 命令：conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
- 结果：CREATE_EXIT=0；源码 SHA-256 校验通过；包生成完成；test_package 编译并运行完成。
- CMake 使用 CMakeDeps 生成的 symfpu::symfpu target；consumer 编译 test_package/backend/src/simpleExecutable.cpp 和 test_package/test.cpp。

## 上游测试盘点

固定源码归档只有 core/、utils/、LICENSE 与 .gitignore；没有 tests/、测试程序或构建系统文件（Makefile、CMakeLists.txt、meson.build）。因此上游单元、集成、其他测试均为 0，合计 0。没有将消费者测试冒充上游套件。

## 消费者测试结果

Conan test_package 执行一个消费者程序（1/1）；该程序使用后端 traits 对目标版本的模板 API 做三项位模式校验（3/3）：

- unpack + pack：5.0f 保持 0x40a00000
- add：1.0f + 2.0f 得到 0x40400000（3.0f）
- multiply：2.0f × 3.0f 得到 0x40c00000（6.0f）

2019 源码没有 concrete baseTypes。为实例化算法，test_package 提供了官方仓库后续提交 40bdec00 的 simpleExecutable 后端作为测试支持，并只调整了其 source-tree-relative operations.h include，使其指向已安装的 2019 core headers。该 fixture 不复制进 Conan package，也不形成依赖。

## 知识库扩展

DRAFT-symfpu-20190517-traits-backend 成对草稿记录了 trait-based 浮点模板需要真实后端实例化、运行和封装验证的做法，并明确将后端限定在 test_package。它与 E257/E307/E321/E322/E470 的通用 header-only 配方或消费测试，以及现有 E600/E601 的其他 SymFPU 版本问题不同。