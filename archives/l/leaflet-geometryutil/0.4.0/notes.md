# leaflet-geometryutil 0.4.0 鸿蒙适配笔记

## 环境信息

- 操作系统：HarmonyOS 6.0（aarch64）
- 构建系统：无（纯 JavaScript）
- Conan 2.x，profile: ohos-aarch64

## 依赖

- Leaflet（软依赖，消费者需自行提供）

## 构建步骤

1. 从 npm registry 下载 tarball（conandata.yml 已记录 sha256）
2. Conan 配方复制 dist/leaflet.geometryutil.js、package.json、README.md 到 package 目录
3. 通过 NODE_PATH 暴露给消费者

## 上游测试情况

上游测试（test/index.html + test/test.geometryutil.js）为 mocha + chai 浏览器端测试，
通过 mocha-phantomjs 驱动，依赖 phantomjs（已 EOL，无 aarch64 构建）。

替代方案：用 jsdom + 真实 Leaflet 0.7.2 + mocha 搭建 Node 端等效环境，
**原样执行上游 60 个测试用例**，不修改任何上游测试文件：

- test_package/upstream-test.js：上游 test.geometryutil.js 的副本
- test_package/setup.js：jsdom + Leaflet 0.7.2 初始化，模拟浏览器 DOM 与 Canvas
- test_package/test.sh：调用 mocha 跑 upstream-test.js

上游 60 个用例全部通过（60 passing, 0 failing），数值期望值与浏览器环境一致。

## 鸿蒙专属测试

test_package/harmony_smoke.js 共 40 条断言，分 3 类：

1. API 挂载（24 项）：验证 L.GeometryUtil 及 23 个核心 API 全部挂载
2. 纯函数数值（13 项）：computeAngle、computeSlope、interpolateOnPointSegment、
   readableDistance、bearing、destination、length、accumulatedLengths
3. 鸿蒙平台消费者场景（3 项）：在地图实例上调用 distanceSegment/closest，
   验证真实消费场景

## 鸿蒙沙箱 JIT 问题

OHOS 沙箱拦截 mmap(PROT_EXEC)，Node.js 默认触发 JIT 会崩溃：

    Check failed: 12 == (*__errno_location()).
    Signal 5 (core dumped)

解决方案：test.sh 顶部 `export NODE_OPTIONS=--jitless`，所有 Node 进程（包括 npm install）
禁用 JIT。测试为纯 JS 逻辑，不依赖 WASM。

## 关键技术点

- jsdom 模拟浏览器 DOM（Leaflet 0.7.x 需要完整的 document/window/screen/navigator）
- 假 Canvas 2D context（Proxy 万能可写对象）绕过 jsdom 不支持 canvas 的限制
- 补 SVGElement.style 可写对象
- 通过 Module._load hook 让 geometryutil UMD 拿到与测试同一个 L 实例

## L0 门禁适配

- L0c 要求 test_package/ 有 .sh/.py/.c/.cpp/.cc/.cxx 测试源 → test.sh
- L0e 要求 test_package/MANIFEST.yml → 已补
- conanfile.py 使用 env="conanrun" 注入 NODE_PATH（VirtualRunEnv）

## 测试结果

- Conan create 全流程通过
- 上游测试: 60 passing, 0 failing
- 鸿蒙专属测试: 40 passed, 0 failed
- 总计: 100/100
