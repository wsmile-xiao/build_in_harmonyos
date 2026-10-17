/* Portability shim: <libc.h> for non-Apple platforms.
 *
 * Classic cctools sources include <libc.h> (a NeXT/macOS header declaring
 * everyday libc entry points). On HarmonyOS/musl the same declarations
 * live in the standard headers aggregated below.
 */
#ifndef OCMTOC_PORT_LIBC_H
#define OCMTOC_PORT_LIBC_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#endif /* OCMTOC_PORT_LIBC_H */
