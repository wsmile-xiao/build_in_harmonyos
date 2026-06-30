# portable-libyaml 0.2.5 适配笔记

## 编译环境
- 构建系统: cmake（替代 autotools）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

### Autotools 构建（失败）

1. 下载源码包：yaml-0.2.5.tar.gz (从 GitHub)
2. 修改 config/config.guess：添加 HarmonyOS 系统识别（E007）
3. 修改 config/config.sub：添加 ohos 三元组验证（E072）
4. 执行 configure --prefix=$DEFAULT_PREFIX
5. ❌ 失败：SELinux 限制导致 config.status 无法创建临时文件

### CMake 构建（成功）

1. 创建简化版 CMakeLists.txt（原版不完整）
2. 创建 include/config.h.in 模板
3. 定义 HAVE_CONFIG_H 编译宏
4. cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
5. make -j2
6. make install DESTDIR=$TEST_PREFIX（staging 验证）
7. make install（安装到本地）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 2018-02-24 版本不包含 HarmonyOS 支持 | 添加 `*:HarmonyOS:*:*)` case 分支（E007） |
| 2 | config.sub 无法验证 ohos 三元组 | config.sub 缺少 ohos 相关验证规则 | 修改 4 处验证规则（E072） |
| 3 | **config.status 权限拒绝** | SELinux/文件系统限制（E046） | 使用 CMake 构建系统替代 |
| 4 | **CMakeLists.txt 不完整** | 原版 CMakeLists.txt 缺少必要配置 | 创建简化版 CMakeLists.txt + config.h.in |

## 验证结果

```bash
# CMake 构建产物
$ ls ~/usr/local/lib/libyaml.a
142472 bytes

$ ls ~/usr/local/include/yaml.h
54439 bytes

# 功能验证
$ clang test_yaml.c -lyaml -o test_yaml
$ ./test_yaml
libyaml version: 0.2.5
```

## 预编译包

- 文件：portable-libyaml-0.2.5-ohos-aarch64.tar.gz (200KB)
- 内容：lib/libyaml.a, include/yaml.h
- 安装：curl install.sh | sh -s -- portable-libyaml 0.2.5

---

**编译结束**: 2026-06-17 15:10
**最终状态**: published