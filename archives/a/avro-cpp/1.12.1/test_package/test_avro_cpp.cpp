#include <avro/Compiler.hh>
#include <avro/ValidSchema.hh>
#include <iostream>

int main()
{
    const auto schema = avro::compileJsonSchemaFromString(
        R"({"type":"record","name":"Message","fields":[{"name":"text","type":"string"}]})");
    if (schema.root()->type() != avro::AVRO_RECORD)
    {
        std::cerr << "schema root is not a record" << std::endl;
        return 1;
    }
    return 0;
}
