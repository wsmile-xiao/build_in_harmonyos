# DRAFT-E660 — OHOS musl open_memstream 不显式 fflush 则缓冲/大小不回写

- 软件实证：mustach 1.2.10（mustach_mem / mustach_cJSON_mem 等内存渲染接口）
- 阶段：原生运行验证（test_package 消费者测试 + 真机 CLI）
- 日期：2026-09-22

## 现象

mustach 的 `mustach_mem`（以及三个 wrapper 的 `*_mem`）在设备上返回 rc=0 但
输出恒空、`*size` 下溢为 SIZE_MAX（18446744073709551615），进程退出期可触发
SIGTRAP。根因在 mustach.c 的 `memfile_close`：

```c
rc = fputc(0, file) ? MUSTACH_ERROR_SYSTEM : 0;
fclose(file);                 /* ← 无显式 flush */
if (rc == 0)
        (*size)--;            /* size==0 时下溢 */
```

OHOS 平台 musl 的 `open_memstream` 只在**显式 flush** 时把字节发布到调用方的
`*buffer/*size`，纯 fclose 不回写。

## 设备四象限探针（最小定性）

| 路径 | fclose 后 *size |
|---|---|
| 写入 + fclose | 0（空 buffer） |
| fputc(0) + fclose | 0（空 buffer） |
| fflush + fclose | 11（内容正确） |
| fputc(0) + fflush + fclose | 12（内容正确，含 NUL） |

复现探针（设备可直接执行）：

```c
/* ms4.c —— /data/service/hnp/bin/clang -o ms4 ms4.c && ./ms4 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void t(const char *name, int use_fputc, int use_fflush){
  char *buf=NULL; size_t sz=0;
  FILE *f=open_memstream(&buf,&sz);
  fputs("Hello OHOS!",f);
  if (use_fputc) fputc(0,f);
  if (use_fflush) fflush(f);
  fclose(f);
  printf("%-28s sz=%zu\n", name, sz);
  free(buf);
}
int main(void){
  t("plain close", 0,0);  t("fputc+close", 1,0);
  t("fflush+close", 0,1); t("fputc+fflush+close", 1,1);
  return 0;
}
```

## 修复（包补丁 0001-ohos-open-memstream-flush-before-close.patch）

```c
 rc = fputc(0, file) ? MUSTACH_ERROR_SYSTEM : 0;
+fflush(file);   /* OHOS: open_memstream 仅在显式 flush 时回写 */
 fclose(file);
```

修复后 mustach_mem 输出与 size 契约全部恢复（消费者测试 13/13 通过）。

## 关联事实

- 替代路径 `tmpfile()` 在设备返回 NULL（/tmp 只读，实测），因此上游的
  `NO_OPEN_MEMSTREAM` 分支在 OHOS 上同样不可用——不能以切 fallback 规避。
- 凡在 OHOS 上采信"渲染到内存"类接口，先用最小探针验证 open_memstream 回写
  行为，再跑业务断言；"rc=0 + 输出恒空"是高隐蔽假绿。
