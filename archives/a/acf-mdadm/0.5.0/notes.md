# acf-mdadm 0.5.0 适配笔记

## 编译环境
- 构建系统: makefile (纯 Lua ACF 模块，无 C 编译)
- 编译日期: 2026-08-08
- 编译器: 无（纯 Lua/HTML 数据模块，无需编译器）
- 状态: built

## 编译步骤

1. 下载源码：Alpine distfiles 官方镜像 `https://distfiles.alpinelinux.org/distfiles/v3.24/acf-mdadm-v0.5.0.tar.gz`
   （上游 gitlab.alpinelinux.org 在构建网络被 HTTP 418 拦截）
2. 解压到 work 目录
3. 构建命令：
```bash
make -j1                    # all 目标为空（纯数据模块）
make install DESTDIR=$TEST_PREFIX
```
4. Makefile 仅 `cp -a mdadm*` 到 `$(DESTDIR)/usr/share/acf/app/mdadm/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gitlab.alpinelinux.org 下载返回 HTTP 418 | 构建网络拦截 gitlab（E017 同款网络限制） | 改用 Alpine distfiles 官方镜像（distfiles.alpinelinux.org），R39 官方源合规 |
| 2 | conan create 失败：acf-core/0.24.1 未发布到制品仓 | acf-core 是运行时框架，未发布（R36） | 移除 requirements()：纯数据模块构建无需 Conan 依赖 |
| 3 | W3 L0d 门禁 stub_test_method | test() 无 self.run() 调用被判空壳 | test() 增加 self.run() 检查模块文件存在且非空（R34/L0d） |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- 无 Conan 依赖（acf-core 为运行时框架，未发布到制品仓；本模块纯数据包无需构建依赖）

## 验证结果

```bash
$ make -j1
make: Nothing to be done for 'all'.   # 纯数据模块

$ make install DESTDIR=...            # 复制 mdadm* 到 share/acf/app/mdadm/
# conan-verify G0-G4 + L2/L4/L5 全部通过
# test_package：5 个 Lua/LSP 文件（controller/model/details-lsp/menu/roles）存在且非空
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/acf-mdadm-0.5.0-ohos-aarch64.tar.gz | 10,775 字节 | 模块文件打包（share/acf/app/mdadm/ 5 文件） |

## 注意事项

1. **ACF 模块为纯数据包**：无 C 编译、无二进制、无 make check 目标，test_package 用文件完整性验证代替（R34 满足）。
2. **gitlab.alpinelinux.org 被 418 拦截**：conandata.yml 必须用 Alpine distfiles 官方镜像作为源码源。
3. **无 bin/ 产物**：package_type=application 但仅暴露 share/acf/app 路径，无需 commands.json（R38 不适用）。
---

**编译结束**: 2026-08-08 22:24
**最终状态**: built
