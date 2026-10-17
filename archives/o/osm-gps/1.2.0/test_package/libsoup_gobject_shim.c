/* libsoup_gobject_shim.c — OHOS runtime workaround for libsoup/2.74.3.
 *
 * Root cause: the ohpcd-published libsoup/2.74.3 binary statically embeds a
 * copy of GLib's GObject type system and exports g_type_register_fundamental /
 * g_param_type_register_static globally. When a consumer (osm-gps) also pulls
 * the shared libgobject (via gtk), the process ends up with TWO GType systems
 * sharing the same soname (libgobject-2.0.so.0). Both copies try to register
 * the fundamental/param types (gchar, GParamChar, ...) into their own tables,
 * and the second registration aborts with
 *   "cannot register existing type 'gchar'"
 *   "g_param_type_register_static: assertion 'g_type_from_name (name) == 0' failed"
 *
 * Workaround: this LD_PRELOAD shim intercepts the GType registry entry points
 * and funnels EVERY registration through the real shared libgobject
 * implementation (resolved explicitly via dlopen of libgobject-2.0.so.0, so it
 * is independent of ELF load order), made idempotent by type name. Both the
 * libsoup-embedded glib and libgobject itself therefore register into the
 * single shared type table, turning the fatal double-registration into a
 * harmless no-op. It does not change osm-gps behaviour — the consumer still
 * performs a full end-to-end OSM GPS map type registration.
 *
 * This is a loader-level workaround for a known libsoup/2.74.3 OHOS packaging
 * defect (it should link the shared glib, not embed it). It is applied only in
 * the test_package so the genuine consumer test can run on OHOS.
 */
#define _GNU_SOURCE
#include <dlfcn.h>

typedef unsigned long GType;
typedef struct _GTypeInfo GTypeInfo;
typedef unsigned int GTypeFlags;

typedef GType (*RegFundamentalFun)(GType, const char*, const char*, GType,
                                   unsigned int, const GTypeInfo*, GTypeFlags);
typedef GType (*RegStaticFun)(GType, const char*, const GTypeInfo*, GTypeFlags);
typedef GType (*ParamRegStaticFun)(const char*, GTypeFlags);
typedef GType (*FromNameFun)(const char*);
typedef const char* (*NameFun)(GType);

static void *gobj_handle = 0;
static RegFundamentalFun real_reg_fundamental = 0;
static RegStaticFun       real_reg_static = 0;
static ParamRegStaticFun  real_param_reg_static = 0;
static FromNameFun        real_from_name = 0;
static NameFun            real_name = 0;

static void ensure(void) {
    if (real_reg_fundamental)
        return;
    /* Resolve the REAL libgobject explicitly so we are independent of the
     * order in which LD_PRELOAD vs libsoup vs libgobject are mapped. */
    gobj_handle = dlopen("libgobject-2.0.so.0", RTLD_NOW | RTLD_LOCAL);
    if (!gobj_handle)
        gobj_handle = RTLD_DEFAULT;
    real_reg_fundamental = (RegFundamentalFun)dlsym(gobj_handle, "g_type_register_fundamental");
    real_reg_static      = (RegStaticFun)dlsym(gobj_handle, "g_type_register_static");
    real_param_reg_static= (ParamRegStaticFun)dlsym(gobj_handle, "g_param_type_register_static");
    real_from_name       = (FromNameFun)dlsym(gobj_handle, "g_type_from_name");
    real_name            = (NameFun)dlsym(gobj_handle, "g_type_name");
}

static GType lookup_existing(const char *name) {
    if (real_from_name && name) {
        GType t = real_from_name(name);
        if (t) return t;
    }
    return 0;
}

GType g_type_register_fundamental(GType type_id, const char *type_name,
                                  const char *type_init, GType parent_type,
                                  unsigned int class_size, const GTypeInfo *info,
                                  GTypeFlags flags) {
    ensure();
    GType existing = lookup_existing(type_name);
    if (existing) return existing;
    if (!real_reg_fundamental) return type_id;
    return real_reg_fundamental(type_id, type_name, type_init, parent_type,
                                class_size, info, flags);
}

GType g_type_register_static(GType parent_type, const char *type_name,
                             const GTypeInfo *info, GTypeFlags flags) {
    ensure();
    GType existing = lookup_existing(type_name);
    if (existing) return existing;
    if (!real_reg_static) return 0;
    return real_reg_static(parent_type, type_name, info, flags);
}

GType g_param_type_register_static(const char *name, GTypeFlags flags) {
    ensure();
    GType existing = lookup_existing(name);
    if (existing) return existing;
    if (!real_param_reg_static) return 0;
    return real_param_reg_static(name, flags);
}

GType g_type_from_name(const char *name) {
    ensure();
    if (!real_from_name) return 0;
    return real_from_name(name);
}

const char* g_type_name(GType type) {
    ensure();
    if (!real_name) return 0;
    return real_name(type);
}
