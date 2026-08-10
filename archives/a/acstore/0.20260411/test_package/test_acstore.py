#!/usr/bin/env python3
from acstore.helpers import yaml_definitions_file


definition = {
    "name": "smoke_container",
    "attributes": [
        {"name": "path", "type": "str"},
        {"name": "size", "type": "int"},
    ],
}

container_class = (
    yaml_definitions_file.YAMLAttributeContainerDefinitionsFile()
    ._ReadDefinition(definition)
)
assert container_class.CONTAINER_TYPE == "smoke_container"
assert container_class.SCHEMA == {"path": "str", "size": "int"}
print("acstore smoke test: YAML definition API assertions passed")
