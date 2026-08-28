# boids

[boids](https://github.com/hughsk/boids) 是 Hugh Kennedy 用 JavaScript 实现的
[Boids 群体模拟算法](https://en.wikipedia.org/wiki/Boids) 轻量级算法库
（Craig Reynolds 于 1987 年提出的经典涌现行为模型）。

- **License**: MIT
- **语言/运行时**: JavaScript / Node.js（纯 JS，无原生代码）
- **版本**: 2.0.0（npm 包 `boids` 的 dist-tag `latest`，与 GitHub tag `v2.0.0` 对应）

## API 概要

```javascript
var Boids = require('boids');
var flock = new Boids({ boids: 50 });  // 可选 speedLimit/accelerationLimit/分离-聚合-对齐参数/attractors
flock.tick();                          // 每帧推进一次模拟
flock.boids                            // 每个 boid 为 [x, y, vx, vy, ax, ay]
flock.attractors                       // [x, y, radius, force]，负力可排斥
```

## OHOS 适配

- **构建系统**: nodejs（npm）。无 C/C++ 源码，无 configure/make/cmake。
- **依赖**: 运行时仅 `inherits@1.0.0`，由 `npm install --omit=dev` 解析并随包捆绑。
- **打包**: `<prefix>/boids/`（模块根）+ `<prefix>/node_modules/inherits/`（运行时依赖），
  配方通过 `runenv_info.NODE_PATH=package_folder` 暴露模块解析路径。
- **测试**: 上游无正式测试套件（无 test 目录 / npm test 脚本，仅含 benchmark.js），
  适配后补全 **17 项功能测试集**（`test_package/test.js`），覆盖构造器/工厂调用、
  数量与记录形状、物理不变式（积分/限速/限加速度）、吸引子/分离/聚合/对齐、
  tick 事件与 1000 帧长稳无 NaN。

## 功能验证

```bash
# 消费者视角（NODE_PATH 由 conanrun 环境注入）
node test.js   # 17 tests passed
```

## 参考

- 上游仓库: https://github.com/hughsk/boids
- npm 包: https://www.npmjs.com/package/boids（latest = 2.0.0）
- 算法原文: https://www.red3d.com/cwr/boids/