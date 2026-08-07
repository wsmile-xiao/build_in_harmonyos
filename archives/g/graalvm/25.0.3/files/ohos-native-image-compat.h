#ifndef GRAALVM_NATIVE_IMAGE_COMPAT_H
#define GRAALVM_NATIVE_IMAGE_COMPAT_H

#include <dlfcn.h>

/* GNU link-map namespaces queried by Graal's Linux POSIX metadata probe. */
typedef long Lmid_t;

#ifndef LM_ID_BASE
#define LM_ID_BASE ((Lmid_t)0)
#endif

#ifndef LM_ID_NEWLM
#define LM_ID_NEWLM ((Lmid_t)-1)
#endif

#ifndef RTLD_DI_LMID
#define RTLD_DI_LMID 1
#endif

#endif
