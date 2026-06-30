# libestr 0.1.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: published

## 补丁列表（仅 2 个必要补丁）

| 编号 | 文件 | 说明 |
|------|------|------|
| 0001 | config.guess.patch | OHOS 平台识别 (linux-ohos) |
| 0002 | config.sub.patch | OHOS 平台识别 |

原 19 个 autotools 生成文件补丁已清理（Makefile.in, config.h.in, ltmain.sh 等）。
`autoreconf -fiv` 重新生成这些文件，补丁无效。符合 R6 铁律。

**注意**: 系统 automake 的 config.guess/config.sub 已自带 OHOS 支持。保留 2 个补丁作为知识记录。

## 功能测试结果 (2026-06-03)

12组30项API测试: 29 PASS / 1 FAIL (es_str2num_hex 上游bug)

### 已知上游缺陷

**es_str2num_hex**: `tolower(c[i]) - 'a'` 缺少 `+10`。上游代码缺陷。

## 上库合规性

- ✅ 门禁 G1-G4 PASS
- ✅ 预编译包已制作+签名
- ✅ 补丁清理：19 → 2（R6/R23 铁律）

## 注意事项

- 纯库无可执行二进制，G2 ⚠️1 正常
- `autoreconf -fiv` bootstrap 需预先删除 `install-sh~`
- `install-sh~` 触发 automake BUG.am 虚警