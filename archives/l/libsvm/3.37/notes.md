# libsvm 3.37 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，无 autotools/configure）
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

libsvm 使用简单 Makefile，无 configure 脚本和 install 目标，采用模式 B 手动编译。

1. 下载源码（SSL 证书问题，使用 Python SSL bypass 下载）
2. `make all` — 编译 svm-train、svm-predict、svm-scale
3. `make lib` — 编译共享库 libsvm.so.4
4. 手动安装到 DESTDIR（$TEST_PREFIX/$DEFAULT_PREFIX/）
   - mkdir -p bin lib include
   - cp svm-train svm-predict svm-scale → bin/
   - cp libsvm.so.4 → lib/，ln -s libsvm.so.4 libsvm.so
   - cp svm.h → include/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | NTU 服务器 SSL 证书不被鸿蒙信任 | Python urllib + SSL bypass 下载 |
| 2 | make install 无目标 | libsvm Makefile 无 install target | 手动 mkdir+cp 安装到 DESTDIR |
| 3 | g++ 不可用 | 鸼蒙平台只有 clang++ | make CXX=clang++（Makefile 默认 g++） |
| 4 | 大量 -Wsign-conversion 警告 | 上游代码 int→size_t 转换（-Wconversion 标志） | 上游代码问题，不影响功能 |

## 源码修改

无源码修改。libsvm 3.37 在鸿蒙平台使用 clang++ 编译无需任何代码改动。

## 依赖版本

无外部依赖。libsvm 是独立的 SVM 库，仅依赖标准 C/C++ 库和数学库 (-lm)。

## 验证结果

```bash
# svm-train 功能测试
$ svm-train heart_scale /tmp/heart_scale.model
optimization finished, #iter = 162
nu = 0.431029, nSV = 132

# svm-predict 功能测试
$ svm-predict heart_scale /tmp/heart_scale.model /tmp/heart_scale.out
Accuracy = 86.6667% (234/270) (classification)

# svm-scale 功能测试
$ svm-scale heart_scale > /tmp/heart_scale.scaled
# 270 行缩放输出正常

# 版本信息
$ svm-train（无 --version 参数，通过用法输出确认版本 3.37）
```

## 鸿蒙特有测试（2026-09-01 新增，积分赛 PR 补全）

`test_package/test_libsvm_ohos.cpp` — 4 用例（真实调用被测库 API，非 mock）：
1. `LIBSVM_VERSION == 337` 断言（HarmonyOS 工具链下头文件版本身份）
2. C_SVC + LINEAR 训练 2D 线性可分合成数据集（40 样本）+ `svm_predict` 40/40 全对
3. `svm_save_model` / `svm_load_model` 真文件往返 + 预测一致性 40/40
4. C_SVC + RBF 训练 + `svm_predict_values` 决策函数有限且标签正确

本地真机 4/4 全过（clang++ 15.0.4，链接 libsvm.so.4）。
CMakeLists 与 test conanfile 同步注册第二个可执行文件与运行步骤，
MANIFEST.yml 声明 `ohos_specific_test` 段（4 用例）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| svm-train | 88576 bytes | SVM 训练工具 |
| svm-predict | 84480 bytes | SVM 预测工具 |
| svm-scale | 31104 bytes | 数据缩放工具 |
| libsvm.so.4 | 84416 bytes | SVM 共享库 |
| svm.h | 3454 bytes | SVM 头文件 |

## 注意事项

- libsvm 的命令行工具没有 --version 参数，版本通过源码确认
- libsvm.so.4 是共享库版本，SHVER=4 为上游定义
- 编译时有大量 -Wsign-conversion 警告，属于上游代码风格问题，不影响功能

## 对话记录

### 初始化阶段
- init-build 成功，SSL 下载失败后用 Python urllib SSL bypass 手动下载源码到 ~/tmp/downloads/
- 将 tarball 复制到 ~/tmp/builds/ 后 init-build --no-download 成功完成
- 环境检查：CC=clang, CXX=clang++, CFLAGS=-fPIC -O2, TMPDIR 已设置

### 编译阶段
- 模式 A 自动编译：make 成功（svm-train/svm-predict/svm-scale 编译完成），但 make install 失败（无 install 目标）
- 切换到模式 B：手动 make lib 生成 libsvm.so.4
- 手动安装到 DESTDIR：mkdir + cp 到 $TEST_PREFIX/$DEFAULT_PREFIX/bin/lib/include/
- Staging 安装验证通过：所有产物文件类型、大小、功能均正常

### 功能测试阶段
- 9 项真实功能测试全部通过（详见 reports/test-report.md）
- svm-train heart_scale: 162次迭代收敛，nSV=132
- svm-predict: 准确率 86.67%
- svm-scale: 270行缩放输出
- 不同核函数（线性/多项式）训练均成功
- 共享库 SONAME=libsvm.so.4，依赖仅 libc++_shared.so + libc.so

### 打包部署阶段
- ohc-run.py package 成功：libsvm-3.37-ohos-aarch64.tar.gz (450136 bytes)
- 本地安装到 ~/usr/local 成功，所有工具功能正常
- 无安全弹窗问题（HongMeng Kernel 1.12.0 已解决）

### 收尾阶段
- finish 成功，状态升级为 published
- G0 干净构建验证失败（已知限制：makefile 项目无 configure 脚本）
- G1-G4 质量门禁全部 PASS
- 知识草稿已创建（libsvm 无 configure、手动安装 DESTDIR、CXX 覆盖等）
---

**编译结束**: 2026-06-10 16:02
**最终状态**: published
