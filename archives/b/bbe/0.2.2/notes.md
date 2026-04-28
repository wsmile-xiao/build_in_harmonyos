# bbe 0.2.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-20
- 编译器: clang
- 状态: partial

## 编译步骤
```bash
patch -p1 < 0002-config-config.guess.patch
patch -p1 < 0003-config-config.sub.patch
./configure --prefix=$DEFAULT_PREFIX
make -j$(nproc)
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 2006版缺少 aarch64 支持 | 补丁添加 aarch64/HarmonyOS case |
| 2 | config.sub 不识别 ohos | 缺少 ohos 操作系统支持 | 补丁添加 linux-ohos* 识别 |
| 3 | config.status 临时目录权限 | HMDFS 限制 mktemp -d "./confXXXXXX" | 修改为 ${TMPDIR:-.}/confXXXXXX |

## 验证结果
```bash
bbe --version  # ✅
echo "hello world" | bbe -e "s/hello/HELLO/"  # ✅
```

## 注意事项
- 源码 char*/unsigned char* 混用，产生编译警告（不影响功能）
- 无测试套件
