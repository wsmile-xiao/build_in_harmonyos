/* Target 1 - link verification for the zephyr/3.1.2 package.
 *
 * Includes the packaged public header (<zephyr/zephyr.h>, which in turn includes
 * the propagated <com_err.h>) and links the packaged library
 * (target_link_libraries(... zephyr::zephyr), i.e. -lzephyr).  Taking the
 * address of every entry point below forces real symbol resolution, so the
 * build fails if the package ships incomplete headers, a broken SONAME or an
 * import library that does not export the API.
 *
 * It is deliberately kept runnable: where the dynamic loader can resolve the
 * packaged SONAME (a HarmonyOS app whose libs live inside the loader namespace,
 * or a host with a writable namespace directory) conanfile.py test() executes
 * it and reports the result; where it cannot - as on this build host, where the
 * loader ignores LD_LIBRARY_PATH / DT_RUNPATH / $ORIGIN / LD_PRELOAD - the
 * binding is asserted structurally instead and the run is reported as
 * environment-limited.  See notes.md for the measurements.
 */
#include "zephyr_consumer.h"

static const struct zephyr_api linked_api = {
    &ZInitialize,
    &ZGetRealm,
    &ZGetSender,
    &ZGetFD,
    &ZCompareUID,
    &ZFormatNotice,
    &ZParseNotice,
    &ZFreeNotice,
};

int main(void)
{
    return zephyr_run_consumer_checks(
        &linked_api, "linked consumer (DT_NEEDED libzephyr.so.4)");
}
