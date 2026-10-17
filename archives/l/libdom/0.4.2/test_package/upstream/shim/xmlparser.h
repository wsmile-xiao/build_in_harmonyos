/*
 * Forwarding shim so the UNMODIFIED upstream DOMTS testutils (load.c) can
 * resolve <xmlparser.h> to the binding header installed by the libdom Conan
 * package (include/dom/bindings/xml/xmlparser.h). Not part of upstream test.
 */
#include <dom/bindings/xml/xmlparser.h>
