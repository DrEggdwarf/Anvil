# Anvil — Vulnerable test binaries for Pwn mode
# Compiled with protections disabled for exploitation practice

CC      = gcc
CXX     = g++
CFLAGS  = -g -no-pie -fno-stack-protector -z execstack -Wno-deprecated-declarations
CXXFLAGS = -g -no-pie -fno-stack-protector -z execstack
LDFLAGS =

TARGETS = bof_basic fmt_string ret2libc use_after_free bof_cpp

.PHONY: all clean go rust

all: $(TARGETS)
	@echo "✓ All C/C++ targets built"

bof_basic: bof_basic.c
	$(CC) $(CFLAGS) -o $@ $<

fmt_string: fmt_string.c
	$(CC) $(CFLAGS) -o $@ $<

ret2libc: ret2libc.c
	$(CC) -g -no-pie -fno-stack-protector -o $@ $<

use_after_free: use_after_free.c
	$(CC) $(CFLAGS) -o $@ $<

bof_cpp: bof_cpp.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

go: bof_go.go
	CGO_ENABLED=1 go build -o bof_go bof_go.go
	@echo "✓ Go target built"

rust: bof_rust.rs
	rustc -g -o bof_rust bof_rust.rs
	@echo "✓ Rust target built"

clean:
	rm -f $(TARGETS) bof_go bof_rust *.o
