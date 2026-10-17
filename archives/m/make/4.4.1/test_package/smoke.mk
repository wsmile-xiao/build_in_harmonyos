all: out.txt
	@echo built-$(<F)
out.txt:
	@echo hello-from-gnu-make > $@

clean:
	@rm -f out.txt
