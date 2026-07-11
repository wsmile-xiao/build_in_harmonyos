-- bam.lua: Simple build script for testing bam
settings = NewSettings()

src = Collect("*.c")
objs = Compile(settings, src)
exe = Link(settings, "hello", objs)
DefaultTarget(exe)
