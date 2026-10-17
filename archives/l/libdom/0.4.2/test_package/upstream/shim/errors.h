/*
 * Forwarding shim so the UNMODIFIED upstream DOMTS testutils (load.c) can
 * resolve <errors.h> to the hubbub binding header installed by the libdom
 * Conan package (include/dom/bindings/hubbub/errors.h). Not part of upstream.
 */
#include <dom/bindings/hubbub/errors.h>
