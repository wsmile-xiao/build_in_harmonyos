// libdap 3.20.6 consumer smoke test (R34: 实质调用被测包 API)
//
// 验证点:
//   1. 头文件闭包可用 (DDS/Int32/Str/Array/AttrTable/DAS/BaseTypeFactory)
//   2. DDS 数据模型: 工厂构造 + add_var + var() 查找 + value() round-trip
//   3. AttrTable append_attr + DDS print 序列化
//   4. 库链接: libdap + libdapclient + libdapserver + libtirpc/uuid/libxml2
#include <cstdio>
#include <iostream>
#include <string>

#include "libdap/DDS.h"
#include "libdap/DAS.h"
#include "libdap/Int32.h"
#include "libdap/Str.h"
#include "libdap/Array.h"
#include "libdap/AttrTable.h"
#include "libdap/BaseTypeFactory.h"
#include "libdap/Error.h"

int main() {
    try {
        // 1. DDS 构造 (BaseTypeFactory 驱动的 DAP2 数据集)
        libdap::BaseTypeFactory factory;
        libdap::DDS dds(&factory, "test_dataset");

        // 2. Int32: set_value/value round-trip
        libdap::Int32 *i32 = new libdap::Int32("test_int");
        i32->set_value(42);
        dds.add_var_nocopy(i32);

        // 3. Str
        libdap::Str *str_var = new libdap::Str("test_str");
        str_var->set_value("hello libdap on OHOS");
        dds.add_var_nocopy(str_var);

        // 4. Array (Int32 原型 + append_dim)
        libdap::Array *arr = new libdap::Array("test_array", new libdap::Int32("proto"));
        arr->append_dim(4, "dim0");
        dds.add_var_nocopy(arr);

        // 5. AttrTable
        libdap::AttrTable attr;
        attr.append_attr("units", "String", "count");

        // 6. DDS 序列化 (print 走一遍类型树)
        dds.print(stdout);
        printf("\n");

        // 7. 校验 round-trip
        libdap::BaseType *bt = dds.var("test_int");
        if (!bt) {
            std::cerr << "FAIL: var(test_int) not found" << std::endl;
            return 1;
        }
        libdap::Int32 *got = dynamic_cast<libdap::Int32 *>(bt);
        if (!got) {
            std::cerr << "FAIL: var(test_int) is not Int32" << std::endl;
            return 1;
        }
        libdap::dods_int32 v = got->value();
        if (v != 42) {
            std::cerr << "FAIL: expected 42, got " << v << std::endl;
            return 1;
        }

        // 8. DAS 构造 + print
        libdap::DAS das;
        das.print(stdout);

        printf("LIBDAP_TEST_OK\n");
        return 0;
    } catch (const libdap::Error &e) {
        std::cerr << "libdap::Error: " << e.get_error_message() << std::endl;
        return 1;
    } catch (const std::exception &e) {
        std::cerr << "exception: " << e.what() << std::endl;
        return 1;
    }
}
