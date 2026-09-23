# DRAFT-E650 — 上游 meson test 注册的无参测试条目是空跑假绿面

- 软件实证：mustach 1.2.10（gitlab.com/jobol/mustach）
- 阶段：conan build() 内上游测试（meson test / make test 双路径）
- 日期：2026-09-21

## 现象

meson test 对 mustach 1.2.10 注册 11 个条目：`tool test1`…`tool test8` 与
`specs cjson` / `specs json-c` / `specs jansson`。meson test 全部 Ok。但读
`test-specs/test-specs.c` 的 `main()`：

```c
int main(int ac, char **av)
{
        ...
        while (*++av) {            /* 空参数表 → 循环体零次 */
                ...
        }
        fprintf(output, "\nsummary:\n");
        ...
        fprintf(output, "  success %u\n", c.nsuccess);   /* 0 */
        ...
        return 0;                                         /* 退出码 0 → PASS */
}
```

`meson.build` 的注册形态（无 args）：

```meson
e = executable(value['xxx'] + '-test-specs', [...])
test('specs ' + value['xxx'], e)      # 无 args！
```

即三条 spec 条目以空 argv 运行：输出 summary 全 0、退出码 0、meson 显示
Ok——**一个 spec 用例都没有执行**。真实覆盖在上游 Makefile 路径：

```make
test-specs/test-specs-%: test-specs/%-test-specs test-specs/specs
        ./$< test-specs/spec/specs/[a-z]*.json > $@.last || true
        diff $@.ref $@.last
```

## 判据（如何识别同类问题）

1. `meson test -C <build> -v "<条目名>"` 的输出以
   `summary:` + `error 0` / `differ 0` / `success 0` 结尾 ⇒ 空跑。
2. 读被注册可执行文件的 `main()`：空参数表是否宽容返回 0。
3. 读 `meson.build` 的 `test(...)` 是否带 `args:`；带数据的 runner 无 args 注册
   即嫌疑。

## 处置

- 采信数字分两级：框架注册数（11）≠ 真跑数（8 工具测试真跑 + 3 spec 空跑）。
  空跑条目不得计入 N′，也不得写成「11/11 全部真跑」。
- 真实 spec 覆盖走 Makefile 带参路径：克隆 mustache/spec v1.4.1 到
  `test-specs/spec` 后逐后端运行并 `diff` 官方 `.ref`（在真机采信轮执行，
  CI 构建保持封闭不克隆外部数据仓）。

## 设备可直接执行的复现命令

```sh
# 在解包的 mustach-1.2.10 源码根目录（构建产物已生成的前提下）：
meson test -C <build_dir> -v "specs cjson" 2>&1 | tail -6
# 输出 summary 三行全为 0 即命中本条
```
