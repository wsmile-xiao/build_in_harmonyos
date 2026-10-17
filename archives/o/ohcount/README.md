# ohcount

源代码行数统计与编程语言检测工具（source code line counter and language detector）。

- 上游仓库: https://github.com/blackducksoftware/ohcount
- 许可证: MIT
- 适配版本: 3.1.1（archives/o/ohcount/3.1.1）、4.0.0（archives/o/ohcount/4.0.0）
- 构建系统: custom（上游 bash build 脚本编译/链接方式，配方直接编译）
- 依赖: pcre/8.45、libmagic/5.48（均已发布 ohpcd）

## 使用

```bash
ohcount <文件或目录>        # 统计语言分布与代码行数
ohcount --help
```

示例输出（`ohcount fixture.c`）：
```
c 1 4 5 1 10
```
（文件数 1、代码 4、注释 5、空白 1、总行 10）

## 适配要点（3.1.1）

- 官方 tarball 不含 Ragel/gperf 生成产物，配方携带预生成纯文本源码
  （`generated/`，ragel 6.10 + gperf 3.1 在设备端生成）
- 7 个补丁：TMPDIR 可移植性（diff.c/sourcefile_test.h）、size_t 64 位安全
  （parser.c/languages.h）、上游测试聚合器补挂与 golang 语言名笔误修复
- 上游 C 套件 529/529 通过，鸿蒙专项测试 10/10 通过
