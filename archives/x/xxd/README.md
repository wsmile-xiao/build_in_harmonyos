# xxd for HarmonyOS

## 概述

xxd 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

xxd 是一个命令行十六进制转储工具，是 vim 编辑器项目的一部分。它是一个纯 C 单文件程序 (xxd.c)，没有外部依赖。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | xxd |
| 版本 | 9.1.0 |
| 下载地址 | https://github.com/vim/vim/archive/refs/tags/v9.1.0.tar.gz |
| 官方文档 | https://www.vim.org/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | makefile |

## 编译步骤

```bash
# 1. 使用 Conan 构建
conan create archives/x/xxd/9.1.0/conanfile.py -pr ci/conan/profiles/ohos-aarch64 --build=missing

# 2. 安装
conan install xxd/9.1.0
```

## 补丁说明

无补丁 (patches: [])。xxd 是纯 C 单文件，无需平台适配补丁。

## 遇到的问题

### 问题1: 源码嵌套在 vim 仓库中

**现象**: xxd 源码不在仓库根目录，而在 src/xxd/ 子目录中

**原因**: xxd 是 vim 编辑器的一部分

**解决**: conanfile.py 中使用 `os.path.join(self.source_folder, "src", "xxd")` 定位源码目录

### 问题2: LDFLAGS 在 CI 中失败

**现象**: CI 环境构建时 LDFLAGS 指向不存在的 ld.bfd

**原因**: /data/service/hnp/bin/ld.bfd 仅存在于本地 OHOS 设备

**解决**: 改为条件性使用 `os.path.isfile(ld_bfd)` 判断，CI 使用默认链接器

## 测试结果

详见 [test_xxd.sh](./9.1.0/test_package/test_xxd.sh)

| 测试项 | 结果 |
|--------|------|
| 版本检查 (-v) | ✅ |
| 十六进制转储 | ✅ |
| 纯十六进制输出 (-ps) | ✅ |
| C 数组输出 (-i) | ✅ |
| 反向操作 (-r -ps) | ✅ |

## 验证安装

```bash
# 检查安装
which xxd
xxd -v

# 功能验证
echo "hello" | xxd
echo "hello" | xxd -ps
echo "hello" | xxd -i
```

## 经验总结

1. xxd 源码嵌套在 vim 仓库的 src/xxd/ 目录中
2. Makefile 自动添加 -DUNIX 宏
3. 无需任何补丁，纯 C 单文件仅依赖标准库
4. ELF 签名在 OHOS 上是必需的
5. LDFLAGS 需条件性使用以兼容 CI 环境

## 参考资料

- https://github.com/vim/vim
- https://www.vim.org/
