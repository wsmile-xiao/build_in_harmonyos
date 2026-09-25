# jgraph 83 适配笔记

## 编译环境

- 构建系统: makefile（上游 POSIX makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: ohos-sdk clang 15.0.4（aarch64-linux-ohos，Conan profile `ohos-aarch64`）
- 目标平台: HarmonyOS PC / aarch64（设备内核 1.12，HAD-W32）
- 状态: built

## 编译步骤

```bash
# 1. 取源码（.orig 保持原样，.work 为可编辑副本）
python3 scripts/ohc-run.py init-build jgraph 83 \
  --url=https://deb.debian.org/debian/pool/main/j/jgraph/jgraph_83.orig.tar.gz

# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight jgraph 83 --src "$BUILD_SRC_DIR"

# 3. 在 .work 中修改源码（10 个文件），然后生成补丁（R3，refresh-patch --auto）
python3 scripts/ohc-run.py track-edit scan jgraph 83
python3 scripts/ohc-run.py refresh-patch --auto jgraph 83

# 4. Conan 配方验证（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify jgraph 83 --profile ohos-aarch64-device

# 5. 本地 CI 模拟（与平台 CI 同脚本）
export CONAN_PROFILE=ohos-aarch64-device
export CI_PACKAGES="archives/j/jgraph/83"
export CI_REPO_ROOT="$PWD"
zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

`make` 的调用方式（conanfile.py `build()`）：`make -j1 CC="<profile 里的 clang>"`
（R33：编译器来自 Conan conf，不裸用 shell 变量）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 编译报 46 处 `error: non-void function 'X' should return a value` | 1997 年 K&R 风格：过程用裸 `return;`，但函数无返回类型声明（隐式 `int`）；clang 15 将 `-Wreturn-type` 判为错误 | 按上游 8.5（2017）与 Debian 83-26 的做法，把 23 个过程改为 `void`（补丁 0001/0002/0006/0007/0008/0009/0010） |
| 2 | 改 `void` 后同文件内"先调用后定义"报 `conflicting types` | 调用处生成隐式 `int` 声明，与后面的 `void` 定义冲突 | 在 jgraph.h 末尾补 21 个现代 void 过程的前置声明（补丁 0003） |
| 3 | 编译通过但**任何输入都立即 SIGSEGV** | `jgraph.h` 仅在 `-DLCC` 时包含 stdlib.h；`malloc`、`get_node`、`make_list` 被隐式声明为返回 `int`，aarch64 上指针被截断为 32 位；`draw.c` 的 `asin/cos/sin/log`、`token.c` 的 `atof` 同理（浮点被当 int 读） | jgraph.h 无条件包含 stdio/stdlib/string/math；list.h 声明 `make_list/get_node/insert/delete_item/free_node`；token.c/list.c 补 stdlib/string（补丁 0003/0004/0005/0010） |
| 4 | 截断的 EPS `%%BoundingBox`（少于 4 个整数）不报错，产生垃圾缩放 | `fscanf(...) == NULL`：`fscanf` 返回 `int`，与 `NULL` 比较恒为假（EOF=-1 时不进入错误分支） | 改为 `fscanf(...) != 1`（上游 2007 快照同款修复，补丁 0001）；测试用例 `eps-bad.eps` 验证必须报 `eof in bounding box` 退出 |
| 5 | `jgraph -L`（landscape、无 -P）的整页平移输出随机数字 | `printf("%f 0 translate\n", -gs->bb[2] - gs->bb[0])` 把 `int` 传给 `%f`；aarch64 可变参数 ABI 下浮点寄存器里是垃圾值 | 显式 `(double)` 转换（Debian 83-26 同款修复，补丁 0001）；测试用 `-bb[2]-bb[0]` 精确校验 |
| 6 | 官网已下架 83 tarball（`jgraph-83.tar.gz`/`jgraph-8.3.tar.gz` 均 404） | 上游主页现在只提供 8.4-8.6 线（2024-02-15-Jgraph.tar） | 使用 Debian 83-26 的 orig tarball：jgraph.c/man 页与官网 2007 快照逐字节相同（README `$Revision: 8.3 $`），`.dsc` Checksums-Sha256 记录同一哈希（e413b98a…546，109419 字节） |

## 源码修改

补丁由 `refresh-patch --auto`（R3）生成，共 10 个文件：

| 补丁 | 内容 |
|------|------|
| `0001-draw.c.patch` | 4 个过程改 `void`；EPS BoundingBox EOF 检测 `!= 1`；landscape 平移转 `double` |
| `0002-edit.c.patch` | 8 个过程改 `void` |
| `0003-jgraph.h.patch` | 无条件包含 stdio/stdlib/string/math；补 24 个 void 过程前置声明 |
| `0004-list.c.patch` | 补 stdlib.h；`insert/delete_item/free_node` 改 `void` |
| `0005-list.h.patch` | 声明 `make_list/get_node/insert/delete_item/free_node` |
| `0006-printline.c.patch` | `setfill/print_label` 改 `void` |
| `0007-prio_list.c.patch` | `prio_insert` 改 `void` |
| `0008-process.c.patch` | `process_legend/process_label/process_label_extrema` 改 `void` |
| `0009-show.c.patch` | `show_label/show_lmark/show_axis` 改 `void` |
| `0010-token.c.patch` | 补 stdlib.h/string.h；`get_comment/nexttoken` 改 `void` |

补丁中无 `__OHOS__` 平台宏、无 `usr/local`/SYS_PREFIX 注入（PF5/PF6 语义），
全部是 POSIX/标准 C 兼容化修改。

## 依赖版本

无第三方依赖（libc + libm）。`requirements()` 有意留空。

## 验证结果

```bash
# 上游示例回归（.orig 原始输入，逐字节未改）
$ for f in *.jgr; do ./jgraph -P < $f > /dev/null; done
20/21 通过；唯一失败 ad.jgr 依赖同目录示例先生成 cube.eps 与 disk.eps
（makefile 规则 `ad.jps: cube.eps disk.eps`），两个 .eps 都生成后 ad.jgr 也通过
（23574 字节输出）—— 属示例间依赖，非代码问题

