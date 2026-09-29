/*
 * ipatch_compat.h — API drift compatibility shim for tests/sample_list_test.c
 *
 * libinstpatch 1.1.7 R03 攻坚：把上游 v1.1.7 已移除的旧测试 API 忠实映射到
 * v1.1.7 现有 API。本文件仅供测试编译期 -include 使用，不修改库源码/配方，
 * 不含任何平台条件编译宏，不弱化测试断言（MAX_DIFF_ALLOWED=0.0 保持）。
 *
 * 用法：
 *   clang -include tests-compat/ipatch_compat.h sample_list_test.c \
 *         -I<include/libinstpatch-2> ... -linstpatch-1.0 ...
 */
#ifndef IPATCH_COMPAT_H
#define IPATCH_COMPAT_H

#include <libinstpatch/libinstpatch.h>
#include <libinstpatch/sample.h>
#include <glib.h>
#include <string.h>
#include <stdarg.h>

/* ── 1. 通道常量：已移除 IPATCH_SAMPLE_LIST_CHAN_* → v1.1.7 sample.h 枚举 ── */
#define IPATCH_SAMPLE_LIST_CHAN_RIGHT IPATCH_SAMPLE_RIGHT
#define IPATCH_SAMPLE_LIST_CHAN_LEFT  IPATCH_SAMPLE_LEFT

/* ── 2. store↔data 关联注册表 + data→size 记录（单 TU；兼容层专用，不触库） ── */
typedef struct { IpatchSample *store; IpatchSampleData *data; } IpatchCompatEntry;
static IpatchCompatEntry ipatch_compat_registry[32];
static guint ipatch_compat_registry_n = 0;

/* data 对象与旧 API 传入的 size 的映射（v1.1.7 sample-size 由 store 承载） */
typedef struct { IpatchSampleData *data; guint size; } IpatchCompatDataSize;
static IpatchCompatDataSize ipatch_compat_data_sizes[32];
static guint ipatch_compat_data_size_n = 0;

static void ipatch_compat_register(IpatchSample *store, IpatchSampleData *data)
{
    if (ipatch_compat_registry_n < 32) {
        ipatch_compat_registry[ipatch_compat_registry_n].store = store;
        ipatch_compat_registry[ipatch_compat_registry_n].data = data;
        ipatch_compat_registry_n++;
    }
}

static void ipatch_compat_remember_data_size(IpatchSampleData *data, guint size)
{
    guint i;
    for (i = 0; i < ipatch_compat_data_size_n; i++) {
        if (ipatch_compat_data_sizes[i].data == data) {
            ipatch_compat_data_sizes[i].size = size;
            return;
        }
    }
    if (ipatch_compat_data_size_n < 32) {
        ipatch_compat_data_sizes[ipatch_compat_data_size_n].data = data;
        ipatch_compat_data_sizes[ipatch_compat_data_size_n].size = size;
        ipatch_compat_data_size_n++;
    }
}

static guint ipatch_compat_lookup_data_size(IpatchSampleData *data)
{
    guint i;
    for (i = 0; i < ipatch_compat_data_size_n; i++)
        if (ipatch_compat_data_sizes[i].data == data)
            return ipatch_compat_data_sizes[i].size;
    return 0;
}

static IpatchSampleData *ipatch_compat_lookup_data(IpatchSample *store)
{
    guint i;
    for (i = 0; i < ipatch_compat_registry_n; i++)
        if (ipatch_compat_registry[i].store == store)
            return ipatch_compat_registry[i].data;
    return NULL;
}

/* ── 3. ipatch_sample_data_new(guint size) → ipatch_sample_data_new(void) ──
 * v1.1.7: IpatchSampleData 的 sample-size 为 readonly，容量由加入的 store 决定
 *（ipatch_sample_data_add）；旧 API 的 size 参数转化为 store 的 sample-size。 */
static inline IpatchSampleData *ipatch_compat_sample_data_new(guint size)
{
    IpatchSampleData *data = ipatch_sample_data_new();
    ipatch_compat_remember_data_size(data, size);
    return data;
}
#define ipatch_sample_data_new(sz) ipatch_compat_sample_data_new(sz)

/* ── 4. ipatch_sample_store_new(type, data, "format",FMT,"location",loc,"active",b,NULL)
 *    → 类型化构造器 + g_object_set + data_add ── */
