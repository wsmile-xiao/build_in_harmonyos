# ossp-uuid 1.6.2-r5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-13
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤
1. `./configure --prefix=$PREFIX --enable-static --disable-shared --build=aarch64-unknown-linux-ohos --no-create`
2. 修补 config.status 使用预创建临时目录（E002: HMDFS 不支持 mktemp）
3. `./config.status`
4. `make -j1 && make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E001 | configure 找不到 C 编译器 | PATH 中无 cc 软链接 | build() 中设置 CC=clang CXX=clang++ |
| E002 | config.status 创建临时目录失败 | HMDFS 不支持 mktemp | 预创建 conf_preset 目录, 修改 config.status 引用 |
| E007 | config.guess 无法识别 HarmonyOS | 2008 版脚本不含 HarmonyOS 检测分支 | patches/0001 / 0002 补丁添加支持 |

## 源码修改
- patches/0001-config.guess.patch: 添加 HarmonyOS 系统识别（uname -s → aarch64-unknown-linux-ohos）
- patches/0002-config.sub.patch: 添加 aarch64 CPU 类型 + linux-ohos* / -ohos* 操作符支持

## 依赖版本
无外部依赖（纯 C 库，仅 libc）

## 验证结果
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
# G0-G4 全部通过
# test_package: 1/1 test passed (0.06s)
```

## 注意事项
- 静态构建产物: libuuid.a (+ libuuid.so 动态库)
- 交付物不包含 systemd/tmpfiles 相关文件（OHOS 不适用）

---

**编译结束**: 2026-07-13
**最终状态**: built
