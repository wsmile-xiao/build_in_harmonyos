# bootstrap 0.0.1 适配笔记

## 编译环境
- 构建系统: custom (pure JavaScript, no compilation)
- 编译日期: 2026-09-01
- 编译器: clang (仅占位，实际无需编译)
- 状态: built

## 上游信息
- 名称: bootstrap 0.0.1 — Bootstrap your node app with some great defaults
- 作者: Andrew Gertig (andrew.gertig@gmail.com)
- 主页: http://github.com/AndrewGertig/bootstrap
- 仓库: git://github.com/AndrewGertig/bootstrap (已归档，现通过 npm registry 分发)
- 许可证: MIT
- 源码: https://registry.npmjs.org/bootstrap/-/bootstrap-0.0.1.tgz
- SHA256: 1ed241799b1f706f2b77aae3e4ef2eab2aa607e0f4f64169e68e4cea2d5d778a
- 内容: package/package.json + package/bin/bootstrap + package/.gitignore (3 files, 3207 bytes)

## 编译步骤
```bash
# 解压 npm tarball (含 package/ 前缀)
tar xzf bootstrap-0.0.1.tgz
# 无需编译，直接拷贝
mkdir -p $PREFIX/bin
cp -a package/bin/bootstrap $PREFIX/bin/
cp package/package.json $PREFIX/
chmod +x $PREFIX/bin/bootstrap
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | npm tarball 含 package/ 前缀 | npm 打包规范 | conan get strip_root=True 自动剥离前缀 |
| 2 | bin/bootstrap 依赖 Node.js 与 commander | 原生 JS CLI，非 C 库 | 配方标记为 application，运行期需 Node.js；test_package 静可静态校验文件，动可用 node 执行 |
| 3 | 上游无测试套件 | 0.0.1 为早期占位版本 | MANIFEST 中声明 upstream_tests_exist: false 并审计说明，补充消费者烟雾测试 |
| 4 | shebang 为 #!/usr/bin/env node | OHOS Node 路径不固定 | 保留原样，依赖 env 解析；OHOS 适配无需改路径 |

## 验证结果
```bash
bootstrap --help  # 需 Node.js，输出包含 --sessions/--jade 选项
cat $PREFIX/bin/bootstrap | grep "program.version('0.0.1')"  # ✅ 静态校验
cat $PREFIX/package.json | grep '"version": "0.0.1"'  # ✅
```

## 注意事项
- 本包为纯 JS 工具，无 C/C++ 库产出，cpp_info.libs 为空，bindirs 为 ["bin"]
- 运行依赖 Node.js >=0.4.8 及 commander 模块；HarmonyOS 消费侧需自行提供 Node 环境
- 无需 OHOS 补丁，适配路径为基础适配 (路径 A)

---

**编译结束**: 2026-09-01
**最终状态**: built
