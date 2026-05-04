; 09_syscalls.asm — Multiple syscalls, stack operations
; Tests: ASM stepping, register changes per instruction, stack view, memory view
section .bss
    buffer resb 64

section .data
    prompt db "Type something: ", 0
    prompt_len equ $ - prompt
    echo_prefix db "You typed: ", 0
    echo_len equ $ - echo_prefix

section .text
    global _start

_start:
    ; write prompt
    mov rax, 1
    mov rdi, 1
    lea rsi, [rel prompt]
    mov rdx, prompt_len
    syscall

    ; read input
    mov rax, 0          ; sys_read
    mov rdi, 0          ; stdin
    lea rsi, [rel buffer]
    mov rdx, 63
    syscall
    mov r12, rax        ; save bytes read

    ; write prefix
    mov rax, 1
    mov rdi, 1
    lea rsi, [rel echo_prefix]
    mov rdx, echo_len
    syscall

    ; echo input back
    mov rax, 1
    mov rdi, 1
    lea rsi, [rel buffer]
    mov rdx, r12
    syscall

    ; push/pop dance for stack view testing
    push 0xDEADBEEF
    push 0xCAFEBABE
    push 0x41414141
    pop rax
    pop rbx
    pop rcx

    ; exit
    mov rax, 60
    xor rdi, rdi
    syscall
