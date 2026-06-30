# libgrapheme 3.0.0 适配笔记

## 编译环境
- 构建系统: custom configure (suckless style)
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built（编译成功，待完善预编译包）

## 编译步骤

1. 从 GitHub 镜像克隆源码（官方源 SSL 证书问题）
2. 修改 configure 脚本添加 HarmonyOS 系统识别
3. 执行 `./configure --prefix=/storage/Users/currentUser/usr/local`
4. 执行 `make -j1` 编译
5. 执行 `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libgrapheme-3.0.0` 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载失败 | Savannah SSL 证书问题 | 从 GitHub 镜像克隆：https://github.com/FRIGN/libgrapheme |
| 2 | configure 不识别 HarmonyOS | suckless 风格脚本未包含 HarmonyOS | 修改 configure 脚本，添加 HarmonyOS 到系统识别列表 |
| 3 | gen/*.h 文件缺失 | 编译时生成失败 | 恢复 gen/util.h 和 gen/types.h 后重新编译 |
| 4 | ldconfig 命令不存在 | HarmonyOS 不支持 ldconfig | 非致命错误，忽略 |

## 源码修改

**补丁**: 0001-configure.patch
- 修改 configure 脚本，在系统识别部分添加：
```sh
HarmonyOS)
    os="linux"
    ;;
```

## 依赖版本

无外部依赖，仅依赖标准 C 库

## 验证结果

```bash
# 静态库验证
ls -lh /storage/Users/currentUser/builds/libgrapheme-3.0.0.work/libgrapheme.a
# -rw-r--r-- 1 currentUser currentUser 465K May 21 11:30 libgrapheme.a

# 动态库验证
ls -lh /storage/Users/currentUser/builds/libgrapheme-3.0.0.work/libgrapheme.so.3.0.0
# -rwxr-xr-x 1 currentUser currentUser 439K May 21 11:30 libgrapheme.so.3.0.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgrapheme.a | 465KB | 静态库 |
| libgrapheme.so.3.0.0 | 439KB | 动态库 |
| grapheme.h | - | 头文件 |
| man3/*.3 | 22个 | man pages |
| man7/libgrapheme.7 | 1个 | 总览 man page |

**预编译包**: 未生成（需后续完善）

## 注意事项

1. **系统识别**: suckless 风格的 configure 脚本需要手动添加 HarmonyOS 支持
2. **ldconfig**: HarmonyOS 不支持 ldconfig，make install 时需忽略错误
3. **gen 目录**: 首次编译需确保 gen/*.h 文件存在，否则编译失败
4. **测试套**: 未执行 make check，需手动验证功能

## 知识提取

1. **suckless configure 适配** (L1 平台真理)
   - suckless 风格的 configure 脚本需要手动添加 HarmonyOS 系统识别
   - 解决方案：修改 configure 脚本，将 HarmonyOS 映射为 linux

2. **gen 目录依赖** (L2 构建模式)
   - suckless 项目依赖 gen/ 目录下的预生成文件
   - 解决方案：确保 gen/*.h 文件存在

---

**编译结束**: 2026-05-21 11:43
**最终状态**: built
---

**编译结束**: 2026-05-21 11:51
**最终状态**: built
