// Consumer test for the libcmis package: exercises real public C++ API
// offline (no network, no session): PropertyType/Property value objects
// and the Exception type. Each numbered check prints exactly one
// "CHECK-OK: <name>" line; the test_package harness requires all 6.
#include <iostream>
#include <string>
#include <vector>

#include <libcmis/exception.hxx>
#include <libcmis/property-type.hxx>
#include <libcmis/property.hxx>

static int failures = 0;

#define CHECK(name, cond)                                              \
    do {                                                               \
        if (cond) {                                                    \
            std::cout << "CHECK-OK: " << name << std::endl;            \
        } else {                                                       \
            std::cout << "CHECK-FAIL: " << name << std::endl;          \
            ++failures;                                                \
        }                                                              \
    } while (0)

int main()
{
    // 1. PropertyType default constructor + id round-trip.
    libcmis::PropertyType pt;
    pt.setId( "cmis:name" );
    CHECK( "property-type-id", pt.getId( ) == "cmis:name" );

    // 2. Temporary type-definition constructor fields.
    libcmis::PropertyType temp( "string", "cmis:objectId", "objectId",
                                "Object Id", "cmis:objectId" );
    CHECK( "property-type-temp-ctor",
           temp.getId( ) == "cmis:objectId"
           && temp.getLocalName( ) == "objectId"
           && temp.getDisplayName( ) == "Object Id"
           && temp.getQueryName( ) == "cmis:objectId" );

    // 3. Type + flags round-trip.
    pt.setType( libcmis::PropertyType::String );
    pt.setMultiValued( true );
    pt.setUpdatable( true );
    CHECK( "property-type-flags",
           pt.getType( ) == libcmis::PropertyType::String
           && pt.isMultiValued( )
           && pt.isUpdatable( ) );

    // 4. Property string-values round-trip through a PropertyType.
    libcmis::PropertyTypePtr typePtr(
        new libcmis::PropertyType( "string", "cmis:name", "name",
                                   "Name", "cmis:name" ) );
    std::vector< std::string > values;
    values.push_back( "hello-cmis" );
    libcmis::Property property( typePtr, values );
    std::vector< std::string > back = property.getStrings( );
    CHECK( "property-values",
           back.size( ) == 1 && back[0] == "hello-cmis"
           && property.getPropertyType( )->getId( ) == "cmis:name" );

    // 5. Property XML serialization produces non-empty output.
    std::string xml = property.toString( );
    CHECK( "property-to-string", !xml.empty( )
           && xml.find( "hello-cmis" ) != std::string::npos );

    // 6. Exception message/type round-trip.
    libcmis::Exception exc( "boom", "constraint" );
    std::string what = exc.what( );
    CHECK( "exception-what", what == "boom" && exc.getType( ) == "constraint" );

    if ( failures == 0 )
        std::cout << "libcmis consumer checks all passed" << std::endl;
    return failures == 0 ? 0 : 1;
}
