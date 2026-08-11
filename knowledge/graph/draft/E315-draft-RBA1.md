# E315: HarmonyOS 权威时区契约：param 服务 + R internal zoneinfo + TZDIR 候选优先级

> **Contributor**: RBA1 | **Status**: DRAFT | **Created**: 2026-08-09
> **Severity**: medium | **Category**: runtime-capability

## 错误特征

R 4.5.1 在 HarmonyOS 上调用 `Sys.timezone()` 时无法正确返回设备本地时区，或在 `as.POSIXct()` / `as.POSIXlt()` 转换时使用错误的时区偏移。具体表现为：

- `Sys.timezone()` 返回空字符串或 NA。
- `as.POSIXct("2026-01-01 00:00:00")` 的结果与设备系统时间不一致。
- 日志中出现 zoneinfo/localtime 相关的查找失败信息。

## 触发条件

1. HarmonyOS 设备不通过传统 `/etc/localtime` 符号链接暴露权威本地时区。
2. R 的 `datetime.R` 中 `Sys.timezone()` 函数按传统 Linux 发现链查找时区：先检查 `/etc/localtime` 是否为符号链接，再检查 `/etc/timezone`、`/etc/TIMEZONE` 等文件。
3. HarmonyOS 的时区信息通过系统 parameter 服务暴露：`/usr/bin/param get persist.time.timezone` 返回 `Asia/Shanghai`（权威 IANA 名称）。
4. 系统 `/system/etc/zoneinfo/tzdata` 为 OpenHarmony 打包格式，不是 R 可直接遍历的 Olson 目录。
5. `/etc/zoneinfo` 目录虽存在，但没有 `Asia/Shanghai` 展开文件，会遮蔽 R internal zoneinfo。
6. R 官方源码自带 `src/extra/tzone/zoneinfo.zip`（含 `zoneinfo/Asia/Shanghai`），是版本固定的 IANA 数据库。

## 根因分析

HarmonyOS 的时区架构与传统 Linux 有三点关键差异：

1. **权威源不同**：Linux 通过 `/etc/localtime` → `/usr/share/zoneinfo/Asia/Shanghai` 的符号链接暴露本地时区；HarmonyOS 通过 `param get persist.time.timezone` 返回 IANA 名称字符串。
2. **zoneinfo 格式不同**：Linux 的 `/usr/share/zoneinfo/` 是展开的 Olson 目录（每个时区一个文件）；HarmonyOS 的 `/system/etc/zoneinfo/tzdata` 是 OpenHarmony 打包格式，R 无法直接遍历。
3. **遮蔽问题**：`/etc/zoneinfo` 目录在 HarmonyOS 上存在但内容不完整（缺少 `Asia/Shanghai` 展开文件），若其优先级高于 R internal zoneinfo，会遮蔽有效数据源。

因此需要在 R 的时区发现逻辑中插入 HarmonyOS 专用探测块，并通过 `--with-internal-tzcode` 启用 R 自带的 IANA 数据库。

## 解决方案（含验证）

### 推荐方案：authoritative param probe + TZDIR 候选优先级（补丁 0003）

补丁 0003 在 `datetime.R` 的 `Sys.timezone()` 中，传统发现链前插入 HarmonyOS 专用探测块：

```r
if(nzchar(param <- Sys.which("param"))) {
    tz0 <- try(system2(param, c("get", "persist.time.timezone"),
                      stdout = TRUE, stderr = FALSE), silent = TRUE)
    if(!inherits(tz0, "try-error") && length(tz0) == 1L) {
        tz <- trimws(tz0)
        if(nzchar(tz)) {
            tzdirs <- c(file.path(R.home("share"), "zoneinfo"),
                        Sys.getenv("TZDIR"),
                        "/usr/share/zoneinfo", "/share/zoneinfo",
                        "/usr/share/lib/zoneinfo", "/usr/lib/zoneinfo",
                        "/usr/local/etc/zoneinfo", "/etc/zoneinfo",
                        "/usr/etc/zoneinfo")
            tzdirs <- unique(tzdirs[nzchar(tzdirs)])
            matches <- tzdirs[file.exists(file.path(tzdirs, tz))]
            if(length(matches)) {
                Sys.setenv(TZDIR = matches[1L])
                cacheIt(tz)
                return(tz)
            }
        }
    }
}
```

关键设计点：

1. **param 探测**：仅当 `param` 命令存在时执行 `param get persist.time.timezone`，返回单一非空 IANA 名称。
2. **TZDIR 候选优先级**：按 "R internal zoneinfo → 显式 TZDIR → 标准系统目录" 的顺序，仅选择真实包含该 IANA 文件的候选目录。
3. **写入 TZDIR**：将选中目录写入 `TZDIR` 环境变量，供后续 `as.POSIXct()` / `as.POSIXlt()` 使用。
4. **缓存**：调用 `cacheIt(tz)` 缓存时区名称，避免重复探测。
5. **透明回退**：若 param 探测失败或无匹配目录，透明回退原上游逻辑。
6. **configure 阶段**：启用 `--with-internal-tzcode` 确保 R 自带 IANA 数据库可用。
7. **未硬编码**：未硬编码 `Asia/Shanghai` 或 UTC，时区值完全来自设备 parameter。

### 验证

```bash
R -e 'cat(Sys.timezone(), "\n"); cat(format(as.POSIXct("2026-01-01 00:00:00")), "\n")'
# 修复前: Sys.timezone() 返回空或 NA
# 修复后: 返回 Asia/Shanghai，时间转换正确
```

Round 12 完整 CI exit 0，Round 13 可移动运行时验证通过。

## 互引说明

- **similar_to E176**: 两者均为 HarmonyOS 平台能力差异导致的问题。E176 是动态链接器拒绝加载 ICU stubdata；E315 是传统时区发现链在 HarmonyOS 上失效。修复策略均为平台能力探测后选择兼容路径。
- 与 E243（Rprof ITIMER）、E245（OpenBLAS SONAME）、E246（install sed 范围限定）属同一 r-base 4.5.1 适配批次（Round 5-16），但解决的问题轴不同。
