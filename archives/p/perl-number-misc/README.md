# Number::Misc

Perl 模块，提供数字处理的便捷工具函数，包括数字判断、字符串转数字、千分位格式化、零填充、范围随机数和奇偶判断。

## 功能概述

| 函数 | 说明 |
|------|------|
| `is_numeric($val)` | 判断标量是否为数字（支持 convertible 选项） |
| `to_number($str)` | 将字符串转换为数字（去除逗号和空格） |
| `commafie($num)` | 为数字添加千分位分隔符（支持自定义分隔符） |
| `zero_pad($num, $len)` | 将数字零填充到指定长度 |
| `rand_in_range($min, $max)` | 返回范围内的随机整数（支持数组上下文） |
| `is_even($num)` / `is_odd($num)` | 判断奇偶 |

遗留别名：`isnumeric`、`tonumber`、`zeropad`（无下划线版本）向后兼容。

## OHOS 适配

### 适配要点

- **纯 Perl 模块**：无 C/XS 代码，不需要编译器参与实际编译，原始源码无需任何修改即可在 OHOS 上编译运行
- **SELinux 兼容**：纯文本 .pm 文件不受 HMDFS SELinux 限制，可直接从用户目录加载（与 perl-dbd-pg 等 XS 模块不同，后者需要管理员安装到系统目录）
- **Conan 集成**：通过 `package_info()` 设置 `PERL5LIB` 环境变量，消费者 `conan install` 后 `source conanrun.sh` 即可使用
- **SSL 证书**：CPAN 下载可能遇到 SSL 证书验证失败，建议安装 `ca-certificates` 解决根因；如需临时绕过可使用 `curl --insecure` 仅限开发环境，下载后务必通过 sha256 校验确认文件完整性

### 已知问题

- `is_numeric('3,003')` 的 POD 文档示例标注返回 false，但实际实现返回 true（内部移除逗号后检查）。这是上游模块的文档/实现不一致，非平台适配问题，不影响功能使用。

## 依赖关系

- **编译依赖**：无（仅需 Perl 5.003+ 核心模块）
- **运行依赖**：无

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| [1.2](./1.2/) | built | 2026-06-29 | conan-verify 全门禁通过，功能测试 73 项全部 PASS |

## 参考资料

- [MetaCPAN - Number::Misc](https://metacpan.org/dist/Number-Misc)
- [CPAN 作者主页](https://metacpan.org/author/MIKO)
- 许可证：Perl 5 (同 Perl 本身)
