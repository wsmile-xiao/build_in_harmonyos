# boids 2.0.0 适配笔记

## 编译环境
- 构建系统: nodejs（npm，纯 JS 库，无 C/C++ 源码）
- 编译日期: 2026-08-27
- 编译器: N/A（Node.js v24.13.0 / npm 11.6.2）
- 状态: published

## 构建步骤

boids 2.0.0 (hughsk/boids) 是纯 JavaScript 的 Boids 群体模拟算法库，
无 configure/make/cmake 流程。Conan 配方按社区 Node.js 包先例
（dockerfile-language-server）处理：

```bash
# 下载官方 v2.0.0 源码（GitHub tag tarball，SHA256 已校验）
# 解析运行时依赖并打包：
npm install --ignore-scripts --no-audit --no-fund --omit=dev
# 打包:
#   <prefix>/boids/{index.js,package.json,LICENSE.md,README.md,benchmark.js}
#   <prefix>/node_modules/inherits/*
# 消费者：NODE_PATH=<prefix> 后 require('boids') 可用
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 将归档初始化到 skill 根目录 archives/ | find_project_dir() 从脚本位置向上找 SKILL.md，总是命中 skill 根 | 显式传 `--project-dir <构建仓库>` 并在 init-build 时清理误建目录 |
| 2 | 上游无任何正式测试 | 上游为教学/演示性质小库；经 6 项核实确认（见下方"上游测试核实过程"） | 按 API 契约补全 17 项功能测试集（构造/工厂/数量/记录形状/初始态/积分/限速/限加速度/吸引子/分离/聚合/对齐/事件/长稳） |

## 上游测试核实过程

对上游 hughsk/boids 仓库做了全面核实，确认上游测试用例为 0：

1. GitHub 默认分支 master 完整文件树：仅 8 个文件（.gitignore/LICENSE.md/README.md/benchmark.js/demo.js/index.html/index.js/package.json），无 test 目录、无测试文件。
2. GitHub 全部提交历史：遍历所有 commit 的 git tree，历史上从未出现任何测试文件。
3. npm 包 boids@2.0.0 发布内容：与 GitHub 相同，仅 8 个文件，无测试。
4. package.json scripts：仅 start/prepublish，无 test 脚本。
5. benchmark.js：性能基准脚本（测量每秒 ticks），调用 b.tick() 但无结果断言，非测试用例。
6. demo.js / index.html：浏览器 canvas 渲染演示，非测试。

因此上游测试用例 = 0，适配后补全 17 项功能测试集（test_package/test.js，17/17 通过）。
| 3 | 聚合(cohesion)长时动力学不收敛 | 算法无阻尼，纯 cohesion 会出现过冲振荡 | 测试断言改为确定性单帧方向判断（加速度指向质心），不依赖长时动力学 |
| 4 | require('boids') 无法解析 | NODE_PATH 需指向模块根所在目录 | 打包为 <prefix>/boids/ + runenv_info.NODE_PATH=package_folder，test_package 用 conanrun 环境消费 |

## 源码修改

无（上游源码零改动，无补丁；配方层处理打包与依赖）。

## 依赖版本

- 运行时依赖（捆绑打包）: inherits@1.0.0（npm）

## 验证结果

```bash
# 功能测试集（17/17 通过，无失败）：
NODE_PATH=<pkg-root> node test.js      # 17 tests passed

# conan create + conan-verify：
# G0-G4 / L2 / L4 / L5 全部 PASS；test_package 真实运行 Node.js 断言
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（打包 JS 模块 + node_modules/inherits，暴露 NODE_PATH） |
| conandata.yml | 官方源码 URL + SHA256（6a955403...） |
| test_package/test.js | 17 项功能测试集（补全上游缺失） |
| test_package/test.sh | 消费者验证脚本（node 可用性 + NODE_PATH + 模块完整性 + 跑测试） |
| test_package/conanfile.py | test_package 入口（VirtualRunEnv + bash 包装） |
| test_package/MANIFEST.yml | 上游测试说明与测试清单 |

## 注意事项

- 上游 npm "boids" 包 dist-tag latest 即 2.0.0，与 GitHub tag v2.0.0 对应。
- npm install 需网络到 registry.npmjs.org（CI/构建机需联网，与既有 nodejs 包先例一致）。
- 本包为库类型（无 CLI），符合 R38 无需 commands.json。
---

**编译结束**: 2026-08-27 22:15
**最终状态**: built

<!-- ready for PR submission -->
