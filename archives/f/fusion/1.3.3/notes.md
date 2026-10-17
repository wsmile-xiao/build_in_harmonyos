# fusion 1.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

```bash
# 源码：https://github.com/xioTechnologies/Fusion/archive/refs/tags/v1.3.3.tar.gz
# SHA-256: 84fc2a6e04f4e2fe4388f506040b3f63359293902211be562bb767b93962161d
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX
cmake --build build -j2     # 产出 libFusion.a + Simple/Advanced 两个示例
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2: test_package 报 `fatal error: 'Fusion.h' file not found` | 上游 CMake 无 install 规则，模板配方照搬 cmake.install() 打包 0 文件；手动装配布局为 include/Fusion/ 子目录 | package() 手动 copy 公开头到 include/Fusion/、复制 libFusion.a 到 lib/；test_package 改用 `#include <Fusion/Fusion.h>`；cpp_info.system_libs=["m"] |

## 源码修改

无补丁（上游源码直接 OHOS 工具链构建通过，patches/ 为空）。

## 依赖版本

无第三方运行时依赖（仅 libc/m 数学库）。

## 验证结果

```bash
# 上游 C 示例实际运行（exit 0）
./build/Examples/C/Simple/Simple-Example
./build/Examples/C/Advanced/Advanced-Example
# 配方验证（G1/G0/G2/G3/G4 全 PASS，本地 W3 通过）
python3 scripts/ohc-run.py conan-verify fusion 1.3.3
# finish（本地验证通过，上游未发布，状态 built）
python3 scripts/ohc-run.py finish fusion 1.3.3 built
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（手动装配 include/Fusion/*.h + libFusion.a） |
| conandata.yml | 官方 tag v1.3.3 源 + SHA-256 |
| test_package/test.c | 消费者测试（AHRS 静止收敛 + 传感器模型断言，5 断言全过） |
| knowledge/drafts/DRAFT-fusion-1.3.3-cmake-no-install-rule-manual-package.{kv,md} | 路径 B 知识草稿（CMake 无 install 规则手动装配模式） |

## 注意事项

- 语言预检（lang-preflight）误判本库为 python（顶层存在 setup.py/pyproject.toml 供
  Python 绑定层使用），实际主体是 C 库（Fusion/*.c 核心 + C 示例 + C 扩展绑定
  imufusion.c）；按 R47 边界规则（绑定包按主体判、辅助脚本不算主体、c↔cpp 兼容族）
  判定为 c/cpp 并继续 C 库适配流程。
- 上游无独立 C 测试框架，test_*.py 属 Python 绑定层测试（依赖 numpy/scipy），
  不计入 source_declared_total。

---

**编译结束**: 2026-09-19
**最终状态**: built