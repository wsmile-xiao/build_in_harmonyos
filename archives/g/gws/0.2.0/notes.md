# gws 0.2.0 适配笔记

## 编译环境
- 构建系统: custom (bash script)
- 编译日期: 2026-07-16
- 编译器: 不适用（纯 bash 脚本）
- 状态: built

## 编译步骤
1. 下载源码：https://github.com/StreakyCobra/gws/archive/refs/tags/0.2.0.tar.gz
2. 编写 conanfile.py（package_type=application，直接复制脚本和补全文件）
3. 运行 conan create 验证
4. 运行 finish 归档

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py init-build 错误将 packaging/debian 提升为源码 | 嵌套打包脚本误判 | 手动下载源码，将正确文件复制到 work 目录 |
| 2 | conanfile.py 模板生成 autotools 配方 | gws 是 bash 脚本，不需要编译 | 重写为 custom 类型，直接复制文件 |
| 3 | package() 中 Conan copy() 失败 | Conan 2 package 阶段 source_folder 路径问题 | 改用 shutil.copy2 |

## 源码修改
无（无需补丁）

## 依赖版本
- Conan: 2.29.1
- bash: 5.3.15（运行要求）

## 验证结果
```
# Conan 创建验证
conan create archives/g/gws/0.2.0 --user=ohpcd --channel=stable
# 结果：G1/G2/G3 全部通过
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码数据 |
| test_package/ | 测试包 |

## 注意事项
- gws 是纯 bash 脚本，无 C/C++ 代码，无需交叉编译
- 依赖：bash >= 4.0, git

## 最终状态
- 编译状态: built
- 补丁: 0 个
- 测试包: test_package/ 已配置
- 归档路径: archives/g/gws/0.2.0/
