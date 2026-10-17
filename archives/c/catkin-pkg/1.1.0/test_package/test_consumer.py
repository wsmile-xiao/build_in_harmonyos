from catkin_pkg.package import parse_package_string

xml = """<package format="3"><name>consumer_demo</name><version>1.2.3</version><description>demo</description><maintainer email="a@example.com">A</maintainer><license>MIT</license></package>"""
pkg = parse_package_string(xml)
assert pkg.name == "consumer_demo"
assert str(pkg.version) == "1.2.3"
print("catkin_pkg API consumer test passed")
