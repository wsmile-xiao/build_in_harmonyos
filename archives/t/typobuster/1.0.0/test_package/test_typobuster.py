from pathlib import Path

from typobuster import tools


assert tools.to_snake_case("Hello World") == "hello_world"
assert tools.to_kebab_case("Hello World") == "hello-world"
assert tools.to_camel_case("hello world") == "helloWorld"
assert Path(tools.__file__).parent.joinpath("langs", "en_US.json").is_file()
print("typobuster pure-Python smoke test passed")
