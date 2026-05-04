# Makefile — Anvil test suite binaries
# Usage: make -C samples/test_suite all

NASM  := nasm
LD    := ld
GCC   := gcc

ASM_FLAGS := -f elf64 -g -F dwarf
LD_FLAGS  := -m elf_x86_64

# C flags per security profile
VULN_FLAGS  := -fno-stack-protector -no-pie -z execstack -g
NORMAL_FLAGS := -g
STRIPPED_FLAGS := -O2 -s
HARDENED_FLAGS := -fPIE -pie -fstack-protector-all -Wl,-z,relro,-z,now -g

TARGETS := 01_hello 02_loop 03_structs 04_bof_ret2win 05_format_string \
           06_rop_chain 07_stripped 08_static_pie 09_syscalls 10_many_functions

.PHONY: all clean

all: $(TARGETS)
	@echo "✓ All test binaries built"

# ASM targets (nasm + ld)
01_hello: 01_hello.asm
	$(NASM) $(ASM_FLAGS) $< -o $@.o && $(LD) $(LD_FLAGS) $@.o -o $@ && rm -f $@.o

09_syscalls: 09_syscalls.asm
	$(NASM) $(ASM_FLAGS) $< -o $@.o && $(LD) $(LD_FLAGS) $@.o -o $@ && rm -f $@.o

# C targets — normal (debug symbols)
02_loop: 02_loop.c
	$(GCC) $(NORMAL_FLAGS) $< -o $@ -lm

03_structs: 03_structs.c
	$(GCC) $(NORMAL_FLAGS) $< -o $@

10_many_functions: 10_many_functions.c
	$(GCC) $(NORMAL_FLAGS) $< -o $@

# C targets — vulnerable (no protections)
04_bof_ret2win: 04_bof_ret2win.c
	$(GCC) $(VULN_FLAGS) $< -o $@

05_format_string: 05_format_string.c
	$(GCC) $(VULN_FLAGS) $< -o $@

06_rop_chain: 06_rop_chain.c
	$(GCC) $(VULN_FLAGS) $< -o $@

# C targets — hardened
07_stripped: 07_stripped.c
	$(GCC) $(STRIPPED_FLAGS) $< -o $@

08_static_pie: 08_static_pie.c
	$(GCC) $(HARDENED_FLAGS) $< -o $@

clean:
	rm -f $(TARGETS) *.o
