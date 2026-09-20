# ondir 0.2.4：GitHub 无 tag 停更仓的官方源判定 + stdout-emitted 工具的功能测试设计

## 场景一：官方源判定（GitHub 仓无 tag 且停更）

alecthomas/ondir 的 GitHub 仓 2014 年后停更、**无 tag**（Homebrew
livecheck 注明 "doesn't tag versions"），`archive/refs/tags/v0.2.4.tar.gz`
返回 404（响应体仅 9-14 字节 "Not Found" 文本——对其取 sha256 写进
conandata 会在 CI source() 才暴露，属可预防错误）。

**判定与核验三步**：

1. 查 Homebrew formula 找真实官方源：
   ```
   curl -s https://raw.githubusercontent.com/Homebrew/homebrew-core/HEAD/Formula/o/ondir.rb
   # url "https://swapoff.org/files/ondir/ondir-0.2.4.tar.gz"
   # sha256 "52921cdcf02273e0d47cc6172df6a0d2c56980d724568276acb0591e0bda343a"
   ```
2. 下载官方站点 tarball，sha256 与 formula 声明**逐字符比对**——一致即
   事实源可信（Homebrew 有 bottle 构建，formula sha256 经过实机验证）。
3. conandata.yml 保留官方站点 URL 并注释核验来源/日期；网络不可达由
   conan-verify/CI 注入镜像处理（E017 预防），不写镜像 URL 进配方。

## 场景二：stdout-emitted 类工具的功能测试设计

ondir 的语义是 `ondir <old> [new]` 按 `~/.ondirrc` 的 enter/leave 正则
规则**把待 eval 的 shell 命令打印到 stdout**（由 shell 钩子 eval），
自身不执行、不产生文件副作用。因此功能测试必须**断言 stdout 文本**，
断言文件副作用（如 touch 后查文件存在）恒失败。

覆盖点（test_package/test.sh，7 项）：

- `-V` 版本输出（smoke）
- enter 规则触发 + `$ONDIRWD` 展开为被遍历路径
- leave 规则触发（old→/ 方向）
- POSIX 正则捕获组 `$1` 展开（`enter /odtest/rx/(.*)` → `got:xyz`）
- 无匹配规则时无输出（静默性）
- 鸿蒙特有：规则路径 `~/...` 经 `getenv("HOME")` 展开为绝对路径
  （`conf.c:95` 的 `tok[0]=='~'` 分支；HMFS /etc 只读且无 `/etc/ondirrc`，
  `$HOME/.ondirrc` 是唯一配置通道 → 该分支在 OHOS 上是实际生效路径）
- 鸿蒙特有：省略 `dst` 参数时经 OHOS bionic `getcwd()` 补全并退出码 0

## 场景三：反面教材——不要断言"二进制里有没有某个字面量"

最初把"鸿蒙特有"写成 `grep -q "/etc/ondirrc" "$BIN"`（断言编译期
`GLOBAL_CONF` 字面量被编进二进制）。该字面量**确实**在 `.rodata` 里
（编译期 `-DGLOBAL_CONF=\"…\"` 展开为字符串字面量；否则 conf.h 的
`#ifndef` 兜底会让 `load_conf(GLOBAL_CONF, root)` 变成 `/etc/ondirrc`
的除法表达式而编译失败），但 CI #44898 实测 OHOS 侧 grep 二进制取不到；
改 `tr -c '[:print:]' '\n' < "$BIN" | grep -q …` 仍取不到（#44xxx）——
toybox/bionic 的 grep 按"行"读且以 NUL 截断，而 `tr` 在该环境可能根本
不存在。

**结论**：鸿蒙特有/消费者断言只写**可观测的运行时行为**，不要扫二进制、
不要依赖 `tr`/`strings`/`grep -a` 这类不保证存在的工具；只用 shell 内建
与功能断言本来就需要的命令。

HMFS 两个约束：**/etc 只读** → `GLOBAL_CONF` 固化的 `/etc/ondirrc`
不可用，测试以 `HOME=<workdir>` 隔离写 `~/.ondirrc`；**/tmp 只读** →
shell here-doc 临时文件须 `TMPDIR=<workdir>` 重定向（与 ctemplate
CI #44037 同根因）。
