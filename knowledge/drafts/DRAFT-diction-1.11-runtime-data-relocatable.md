# DRAFT: autotools 包运行时数据目录不可迁移（configure 期烧入 SHAREDIR）

## 来源

diction 1.11 适配（HarmonyOS PC / aarch64，2026-09-10）。

## 现象

diction 的短语库安装在 `share/diction/`（`C`、`de`、`en`、`en_GB`、`nl`），
二进制在 configure 阶段被写入 `-DSHAREDIR=\"${prefix}/share\"`（见 `Makefile`：
`CPPFLAGS= ... -DSHAREDIR=\"${prefix}/share\" -DLOCALEDIR=\"$(localedir)\"`），
运行期只使用该编译期绝对路径：

```
diction: Opening '<configure 前缀>/share/diction/en' failed (No such file or directory).   [exit 1]
```

适配/打包后包会被安装到任意位置（Conan 缓存 hash 目录、用户自定义 prefix、制品仓解包目录），
编译期绝对路径必然失效，故 `conan create` 的 test_package 阶段（以及真实用户使用）会失败。

## 处理

补丁 `0005-diction.c.patch` 把运行时短语库目录改为**相对可执行文件查找**：

1. `readlink("/proc/self/exe", ...)` 取自身路径 → 去掉 `/bin/<exe>` → 拼 `/share/diction/<lang>`；
2. 未命中时回退编译期 `SHAREDIR`（保证开发树内直接运行仍可用）；
3. **关键细节**：`readlink` 返回长度但不写 NUL 终止符，静态缓冲区会残留上一次调用的字节，
   导致路径错乱（实测 `DBG computed='.../tmp-d2/share/diction/'` 之类错误拼接）；必须显式 `buf[n]='\0'`。

配方侧配合：`generate()`/`build()` 中 `--prefix={self.package_folder}`，使回退路径与安装布局一致。

## 验证

- 搬迁测试：把安装树移动到另一目录，直接运行默认查找路径（不传 `-f`/`-n`）仍能标记短语：
  `printf 'In order to test this, we need a case.\n' | diction` → `[In order to] ... [case]` + `2 phrases in 1 sentence found.`
- 消费者测试：`test_package/test_diction.sh` 校验 `share/diction/en` 随包安装且走默认查找路径（4 项断言）。

## 适用范围

同类模式（运行时数据目录在 configure/build 阶段被烧进二进制）在 autotools 包中很常见：
`SHAREDIR`/`LOCALEDIR`/内置插件目录/字体与模板路径等。判断方法：安装树搬迁后运行 CLI 默认路径是否报
`Opening '<compile-time prefix>/...' failed`。
