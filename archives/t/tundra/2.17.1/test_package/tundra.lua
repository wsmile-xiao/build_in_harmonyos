local native = require 'tundra.native'

Build {
    Configs = {
        Config {
            Name = 'linux-clang',
            Tools = { 'clang' },
            DefaultOnHost = { native.host_platform },
        },
    },
    Units = function()
        Program {
            Name = 'hello',
            Sources = 'hello.c',
        }
        Default 'hello'
    end,
}
