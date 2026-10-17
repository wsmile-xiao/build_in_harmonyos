# zsdx

The Legend of Zelda - Mystery of Solarus DX — quest data package for the
Solarus 2D game engine (Solarus team's first game). The recipe packages the
upstream `data/` tree (293 Lua game scripts + maps/sprites/sounds/fonts)
into a root-relative `data.solarus` zip, installed to
`share/solarus/zsdx/data.solarus`, exactly as the upstream build does.

Pure data package: no compiler units (`project(ZSDX NONE)`), no conan
dependency on the Solarus engine. Consumers need a Solarus 1.6.x runtime to
play. License: GPL-3.0-only (Lua scripts) AND CC-BY-SA-4.0 (created data).
