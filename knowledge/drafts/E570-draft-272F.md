# E570 — 老 CLI 工具只登记短选项，CI 的 --version/--help 冒烟测试失败

## 错误特征
```
<tool>: unrecognized option '--version'
<tool>: unrecognized option '--help'
```
或者更隐蔽的形态：工具自己打印 usage 并 `exit 1`（上游 usage() 分支），
CI 冒烟门禁据此判定「可执行产物未通过冒烟」。短选项 `-v`/`-h` 却是正常的。

## 触发条件
- 阶段: 测试（CI 的 L2 冒烟 / 消费者测试）
- 对象: 2000 年代只用 `getopt` 登记短选项的 C/C++ 命令行工具
- 依赖: CI 冒烟与多数自动化脚本按 GNU 习惯使用长选项 `--version` / `--help`

## 根因分析
`getopt` 的长选项支持在 `getopt_long`（GNU 扩展）里；老工程普遍只写
`while ((c = getopt(argc, argv, "ho:qv")) != -1)`，未知选项（包括 `--version`）会走
`default:` → `usage()` → 非零退出的路径。于是交叉编译产物虽然可用，但门禁判定失败。
这不是平台缺陷而是上游接口能力问题，补丁应当补齐接口而不是改门禁。

## 解决方案

### 推荐方案
把选项解析换成 `getopt_long`，把长选项映射到既有短选项分支（保持原行为不变），
并同步在 usage 文本里补上长选项说明：
```c
static const struct option long_options[] = {
    { "help",    no_argument,       NULL, 'h' },
    { "version", no_argument,       NULL, 'v' },
    { "output",  required_argument, NULL, 'o' },
    { 0, 0, 0, 0 }
};
while ((c = getopt_long(argc, argv, "ho:qv", long_options, NULL)) != -1) { ... }
```

### 禁止做法
- ❌ 在 CI/测试里把 `--version` 改成 `-v` 绕过（门禁接口是 GNU 约定，改测试等于掩盖问题）。
- ❌ 长选项与短选项行为不一致（例如 `--version` 退出码或输出与 `-v` 不同），会造成后续脚本误判。

## 验证
```bash
bin/<tool> --version && echo RC_OK        # 退出码 0，输出含版本号
bin/<tool> --help | grep -q 'Usage' && echo HELP_OK
```

## 关联条目
- 相关: E194（musl 头文件下老代码的移植阻塞点，同属「老代码 + 新工具链」类问题）
