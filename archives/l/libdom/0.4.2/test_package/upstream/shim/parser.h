/*
 * Forwarding shim so the UNMODIFIED upstream DOMTS testutils (load.c) can
 * resolve <parser.h> to the hubbub binding header installed by the libdom
 * Conan package (include/dom/bindings/hubbub/parser.h). Not part of upstream.
 */
#include <dom/bindings/hubbub/parser.h>
