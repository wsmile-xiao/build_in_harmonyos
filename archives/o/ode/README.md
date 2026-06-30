# ODE (Open Dynamics Engine)

## 简介
ODE 是一个高性能的开源刚体物理模拟库，广泛应用于游戏、虚拟现实和机器人仿真领域。

## OHOS 适配要点
- CMake 版本要求 >= 3.5，在 OHOS 上需设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 禁用 demos 和 tests 以避免 OpenGL 依赖（OHOS 上缺少完整 OpenGL 支持）
- 建议编译为静态库，避免动态库的依赖问题
- 使用 autotools 时会遇到工具链兼容性问题，推荐使用 CMake 构建

## 编译配置
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DODE_WITH_DEMOS=OFF \
  -DODE_WITH_TESTS=OFF \
  -DBUILD_SHARED_LIBS=OFF
make -j2
make install
```

## 依赖
- 无外部依赖（核心库）
- demos/tests 需要 OpenGL（已禁用）

## 功能验证
```bash
# 检查静态库
ls $DEFAULT_PREFIX/lib/libode.a

# pkg-config 验证（如已安装）
pkg-config --modversion ode
```

## 参考
- 官网：https://www.ode.org
- 源码：https://bitbucket.org/odedevs/ode
- 文档：https://ode-wiki.org