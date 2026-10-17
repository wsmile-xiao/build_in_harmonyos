# fdk-aac 2.0.3.2

Fraunhofer FDK AAC 编解码库,鸿蒙 PC(OpenHarmony PC)适配配方。

上游:https://sourceforge.net/projects/opencore-amr/ (2.0.3 发行包,零 patch)

## 结构

```
2.0.3.2/
├── conanfile.py        # cmake 配方;BUILD_PROGRAMS=ON;真机 ninja --parallel 8
├── conandata.yml       # 官方 SourceForge 源 + sha256(与 2.0.3 同源)
├── manifest.yaml       # 版本级清单(状态/构建口径/知识发现)
├── notes.md            # 适配笔记(上游分析/设计决策/测试矩阵)
├── README.md
└── test_package/
    ├── conanfile.py    # L0c:四 settings + 非 conanfile 测试源
    ├── CMakeLists.txt  # 探针 + 上游官方工具同批构建
    ├── probe.c         # 消费者探针(18 断言,编码往返 + SHA-1)
    ├── test.sh         # 三阶段:探针 / 官方 fixture 套件 / 合成 wav 烟测
    ├── gen_fixture.py  # 确定性 wav 生成(441Hz 正弦表,官方工具阈值内)
    ├── MANIFEST.yml    # 测试清单(probe 18 断言 + upstream_tests 溯源)
    └── upstream-test/  # 官方发行包 vendor:test-encode-decode 工具源 + refs + run-test.sh + NOTICE
```

## 测试

- **消费者探针**(永远执行):441Hz 正弦表 + LCG 噪声合成 PCM(纯整数,
  与 libm 无关)编码往返,18 项结构断言,聚合 SHA-1 输出。
- **官方套件**(官方 wav fixture 置入测试目录时):`test.sh` 复刻官方
  `run-test.sh` 全语义 —— md5 校验 Xiph Sample01_4.wav(1543244B,
  a5c10554…)与 ffmpeg 单声道版(3bfccac9…),`test-encode-decode` 跑全模式
  矩阵,输出哈希与 `ref-stereo.txt` / `ref-mono.txt` 比对。
  **架构分流**:官方 ref 生成于 x86;FDK 在 ARM64 使用 16-bit 系数表 +
  32x16 定点乘法(上游 FDK_archdef.h 设计),码流跨架构设计上非位元一致。
  x86 必须与 ref 位元一致(MinGW 本地已验证);其他架构以上游工具自身
  质量门禁(退出码=0 且各模式 avg_diff 阈值内,真机 aarch64 已验证)为准。
- **合成 wav 烟测**(无官方 fixture 时):gen_fixture.py 生成确定性 wav,
  验证官方工具可运行且哈希行形状正确。

## 版本说明

任务版本 2.0.3 已存在于官方 main 与制品仓(R37 铁律),本配方递增
Conan 版本后缀至 2.0.3.2;上游源码保持官方 2.0.3 发行包不变。
