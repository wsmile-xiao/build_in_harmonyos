# daa2iso 0.1.7e 适配笔记

## 上游信息
- 上游作者: Luigi Auriemma（aluigi.altervista.org，个人工具集）
- 功能: Direct Access Archive (.daa) / GBI 镜像 → ISO 转换
- 形态: 纯 C 命令行工具，3 个 C 文件 + 自带 src/Makefile

## 源码获取
上游站点在 CI worker 上不可达。改用 **Debian pool 的 orig.tar.gz**：
```
https://deb.debian.org/debian/pool/main/d/daa2iso/daa2iso_0.1.7e.orig.tar.gz
sha256 = d304428eb40106fe38039ed796f2c0059991c453190d89ff108e8b78d3796b9b
```
`deb.debian.org` 在 worker 可达（CI 镜像列表已覆盖该主机）。

## 编译
```
clang -O2 -Wall -fcommon -c src/LzmaDec.c  -o src/LzmaDec.o
clang -O2 -Wall -fcommon -c src/tinflate.c -o src/tinflate.o
clang -O2 -Wall -fcommon src/daa2iso.c src/LzmaDec.o src/tinflate.o -o src/daa2iso
```
- 不使用 Makefile：其内容就是上面三步（外加 `-s` strip），直接驱动 clang 减少一层依赖。
- `-fcommon`：`LzmaDec.c` / `tinflate.c` 为 7-Zip 与 zlib 的内嵌副本，含老式 C 的
  tentative definition，多 TU 链接时在新 clang 下会报重复定义，`-fcommon` 恢复旧语义。
- 无外部依赖，`DT_NEEDED` 仅 `libc.so`。

## 运行验证
- 无参数执行 → 打印
  `Usage: <bin> <input.DAA/GBI> <output.ISO>` 后走 `myexit()` 的预期错误路径。
- 真实转换需要 .daa 样本，不在本 PR 范围（消费者测试只断言可执行性与 usage 输出）。

## 测试（test_package，5 条断言）
1. `bin/daa2iso` 存在
2. `bin/daa2iso` 可执行
3. ELF64 / AArch64（e_machine == 0xB7）
4. 真实执行未被信号杀死、退出码不在 {126,127,255}（非加载失败）
5. 无参数输出含 `Usage`

**注意**：断言全部用 `popen` 直读子进程输出，**不落盘到 /tmp**（OHOS 上 /tmp 只读，
写中间文件会让 grep 找不到文件而误报）。
