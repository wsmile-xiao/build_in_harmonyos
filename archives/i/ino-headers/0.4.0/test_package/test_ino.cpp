// Consumer probe — C++ translation unit exercising the public API surface
// of ino-headers 0.4.0 (header-only, declarations only).
//
// The header declares the ino API but implements nothing (implementations
// live in downstream ino backend libraries), so this probe intentionally
// performs compile-time checks only — decltype() comparisons never ODR-use
// the declared functions, hence no linker references are emitted.
#include <ino/lib.h>

#include <cstddef>
#include <cstdint>
#include <type_traits>

// --- Types ---------------------------------------------------------------
static_assert(std::is_same<ino_context, void*>::value, "ino_context must be void*");
static_assert(std::is_same<ino_variant, void*>::value, "ino_variant must be void*");
static_assert(std::is_same<ino_method_cb, ino_variant (*)(ino_context, const ino_variant*, std::size_t)>::value,
              "ino_method_cb signature");

// --- Enum values (public API, upstream API version 0.0.0) ----------------
static_assert(INO_VARIANT_TYPE_UNDEFINED == 0, "enum value");
static_assert(INO_VARIANT_TYPE_NULL == 1, "enum value");
static_assert(INO_VARIANT_TYPE_BOOLEAN == 2, "enum value");
static_assert(INO_VARIANT_TYPE_STRING == 3, "enum value");
static_assert(INO_VARIANT_TYPE_NUMBER == 4, "enum value");
static_assert(INO_VARIANT_TYPE_OBJECT == 5, "enum value");

// --- Exact function signatures (decltype: unevaluated, no link refs) -----
static_assert(std::is_same<decltype(&ino_context_new), ino_context (*)()>::value, "ino_context_new()");
static_assert(std::is_same<decltype(&ino_context_free), void (*)(ino_context)>::value, "ino_context_free()");
static_assert(std::is_same<decltype(&ino_context_get_global_object), ino_variant (*)(ino_context)>::value,
              "ino_context_get_global_object()");
static_assert(std::is_same<decltype(&ino_variant_new_undefined), ino_variant (*)(ino_context)>::value,
              "ino_variant_new_undefined()");
static_assert(std::is_same<decltype(&ino_variant_new_null), ino_variant (*)(ino_context)>::value,
              "ino_variant_new_null()");
static_assert(std::is_same<decltype(&ino_variant_new_boolean), ino_variant (*)(ino_context, bool)>::value,
              "ino_variant_new_boolean()");
static_assert(std::is_same<decltype(&ino_variant_new_string), ino_variant (*)(ino_context, const std::uint16_t*)>::value,
              "ino_variant_new_string()");
static_assert(std::is_same<decltype(&ino_variant_new_string_utf8), ino_variant (*)(ino_context, const char*)>::value,
              "ino_variant_new_string_utf8()");
static_assert(std::is_same<decltype(&ino_variant_new_number), ino_variant (*)(ino_context, double)>::value,
              "ino_variant_new_number()");
static_assert(std::is_same<decltype(&ino_variant_new_object), ino_variant (*)(ino_context)>::value,
              "ino_variant_new_object()");
static_assert(std::is_same<decltype(&ino_variant_get_type), ino_variant_type (*)(ino_context, ino_variant)>::value,
              "ino_variant_get_type()");
static_assert(std::is_same<decltype(&ino_variant_to_boolean), bool (*)(ino_context, ino_variant)>::value,
              "ino_variant_to_boolean()");
static_assert(std::is_same<decltype(&ino_variant_to_string), std::uint16_t* (*)(ino_context, ino_variant)>::value,
              "ino_variant_to_string()");
static_assert(std::is_same<decltype(&ino_variant_to_string_utf8), char* (*)(ino_context, ino_variant)>::value,
              "ino_variant_to_string_utf8()");
static_assert(std::is_same<decltype(&ino_variant_to_number), double (*)(ino_context, ino_variant)>::value,
              "ino_variant_to_number()");
static_assert(std::is_same<decltype(&ino_variant_object_get_property),
                           ino_variant (*)(ino_context, ino_variant, const std::uint16_t*)>::value,
              "ino_variant_object_get_property()");
static_assert(std::is_same<decltype(&ino_variant_object_get_property_utf8),
                           ino_variant (*)(ino_context, ino_variant, const char*)>::value,
              "ino_variant_object_get_property_utf8()");
static_assert(std::is_same<decltype(&ino_variant_object_set_property),
                           void (*)(ino_context, ino_variant, const std::uint16_t*, ino_variant)>::value,
              "ino_variant_object_set_property()");
static_assert(std::is_same<decltype(&ino_variant_object_set_property_utf8),
                           void (*)(ino_context, ino_variant, const char*, ino_variant)>::value,
              "ino_variant_object_set_property_utf8()");
static_assert(std::is_same<decltype(&ino_variant_object_add_method),
                           ino_variant (*)(ino_context, ino_variant, const std::uint16_t*, ino_method_cb)>::value,
              "ino_variant_object_add_method()");
static_assert(std::is_same<decltype(&ino_variant_object_add_method_utf8),
                           ino_variant (*)(ino_context, ino_variant, const char*, ino_method_cb)>::value,
              "ino_variant_object_add_method_utf8()");
static_assert(std::is_same<decltype(&ino_variant_object_call),
                           ino_variant (*)(ino_context, ino_variant, const ino_variant*, std::size_t)>::value,
              "ino_variant_object_call()");
static_assert(std::is_same<decltype(&ino_variant_protect), void (*)(ino_context, ino_variant)>::value,
              "ino_variant_protect()");
static_assert(std::is_same<decltype(&ino_variant_unprotect), void (*)(ino_context, ino_variant)>::value,
              "ino_variant_unprotect()");
static_assert(std::is_same<decltype(&ino_eval), ino_variant (*)(ino_context, const std::uint16_t*)>::value,
              "ino_eval()");
static_assert(std::is_same<decltype(&ino_eval_utf8), ino_variant (*)(ino_context, const char*)>::value,
              "ino_eval_utf8()");

// --- Declaration-delimiter macros must work in C++ -----------------------
INO_BEGIN_C_DECLS
typedef int probe_c_decls_ok;
INO_END_C_DECLS

int main()
{
    // Runtime spot-check of the public enum numbering.
    int values[] = {
        INO_VARIANT_TYPE_UNDEFINED, INO_VARIANT_TYPE_NULL,   INO_VARIANT_TYPE_BOOLEAN,
        INO_VARIANT_TYPE_STRING,    INO_VARIANT_TYPE_NUMBER, INO_VARIANT_TYPE_OBJECT,
    };
    for (int i = 0; i < 6; ++i) {
        if (values[i] != i) return 1;
    }
    (void)sizeof(probe_c_decls_ok);
    return 0;
}
