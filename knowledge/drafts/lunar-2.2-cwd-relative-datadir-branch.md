# 随包数据文件必须在消费者测试里被真正走到（相对路径打开的那类）

> Draft: `DRAFT-LUNAR-CWD-RELATIVE-DATADIR-BRANCH`
> Stem: `lunar-2.2-cwd-relative-datadir-branch` — 与同 stem 的 `.kv` 成对
> 实例：lunar 2.2（`archives/l/lunar/2.2`，PR !9xxx，`-b` bitmap 字形）

## 基本信息

- **ID**: `DRAFT-LUNAR-CWD-RELATIVE-DATADIR-BRANCH`
- **严重度**: 3（**假绿**——测试全通过，但一整条功能分支从未被执行）
- **类别**: test-design, packaging, coverage
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 问题：把"文件被安装了"当成"分支被覆盖了"

有一类经典 CLI 用**相对路径**打开自己的数据文件：

```c
/* lunar.c:144 */
char BMfile[] = "lunar.bitmap";
```

这意味着该功能**依赖进程 CWD**。同一类的还有：字库/字形表、拼写词典、时区表
（tzdata 消费者）、`terminfo`/`termcap` 条目、zone 文件生成器、翻译词表。

写 `test_package` 的常见形态是：

```python
def package(self):
    copy(self, "lunar.bitmap", src=self.source_folder,
         dst=os.path.join(self.package_folder, "share", "lunar"))

def test(self):
    self.run(f'"{test_exe}" "{bin_path}"')        # ❌ 测试进程 CWD = test_package 构建目录
```

于是被测程序在**构建目录**里找 `lunar.bitmap` → 找不到：

```
$ cd <test_package build dir> && lunar -b 2000 1 1
Lunar Version 2.2 (October 28, 2001)

Bitmap file 'lunar.bitmap' not found.
$ echo $?
1
```

**但测试依然全绿**——因为没人断言过这条分支。`package()` 的
`Packaged 1 '.bitmap' file` 只证明文件进了包，**不证明测试走到过它**。

更隐蔽的是它在开发机上"看起来能跑"：开发者习惯在源码目录里手工执行，
而 CI 的 CWD 完全不同。

## 方案：把包内数据目录作为参数传进去，用 `cd A && B` 切换

```python
# conanfile.py (test_package)
def test(self):
    pkg = self.dependencies["lunar"].package_folder
    bin_path = os.path.join(pkg, "bin", "lunar")
    data_dir = os.path.join(pkg, "share", "lunar")        # ① 包内真实安装位置
    test_exe = os.path.join(self.cpp.build.bindir, "test_lunar")
    self.run(f'"{test_exe}" "{bin_path}" "{data_dir}"')   # ② 作为 argv 传入
```

```c
/* test_lunar.c — ③ 依赖数据文件的用例用 shell 的 cd 语义切换 CWD */
if (g_data_dir && *g_data_dir)
    snprintf(cmd, sizeof(cmd),
             "cd \"%s\" && \"%s\" %s < /dev/null 2>&1",   /* 路径必须引号包裹 */
             g_data_dir, g_bin, args);
else
    snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", g_bin, args);
```

## 五个容易踩的细节

| # | 细节 | 原因 |
| --- | --- | --- |
| ① | **不要"把数据文件复制到测试 CWD"来绕过** | 那验证的是"文件可复制"，不是"包内安装位置正确"。包把数据装错目录时测试依然全绿 |
| ② | **用 `cd A && B`，不要 `chdir()`** | `chdir` 后不恢复会污染同进程后续用例的 CWD，且 `popen` 走 `/bin/sh -c`，子进程继承关系易误判 |
| ③ | **路径必须双引号包裹** | `package_folder` 是用户可控路径，可能含空格 |
| ④ | **断言不能只看退出码** | lunar bitmap 缺失时**打印 not found 并以 1 退出**——只断言退出码会漏掉这个降级路径 |
| ⑤ | **数据目录未提供时打印 SKIP 而不是静默跳过** | 保留可见性，避免"没跑"被误读成"跑过了" |

### 断言写法（④ 的落地）

```c
if (g_data_dir) {
    if (run_capture("-b 2000 1 1", buf, sizeof(buf)) < 0) {
        expect(0, "-b 调用未正常执行", "");
    } else {
        expect(strstr(buf, "not found") == NULL,
               "-b 能找到 lunar.bitmap 数据文件",
               strstr(buf, "not found") ? "报 'not found'，数据文件未随包安装" : "");
        expect(strlen(buf) > 32, "-b 产出非空位图输出", "");
    }
} else {
    printf("── 未提供数据目录，跳过 -b 用例\n");     /* ⑤ 显式打印 */
}
```

实测（包内 `share/lunar/lunar.bitmap`）：

```
── lunar -b 2000 1 1（bitmap 字形，需 lunar.bitmap）
  [PASS] -b 能找到 lunar.bitmap 数据文件
  [PASS] -b 产出非空位图输出
```

## 配套的 `package()` / `package_info()`

```python
def package(self):
    copy(self, "lunar.bitmap", src=self.source_folder,
         dst=os.path.join(self.package_folder, "share", "lunar"))

def package_info(self):
    self.cpp_info.bindirs = ["bin"]
    self.cpp_info.resdirs = ["share"]        # 声明 resdirs，消费者才知道去哪找
```

## 推广判据

> 凡是 `package()` 里往 `share/**` 装了数据文件，**且被测工具用相对路径读它**，
> 就必须有至少一条用例在数据目录内执行，并断言"没有 not found"。

只装了文件而没有在数据目录执行过的测试，等价于**没有测试**。

## 参考实现

- `archives/l/lunar/2.2/test_package/test_lunar.c`（argv[2] 传递数据目录）
- `archives/l/lunar/2.2/test_package/conanfile.py`（`dependencies[...].package_folder` → `share/lunar`）