static inline IpatchSample *ipatch_compat_sample_store_new(GType type,
        IpatchSampleData *data, ...)
{
    va_list ap;
    const char *prop;
    int format = 0;
    gpointer location = NULL;
    gboolean active = FALSE;
    IpatchSample *store;

    va_start(ap, data);
    while ((prop = va_arg(ap, const char *)) != NULL) {
        if (strcmp(prop, "format") == 0)
            format = va_arg(ap, int);
        else if (strcmp(prop, "location") == 0)
            location = va_arg(ap, gpointer);
        else if (strcmp(prop, "active") == 0)
            active = va_arg(ap, gboolean);
        else
            (void) va_arg(ap, void *);
    }
    va_end(ap);

    if (type == IPATCH_TYPE_SAMPLE_STORE_RAM)
        /* 外部自有 buffer（测试的 dwave）：不得设置 free-data/RAM_ALLOCATED 标志，
         * 否则 finalize 会提前 g_free(location) 造成与测试自己的 g_free(dwave) 双释放。
         * 用 g_object_new + g_object_set("location") 构造（location setter 仅要求初始为 NULL）。 */
        store = (IpatchSample *) g_object_new(IPATCH_TYPE_SAMPLE_STORE_RAM, NULL),
        g_object_set(store, "location", location, NULL);
    else if (type == IPATCH_TYPE_SAMPLE_STORE_VIRTUAL)
        store = (IpatchSample *) ipatch_sample_store_virtual_new();
    else
        return NULL;

    if (format)
        g_object_set(store, "sample-format", format, NULL);

    /* v1.1.7: sample-size 由 store 承载（data 上 readonly）；旧 API 的 size 参数
     * 经 data 记录在此应用，保证列表项断言 ofs+size <= sample_size 通过 */
    {
        guint dsize = ipatch_compat_lookup_data_size(data);
        if (dsize)
            g_object_set(store, "sample-size", dsize, NULL);
    }

    ipatch_compat_register(store, data);

    /* 旧 "active"=TRUE 语义 = 装配进 data（v1.1.7: ipatch_sample_data_add） */
    if (active && data)
        ipatch_sample_data_add(data, IPATCH_SAMPLE_STORE(store));

    return store;
}
#define ipatch_sample_store_new(...) ipatch_compat_sample_store_new(__VA_ARGS__)

/* ── 5. ipatch_sample_store_activate(store) → ipatch_sample_data_add(data, store) ── */
static inline void ipatch_compat_sample_store_activate(IpatchSample *store)
{
    IpatchSampleData *data = ipatch_compat_lookup_data(store);
    if (data)
        ipatch_sample_data_add(data, IPATCH_SAMPLE_STORE(store));
}
#define ipatch_sample_store_activate(s) ipatch_compat_sample_store_activate(s)

/* ── 6. ipatch_sample_store_duplicate(store,type,FMT,err)
 *    → 按通道 mono 渲染虚拟 store 的两个列表并交错为 stereo RAM store
 *      （v1.1.7 无通用 duplicate；get_cache_sample 对 stereo 虚拟 store 的
 *       list_render 断言 channel==1，故逐通道 render_alloc + 交错是语义等价路径） ── */
static inline IpatchSample *ipatch_compat_sample_store_duplicate(IpatchSample *store,
        GType type, int format, GError **err)
{
    IpatchSampleStoreVirtual *vst;
    IpatchSampleList *l0, *l1;
    guint frames = 0;
    int mono_fmt = IPATCH_SAMPLE_DOUBLE | IPATCH_SAMPLE_MONO
                   | IPATCH_SAMPLE_ENDIAN_HOST;
    gpointer b0 = NULL, b1 = NULL;
    double *out;
    guint i;
    IpatchSample *ram;

    (void) type;
    vst = IPATCH_SAMPLE_STORE_VIRTUAL(store);
    l0 = ipatch_sample_store_virtual_get_list(vst, 0);
    l1 = ipatch_sample_store_virtual_get_list(vst, 1);

    g_object_get(store, "sample-size", &frames, NULL);

    /* ipatch_sample_list_render_alloc 的 size 参数为字节数（须为帧大小整数倍） */
    {
        guint nbytes = frames * (guint) ipatch_sample_format_size(mono_fmt);
        b0 = ipatch_sample_list_render_alloc(l0, 0, nbytes, mono_fmt, err);
        if (!b0)
            return NULL;
        b1 = ipatch_sample_list_render_alloc(l1, 0, nbytes, mono_fmt, err);
        if (!b1) {
            g_free(b0);
            return NULL;
        }
    }

    out = g_new(double, frames * 2);
    for (i = 0; i < frames; i++) {
        out[i * 2] = ((double *) b0)[i];
        out[i * 2 + 1] = ((double *) b1)[i];
    }
    g_free(b0);
    g_free(b1);

    ram = (IpatchSample *) ipatch_sample_store_ram_new(out, TRUE);
    g_object_set(ram, "sample-format", format, NULL);
    g_object_set(ram, "sample-size", frames, NULL);
    return ram;
}
#define ipatch_sample_store_duplicate(s,t,f,e) ipatch_compat_sample_store_duplicate(s,t,f,e)

/* ── 7. ipatch_sample_store_RAM_get_location(store) → g_object_get "location" ── */
static inline gpointer ipatch_compat_sample_store_RAM_get_location(IpatchSample *store)
{
    gpointer loc = NULL;
    g_object_get(store, "location", &loc, NULL);
    return loc;
}
#define ipatch_sample_store_RAM_get_location(s) ipatch_compat_sample_store_RAM_get_location(s)

#endif /* IPATCH_COMPAT_H */
