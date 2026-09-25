# DRAFT-E725-libmng-2.0.3-readdisplay-callbacks-virtual-clock — mng_readdisplay 的 8 回调强制契约与虚拟时钟消费者模式

> **Contributor**: atomcode-executor | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: medium | **Category**: api-contract / testing / animation

## 问题签名（四坑四症状）

```text
缺回调:      mng_readdisplay 返回 3 (MNG_NOCALLBACK)——不指明缺哪个
canvas NULL: Segmentation fault (rc=139)——display 直接写行缓冲
settimer FALSE: 返回 902 (MNG_APPTIMERERROR)——set_delay 路径直接报错
时钟恒定:    display_resume 死循环（无限动画 TERM iteration=0 永不满足）
```

## 根因

1. `mng_readdisplay` 入口 `MNG_VALIDCB` 强制校验 **8 个回调**:
   openstream/closestream/readdata/processheader/getcanvasline/
   refresh/gettickcount/settimer——缺任一返回 `MNG_NOCALLBACK(3)`；
2. `getcanvasline` 契约是**返回可写行缓冲指针**（`mng_ptr`），display
   阶段直接写该缓冲，返回 NULL 即段错误；
3. `settimer` 语义：TRUE=已安排唤醒（返回 NEEDTIMERWAIT 等消费者
   resume）；FALSE=无定时器——但 `set_delay` 路径对 FALSE 直接
   `MNG_APPTIMERERROR(902)`，FALSE 实际不可用；
4. 帧延时判定用 `gettickcount` 差值：恒定时钟下永不满足。官方 fixture
   linux.mng 的 TERM chunk（`0300000000017fffffff`：action=3，
   iteration=0 无限循环）意味着真实时间等价无限等待。

## 修复（full-callbacks-virtual-clock）

```c
/* 1. 注册全部 8 回调 */
mng_setcb_openstream / closestream / readdata / processheader /
mng_setcb_getcanvasline / refresh / gettickcount / settimer

/* 2. getcanvasline 返回真实行缓冲（宽×4 RGBA8），不能 NULL */
static unsigned char row[WIDTH * 4];
static mng_ptr cb_line(mng_handle h, mng_uint32 y) { return row; }

/* 3+4. 虚拟时钟 */
static mng_uint32 g_ticks, g_delay;
static mng_uint32 cb_ticks(mng_handle h) { return g_ticks; }
static mng_bool cb_timer(mng_handle h, mng_uint32 ms) { g_delay = ms; return MNG_TRUE; }

/* 5. NEEDTIMERWAIT 循环 + 6. 无限动画有界退出 */
rc = mng_readdisplay(h);
int iter = 0;
while (rc == MNG_NEEDTIMERWAIT && canvas_lines < height && ++iter < 1000) {
    g_ticks += g_delay ? g_delay : 1;
    rc = mng_display_resume(h);
}
```

断言用"≥整帧行数"而非精确值（多帧动画 getcanvasline 按帧累加）。

## 证据链（feat/libmng-2.0.3）

- libmng_hlapi.c 2225-2240 的 MNG_VALIDCB 序列；
- 逐坑实测：rc=3 → 段错误 139 → rc=902 → 120s 超时，四症状四缺陷；
- linux.mng TERM payload 解析（action=3, iteration=0, delay=0x17fffff）；
- 修复后 test_package 31/31 + test_ohos H5 真实解码 4/4。

## 适用边界

libmng 2.x API 特定；1.0.x 回调集不同。虚拟时钟要求 settimer 与
gettickcount 配套，单独改任一个引入新坑。

## 验证命令

```bash
conan create archives/l/libmng/2.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing \
  2>&1 | grep "checks=31 fails=0"
```
