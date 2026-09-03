# E2174 — HarmonyOS Clang 上 Arm 能力寄存器不可读

## 错误特征
StringZilla 的 Arm 能力探测在 HarmonyOS aarch64 交叉编译时失败，Clang
报告 `expected readable system register`，错误位置涉及 `mrs
ID_AA64ZFR0_EL1`。这发生在库源码编译阶段，而不是消费者链接阶段。

## 触发条件
- 构建系统: CMake
- 阶段: Clang 编译
- 目标: HarmonyOS aarch64
- 典型项目: 直接读取 Arm feature/system registers 的 SIMD 能力检测实现

## 根因分析
上游检测逻辑把 Linux/裸机环境中可读取的 Arm feature register 当成了
HarmonyOS 用户态可读取的寄存器。当前 HarmonyOS Clang 目标拒绝该 `mrs`
操作，因此无法生成目标库。平台宏本身不是能力证明，交叉编译阶段也不能
用构建机的运行时探测结果替代目标判断。

## 解决方案

### 推荐方案
在 HarmonyOS 分支返回保守的串行能力标记，绕过不可访问的 Arm 系统寄存器，
保留上游在其他平台上的能力路径。把该选择固化为可审查的源码补丁，并在
官方源码归档上先做补丁干跑，再用目标 Conan profile 编译和运行安装后的
C consumer。

### 禁止做法
- ❌ 不要仅删除编译错误、把未知平台强行归入 Linux，或把构建机的 Arm
  能力探测结果写入目标配置。
- ❌ 不要用关闭整个测试套件或伪造 SIMD 能力的方式掩盖寄存器不可读问题。

## 验证
```bash
patch --dry-run -p1 < patches/0001-harmonyos-capability-probe.patch
conan create . -pr:h=ohos-aarch64 -pr:b=default -o stringzilla/*:shared=True
```

补丁已针对官方 `StringZilla v5.1.2` release archive 完成 `patch --dry-run`。
鸿蒙端已使用 `ohos-aarch64` profile 强制源码构建；修复后的 Conan 构建、安装
以及 consumer 编译和执行均通过（`W3_RC=0`）。在修复前，目标编译已稳定复现
上述寄存器错误。

## 关联条目
- 相关: E266（编译器能力驱动的目标选择）、E302（目标能力探测不能由符号存在替代）
