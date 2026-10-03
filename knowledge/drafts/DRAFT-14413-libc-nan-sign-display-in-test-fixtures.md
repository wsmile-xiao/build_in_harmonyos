# DRAFT-14413: libc printf 显示负 NaN 为 "-nan" 造成上游期望文件比对失败

- **来源**：tomlc99 0.0-git20260130 适配（2026-10-03，j669539）
- **领域**：libc 显示层差异（musl/glibc vs 旧 glibc 期望文件）× 测试比对
- **邻近但不同**：E151（musl 检测宏 HAVE_DECL_ISNAN）、E047（HMDFS 权限断言）——均非 NaN 显示主题，图谱未命中

## 现象

上游回归测试用 `printf("%f")` 打印 double、期望文件逐字节比对（tomlc99 的
stdex/：`../toml_cat $i >& $i.out` 再 `diff $i.out $i.res`）。在 OHOS/musl 及
glibc >= 2.23 上：

```
stdex: float6.toml [FAILED]
7c7
<   sf6 = -nan,          ← 实际输出（toml_cat）
>   sf6 = nan,           ← 期望文件（.res，旧 glibc 行为记录）
```

其余 61 个样例全部字节精确通过；只有含 `-nan` 字面量的样例失败。

## 根因

**显示层 implementation-defined 差异，不是解析缺陷**：

1. `strtod("-nan")` 在 musl/glibc 上都成功返回带符号位 NaN（signbit=1），解析
   路径 ok=1、位模式正确；
2. `printf("%f")` 家族对负 NaN 的文字表示是 implementation-defined：musl 与
   glibc >= 2.23 打印 `-nan`，旧 glibc（< 2.23）打印 `nan`；
3. 上游 .res 期望文件以旧行为记录 `nan`；
4. TOML v1.0.0 规范自己声明该差异不可判定——float6.toml 源码注释原文：
   `sf6 = -nan # valid, actual encoding is implementation-specific`。

即：规范层面承认、libc 层面各异、库行为正确、纯显示层 token 差一个符号。

## 修复（比对 harness 归一化，双侧）

```python
_NAN_SIGN_RE = re.compile(r"(?<=[\s=,])[-+]nan\b")

def _normalize_nan_display(text):
    return _NAN_SIGN_RE.sub("nan", text)

# 三态比对：字节精确 → NaN 符号归一化 → 失败
if actual_raw == expected_raw:
    byte_exact += 1
elif _normalize_nan_display(actual_raw) == _normalize_nan_display(expected_raw):
    normalized_only += 1
    print(f"{base} [OK] (NaN sign display normalized)")
else:
    failures.append(base)
```

要点：
- **双侧归一化**（期望侧也可能记的是新行为，统一到 `nan` 基准）
- **保留 raw 计数**：输出 "61 byte-exact, 1 NaN-sign-normalized"，逐例打印，nothing hidden
- **不改上游 .res、不改被测库源码**：上游测试零修改原则不被破坏

## 验证

tomlc99 0.0-git20260130 本地 conan create（HarmonyOS PC aarch64 原生真跑）：
stdex 62/62 通过（61 字节精确 + 1 归一化）；反向验证：去掉归一化分支 float6
稳定 FAIL（证明 harness 对该差异敏感、非空壳）。

## 红线

- **禁止改上游期望文件**（把 .res 的 `nan` 改成 `-nan`）——那等于篡改上游测试
  基线，PR 审查必打回，且换了 libc 又会反过来挂
- **禁止把整个比对改成 contains/宽松匹配**——只归一化 NaN 符号 token，其余
  逐字节严格，否则真回归会被吞掉
- 若框架不支持改 harness，则按"libc 显示 implementation-defined"做单例定性
  豁免并在统计表逐项注明，不静默跳过
