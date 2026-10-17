/* compat/ap_Args.h — OHOS minimal AP_Args shim
 * mswrite plugin only reads the static AP_Args::m_impProps (import props).
 */
#ifndef COMPAT_AP_ARGS_H
#define COMPAT_AP_ARGS_H

#include "ie_types.h"

class AP_Args
{
public:
	/* import property set (static, shared by all importers) */
	static const char ** m_impProps;
};

#endif /* COMPAT_AP_ARGS_H */
