/* Single compilation unit that instantiates the clay implementation.
 * Downstream projects link the packaged libclay.a and include clay.h
 * WITHOUT defining CLAY_IMPLEMENTATION (declaration-only mode). */
#define CLAY_IMPLEMENTATION
#include "clay.h"
