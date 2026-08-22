-- test.lua — middleclass test_package: verify the Lua OOP module works
-- This test requires the middleclass package and exercises its core API:
--   - Class creation
--   - Inheritance
--   - Instance methods
--   - Mixins
--   - isInstanceOf

local class = require('middleclass')

-- Verify module metadata
assert(class, "middleclass module not found")
assert(class._VERSION == "middleclass v4.1.1",
    "Unexpected version: " .. tostring(class._VERSION))
assert(class._DESCRIPTION == "Object Orientation for Lua",
    "Unexpected description: " .. tostring(class._DESCRIPTION))

-- Test class creation
local Animal = class('Animal')
function Animal:initialize(name)
    self.name = name
end
function Animal:speak()
    return "My name is " .. self.name
end

-- Test inheritance
local Dog = class('Dog', Animal)
function Dog:speak()
    return "My name is " .. self.name .. " and I bark!"
end

-- Test instance creation via :new()
local dog = Dog:new('Rex')
assert(dog.name == 'Rex', "Instance name should be 'Rex'")
assert(dog:speak() == "My name is Rex and I bark!", "Method override failed")
assert(dog:isInstanceOf(Animal), "isInstanceOf(Animal) failed")
assert(dog:isInstanceOf(Dog), "isInstanceOf(Dog) failed")
assert(not dog:isInstanceOf(Animal:new('other')), "isInstanceOf should return false for unrelated instances")

-- Test static methods
assert(Dog:isSubclassOf(Animal), "isSubclassOf failed")
assert(not Animal:isSubclassOf(Dog), "isSubclassOf should be false for parent")

-- Test mixins
local Barker = { bark = function(self) return "Woof!" end }
Animal:include(Barker)
assert(dog:bark() == "Woof!", "Mixin method failed")

-- Test __call syntax (class(name) == class:class(name))
local Cat = class('Cat')
function Cat:initialize(name) self.name = name end
local cat = Cat:new('Whiskers')
assert(cat.name == 'Whiskers', "Cat instance name failed")

print("All middleclass tests passed!")
