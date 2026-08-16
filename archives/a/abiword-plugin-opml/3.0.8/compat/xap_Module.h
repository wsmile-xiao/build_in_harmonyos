/* compat/xap_Module.h — OHOS minimal AbiWord xap_Module.h shim */
#ifndef XAP_MODULE_H
#define XAP_MODULE_H

#include <stdio.h>
#include "ut_types.h"

/* Non-Windows builds: nothing extra is needed for dlopened modules. */
#define ABI_PLUGIN_DECLARE(name)

extern "C" {
	typedef struct {
		const char * name;
		const char * desc;
		const char * version;
		const char * author;
		const char * usage;
	} XAP_ModuleInfo;
}

typedef int (*XAP_Plugin_Registration) (XAP_ModuleInfo * mi);
typedef int (*XAP_Plugin_VersionCheck) (UT_uint32 major, UT_uint32 minor, UT_uint32 release);

#define isCurrentAbiVersion(a,b,c) true

/* ABI_PLUGIN_SOURCE is not defined when building the plugin, so the
   plugin reports the core build version. */
#define ABI_VERSION_STRING ABI_BUILD_VERSION

#endif /* XAP_MODULE_H */
