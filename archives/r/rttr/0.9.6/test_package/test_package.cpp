// test_package — real consumer of the packaged rttr library.
//
// Exercises the reflection API end to end against the INSTALLED package:
// version macros, type lookup, reflective construction, property get/set,
// method invocation, metadata queries. 15 runtime checks + 2 compile-time
// static_asserts; exits non-zero if any check fails.
#include <rttr/registration>
#include <rttr/type>
#include <rttr/detail/base/version.h>

#include <cstdio>
#include <string>
#include <utility>

// The packaged headers must be rttr 0.9.6.
static_assert(RTTR_VERSION == 906, "unexpected rttr version");
static_assert(RTTR_VERSION_MAJOR == 0 && RTTR_VERSION_MINOR == 9 &&
                  RTTR_VERSION_PATCH == 6,
              "unexpected rttr version components");

struct product
{
    product() : id(0) {}
    product(int ident, std::string name) : id(ident), name(std::move(name)) {}

    int get_id() const { return id; }
    void set_name(const std::string& n) { name = n; }
    const std::string& get_name() const { return name; }

    int id;
    std::string name;
};

RTTR_REGISTRATION
{
    // rttr 0.9.6 defaults to policy::ctor::as_std_shared_ptr (bind_impl.h);
    // pin as_object (via the bind call operator) so type::create() yields a
    // value-typed variant.
    rttr::registration::class_<product>("product")
        .constructor<>()(rttr::policy::ctor::as_object)
        .constructor<int, std::string>()(rttr::policy::ctor::as_object)
        .property("id", &product::id)
        .property("name", &product::get_name, &product::set_name)
        .method("get_id", &product::get_id);
}

static int failures = 0;

#define RTTR_CHECK(cond)                                                       \
    do                                                                         \
    {                                                                          \
        if (!(cond))                                                           \
        {                                                                      \
            std::printf("FAIL: %s\n", #cond);                                  \
            ++failures;                                                        \
        }                                                                      \
    } while (false)

int main()
{
    rttr::type t = rttr::type::get<product>();
    RTTR_CHECK(t.is_valid());
    RTTR_CHECK(t.get_name() == std::string("product"));

    // construct a product reflectively: product(42, "widget")
    rttr::variant inst = t.create({42, std::string("widget")});
    RTTR_CHECK(inst.is_valid());
    RTTR_CHECK(inst.get_type() == t);

    rttr::property id_prop = t.get_property("id");
    rttr::property name_prop = t.get_property("name");
    RTTR_CHECK(id_prop.is_valid());
    RTTR_CHECK(name_prop.is_valid());

    rttr::variant id_val = id_prop.get_value(inst);
    RTTR_CHECK(id_val.is_valid() && id_val.to_int() == 42);

    rttr::method get_id = t.get_method("get_id");
    RTTR_CHECK(get_id.is_valid());
    rttr::variant id_via_method = get_id.invoke(inst);
    RTTR_CHECK(id_via_method.is_valid() && id_via_method.to_int() == 42);

    RTTR_CHECK(name_prop.set_value(inst, std::string("gadget")));
    rttr::variant name_after = name_prop.get_value(inst);
    RTTR_CHECK(name_after.is_valid() && name_after.to_string() == "gadget");

    // metadata queries
    RTTR_CHECK(t.get_properties().size() == 2);
    RTTR_CHECK(t.get_methods().size() == 1);
    RTTR_CHECK(rttr::type::get<int>().is_arithmetic());
    RTTR_CHECK(t.get_sizeof() == sizeof(product));

    if (failures == 0)
    {
        std::printf("RTTR_TEST_PACKAGE_OK (15 checks)\n");
        return 0;
    }
    std::printf("RTTR_TEST_PACKAGE_FAILED (%d failures)\n", failures);
    return 1;
}
