-- test.lua: Test that std.debug module loads correctly
local d = require("std.debug")
if d then
    print("std.debug loaded successfully")
else
    error("std.debug is nil")
end
