# ckon

**ROOT 数据分析程序的自动构建工具**（来自 tschaume，MIT 许可）

ckon 面向 CERN ROOT 框架的数据分析项目：自动处理程序与库的编译、字典生成（ROOTCINT/基 CINT）和链接。它读取 `ckon.cfg` 配置，扫描 `src_dir` 下的包目录，生成并驱动 CMake 构建或安装流程，支持 `setup`/`clean`/`install`/`dry` 等子命令。

## 用法

```bash
ckon --version       # 打印版本号
ckon --help          # 显示用法
ckon setup           # 初始化示例项目结构
```

## 上游

- 主页: https://github.com/tschaume/ckon
- 许可证: MIT
- 构建: Autotools（发布 tarball 无预生成 configure，需 autoreconf -fi）
- 依赖: boost（filesystem/regex/program_options）+ libcurl