# 消费者测试（test_package/test_jgraph.sh，25 断言）
$ bash test_jgraph.sh
25 passed, 0 failed

# 关键行为抽查
$ ./jgraph -p < simple.jgr | grep '^bbox'
bbox -27 -45 219 219
$ ./jgraph -L < simple.jgr | grep -m1 ' 0 translate'
-192.000000 0 translate        # = -bb[2]-bb[0] = -219-(-27)，修复前为垃圾值
$ ./jgraph -P < eps-bad.jgr; echo rc=$?
Error: Eps file 'eps-bad.eps': eof in bounding box
rc=1                          # 修复前不报错
$ printf 'bogus_keyword\n' | ./jgraph -P; echo rc=$?
<stdin>,1: Bad token: bogus_keyword
rc=1
```

`conan create`（G0-G4 + L2/L4/L5）与本地 CI 门禁（L0/L1/L1e/L2/L5）结果见
`reports/test-report.md` 与 `.ci-result.json`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/jgraph` | 命令行工具（aarch64 ELF，PIE + RELRO） |
| `share/man/man1/jgraph.1` | 上游 man 页（原样安装） |

## 注意事项

- 上游 83 的 tarball 在官网已 404，本配方固定使用 Debian 83-26 orig tarball
  并锁 sha256；如上游重新发布 83，可换回官方 URL（哈希需一致）。
- `jgraph` 不提供 `--version`/`--help`（非选项参数被当作输入文件名），
  CI L2 smoke test 对其会记非阻塞 warn；真实功能由消费者测试覆盖。
- 编译仍有 31 条告警（K&R 非原型定义、部分内部函数的隐式声明、个别格式串），
  均为上游 1992 年代码风格遗留；本适配的补丁只消除错误与 64 位截断/UB 问题，
  未整体改写为原型式定义（上游 8.4-8.6 才做该重构），以保持补丁面最小。
- 设备 `/tmp` 只读：本工具不写任何临时文件，无影响。

---

**编译结束**: 2026-09-21 20:10
**最终状态**: built
