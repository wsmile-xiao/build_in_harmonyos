# bootstrap — OpenHarmony 编译档案

## 软件简介
bootstrap 0.0.1 是 Andrew Gertig 的 Node.js Express 应用生成器，用于快速初始化 Express 项目骨架。生成文件包含 Express 应用模板、视图模板 (EJS/Jade) 及基础样式。

## OHOS 适配要点
- 纯 JavaScript 工具，无需编译，仅文件拷贝
- npm 打包含 `package/` 前缀，`conan get strip_root=True` 自动处理
- 可执行文件 `bin/bootstrap` 依赖 Node.js 及 `commander` 模块
- 上游无测试套件，采用消费者烟雾测试校验

## 依赖关系
- 运行期依赖: Node.js >=0.4.8, commander (未打包，宿主环境提供)
- 无编译依赖

## 参考资料
- [npm 仓库](https://www.npmjs.com/package/bootstrap)
- [源码 tarball](https://registry.npmjs.org/bootstrap/-/bootstrap-0.0.1.tgz)
- [GitHub (归档)](https://github.com/AndrewGertig/bootstrap)
