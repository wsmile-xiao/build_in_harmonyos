# libfyaml 0.9.6 编译笔记

## 编译信息
- 编译日期: 2026-09-06
- 编译系统: autotools
- 编译器: clang 15
- 平台: aarch64-unknown-linux-ohos

## 编译过程

### 1. 配置
```bash
./configure --prefix=$DEFAULT_PREFIX
```

### 2. 编译
```bash
make -j4
```

### 3. 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

## 产物
- 共享库：lib/libfyaml.so
- 可执行文件：bin/fy-tool
- 开发头文件：include/libfyaml.h, include/libfyaml/*.h

## 验证
- make check: 数据驱动套件 1328/1328 PASS, emitter 525/525 PASS, check 单元 252/286
  (34 个 emit/emit-bugs 失败为上游 emitter 行为断言, 非平台问题)
- OHOS 专项消费者测试 8/8 PASS
- conan create + test_package 消费者验证通过 (G2/G3/G4/L2/L4/L5)

## 补丁
应用了以下补丁：
1. config.guess 增加 HarmonyOS (__OHOS__/HarmonyOS) 识别（aarch64-unknown-linux-ohos）
2. config.sub 增加 ohos-linux 三元组 + linux-ohos* kernel-os 白名单

## 注意事项
- 官方 tag 源码不含生成的 configure, 需先 bootstrap.sh; m4/pkg.m4 需在 bootstrap 前就位
  (PKG_CHECK_MODULES 展开), config.guess/sub 补丁需在 bootstrap 后应用。
- check/0.15.2 为测试框架依赖(制品仓已发布), 运行时需 TEMP 指向可写目录(/tmp 只读)。
---

**编译结束**: 2026-09-06 21:20
**最终状态**: built
---

**编译结束**: 2026-09-07 15:18
**最终状态**: published
