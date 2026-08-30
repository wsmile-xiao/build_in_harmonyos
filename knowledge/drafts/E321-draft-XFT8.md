# E321 — 已发布包的 .so 可能带消费端不接受的签名（dlopen: Permission denied）

## 错误特征

同一个视图目录里，相邻的库能正常加载，只有目标库被拒：

```
/storage/.../runtime-libs/libfreetype.so.6      -> OK
/storage/.../runtime-libs/libxml2.so.16         -> OK
/storage/.../runtime-libs/libfontconfig.so.1    -> Error loading shared library
                                                   /storage/.../libfontconfig.so.1:
                                                   Permission denied
```

关键区别于路径问题：错误文案是 `Permission denied`，而不是 `No such file`。
也区别于 E135（完全未签名）：`llvm-readelf -SW` 显示该文件**确实含 `.codesign` 段**
（计数为 1），只是这个签名在本机不被接受。

## 触发条件

- 构建系统: 无关（autotools/cmake/meson 都会遇到）
- 阶段: configure 运行探测、test_package 执行、任何 dlopen/加载器映射
- 前提: 使用从制品仓下载的**已发布**共享库二进制

## 根因分析

共享库在构建机上完成自签名后随二进制包分发。设备侧的 ELF 校验依据本机策略
判定签名是否可接受，因此"有签名"不等于"在这台机器上有效"。一旦被判无效，
加载器拒绝映射该库，错误以 `Permission denied` 形式出现，极易被误读成
权限位问题（HMDFS 的权限位会被归一化，且 MAC 优先）或路径/符号链接问题。

## 解决方案

### 推荐方案

把目标库复制进任务私有视图后**先去段、再重签名**，最后自校验：

1. `llvm-objcopy --remove-section .codesign <copy>`
   （`binary-sign-tool` 无法覆盖已存在的 `.codesign`，必须先移除）
2. `binary-sign-tool sign -inFile <copy> -outFile <copy>.signed -selfSign 1`
3. 原子替换回原名，恢复执行位，校验 `.codesign` 计数**恰为 1**

操作顺序固定为 RPATH → strip/调试分离 → 签名 → 权限（修改类步骤必须在签名之前）。
依赖包本体保持只读、零改动。

### 禁止做法

- ❌ 看到 `Permission denied` 就改静态链接：只掩盖本机加载问题，改变产物语义
- ❌ 用 `chmod`/放宽 umask 修复：HMDFS 归一化权限位，MAC 优先于 DAC；
  反复 `chmod +x` 本身就是签名失效的信号（E077）
- ❌ 把签名问题误判为"路径没设对"而反复调 `LD_LIBRARY_PATH`（见 E257）

## 验证

```bash
# 逐个绝对路径 dlopen，隔离"签名 vs 路径 vs 符号链接"
./dl_probe /abs/path/libfontconfig.so.1     # Permission denied ⇒ 签名问题
./dl_probe /abs/path/libfreetype.so.6       # OK              ⇒ 同目录可用，排除路径
# 重签名后
llvm-objcopy --remove-section .codesign $V/libfontconfig.so.1
binary-sign-tool sign -inFile $V/libfontconfig.so.1 -outFile $V/x.signed -selfSign 1
mv $V/x.signed $V/libfontconfig.so.1
./dl_probe libfontconfig.so.1               # 期望 OK
```

## 关联条目

- 相关: E135（未签名版本）、E077（签名失效表现）、E257（搜索路径语义）
- 来源: libxft 2.3.8 适配，2026-08-28，fontconfig/2.18.3 已发布二进制实测
