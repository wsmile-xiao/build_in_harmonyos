/* Target definitions for HarmonyOS using the Linux kernel and musl ABI.

   This adaptation is distributed under the same terms as GCC; see COPYING3
   and COPYING.RUNTIME in the GCC source distribution.  */

#ifndef GCC_OHOS_H
#define GCC_OHOS_H

/* Retain the normal GNU/Linux and musl builtins, and add the platform
   macro used by HarmonyOS source ports.  */
#undef TARGET_OS_CPP_BUILTINS
#define TARGET_OS_CPP_BUILTINS()          \
  do                                      \
    {                                     \
      GNU_USER_TARGET_OS_CPP_BUILTINS (); \
      builtin_define ("__OHOS__");        \
    }                                     \
  while (0)

#endif /* GCC_OHOS_H */
