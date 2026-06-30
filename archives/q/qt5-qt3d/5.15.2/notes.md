# qt5-qt3d 5.15.2 编译笔记

## 编译信息

- **软件**: qt5-qt3d
- **版本**: 5.15.2
- **构建系统**: qmake
- **目标平台**: HarmonyOS (aarch64-linux-ohos)

## 编译步骤

1. 设置Qt5环境：
   ```
   export PATH=/storage/Users/currentUser/usr/local/Qt5/bin:$PATH
   export QTDIR=/storage/Users/currentUser/usr/local/Qt5
   ```

2. qmake配置：
   ```
   cd ~/tmp/qt5-qt3d-src
   /storage/Users/currentUser/usr/local/Qt5/bin/qmake qt3d.pro
   ```

3. 编译（约30分钟）：
   ```
   make -j2
   ```

4. 安装：
   ```
   make install
   ```

## 编译结果

编译成功，无需源码修改。Qt3D的所有模块均正常编译和安装。

### 安装的库文件

| 库 | 版本 |
|---|---|
| libQt53DCore | 5.15.2 |
| libQt53DRender | 5.15.2 |
| libQt53DInput | 5.15.2 |
| libQt53DLogic | 5.15.2 |
| libQt53DAnimation | 5.15.2 |
| libQt53DExtras | 5.15.2 |
| libQt53DQuick | 5.15.2 |
| libQt53DQuickRender | 5.15.2 |
| libQt53DQuickInput | 5.15.2 |
| libQt53DQuickAnimation | 5.15.2 |
| libQt53DQuickExtras | 5.15.2 |
| libQt53DQuickScene2D | 5.15.2 |

### 安装的可执行文件

- qgltf

### 安装的QML插件

- Qt3D/Core, Input, Render, Animation, Extras, Scene2D

### 安装的渲染插件

- plugins/renderplugins/libscene2d.so

## 平台适配

**无需适配**。qt3d源码中没有需要修改的UNIX/LINUX条件宏。Qt的mkspecs已使用harmonyos-clang配置，编译时自动添加`-D__OHOS__`标志。

## 依赖

- qt5-qtbase 5.15.2（已安装）
- qt5-qtdeclarative 5.15.2（已安装，提供Qml和Quick模块）

## 注意事项

- qt3d内置了assimp作为3rdparty库，用于3D模型加载
- System Assimp未使用，使用bundled assimp
- Autodesk FBX支持未启用
- make -j2的jobserver mkfifo有"Operation not permitted"警告，但不影响编译
- assimp代码有一些deprecated warnings（C++拷贝构造/赋值），但不影响功能

---

**编译结束**: 2026-05-31
**最终状态**: built (成功)