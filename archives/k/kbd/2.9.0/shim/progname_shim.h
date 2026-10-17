/* kbd OHOS/musl shim: glibc's program_invocation_short_name is unavailable;
 * musl's dynamic loader provides __progname with the same semantics.
 * Force-included via -include (see conanfile.py generate()). */
#ifndef KBD_PROGNAME_SHIM_H
#define KBD_PROGNAME_SHIM_H

#ifndef __GLIBC__
extern char *__progname;
#define program_invocation_short_name __progname
#endif

#endif /* KBD_PROGNAME_SHIM_H */
