/**
 * Pwntools + Python stdlib completion provider for Monaco Editor.
 * Registers once via `registerPwnCompletions(monaco)`.
 */

import type * as Monaco from 'monaco-editor'

/* ═══════════════════════════════════════════════════════════
   pwntools API completions
   ═══════════════════════════════════════════════════════════ */

interface PwnItem {
  label: string
  insert: string
  detail: string
  doc?: string
  kind: 'function' | 'class' | 'constant' | 'snippet' | 'keyword' | 'module'
}

const PWN_ITEMS: PwnItem[] = [
  // ── Imports & setup ──
  { label: 'from pwn import *', insert: 'from pwn import *', detail: 'Import all pwntools', kind: 'snippet' },
  { label: 'context', insert: 'context', detail: 'pwntools global context', kind: 'class' },
  { label: 'context.arch', insert: "context.arch = '${1|amd64,i386,arm,aarch64,mips|}'", detail: 'Set architecture', kind: 'snippet' },
  { label: 'context.os', insert: "context.os = '${1|linux,freebsd,windows|}'", detail: 'Set OS', kind: 'snippet' },
  { label: 'context.log_level', insert: "context.log_level = '${1|debug,info,warn,error|}'", detail: 'Set log level', kind: 'snippet' },
  { label: 'context.binary', insert: 'context.binary = ${1:elf}', detail: 'Set binary context', kind: 'snippet' },

  // ── ELF ──
  { label: 'ELF', insert: "ELF('${1:./binary}')", detail: 'Load ELF binary', kind: 'class', doc: 'ELF(path, checksec=True) → ELF object with symbols, GOT, PLT, etc.' },
  { label: 'elf.symbols', insert: "elf.symbols['${1:main}']", detail: 'Get symbol address', kind: 'function' },
  { label: 'elf.got', insert: "elf.got['${1:puts}']", detail: 'Get GOT entry', kind: 'function' },
  { label: 'elf.plt', insert: "elf.plt['${1:puts}']", detail: 'Get PLT entry', kind: 'function' },
  { label: 'elf.bss', insert: 'elf.bss(${1:0})', detail: 'Get BSS address + offset', kind: 'function' },
  { label: 'elf.address', insert: 'elf.address', detail: 'Base address of ELF', kind: 'constant' },
  { label: 'elf.entry', insert: 'elf.entry', detail: 'Entry point address', kind: 'constant' },
  { label: 'elf.search', insert: "next(elf.search(${1:b'/bin/sh'}))", detail: 'Search for bytes in ELF', kind: 'function' },

  // ── Process / Remote ──
  { label: 'process', insert: "process('${1:./binary}')", detail: 'Spawn local process', kind: 'function', doc: 'process(argv, env=None, stdin=PIPE, ...) → tube' },
  { label: 'remote', insert: "remote('${1:host}', ${2:port})", detail: 'Connect to remote', kind: 'function' },
  { label: 'gdb.debug', insert: "gdb.debug('${1:./binary}', '''\n    break main\n    continue\n''')", detail: 'Debug with GDB', kind: 'function' },
  { label: 'gdb.attach', insert: 'gdb.attach(${1:p})', detail: 'Attach GDB to process', kind: 'function' },
  { label: 'ssh', insert: "ssh(host='${1:host}', user='${2:user}', password='${3:pass}')", detail: 'SSH connection', kind: 'function' },

  // ── Tube I/O ──
  { label: 'send', insert: 'send(${1:payload})', detail: 'Send data', kind: 'function' },
  { label: 'sendline', insert: 'sendline(${1:payload})', detail: 'Send data + newline', kind: 'function' },
  { label: 'sendafter', insert: "sendafter(${1:b'prompt'}, ${2:payload})", detail: 'Send after receiving', kind: 'function' },
  { label: 'sendlineafter', insert: "sendlineafter(${1:b'prompt'}, ${2:payload})", detail: 'Send line after receiving', kind: 'function' },
  { label: 'recv', insert: 'recv(${1:4096})', detail: 'Receive n bytes', kind: 'function' },
  { label: 'recvline', insert: 'recvline()', detail: 'Receive until newline', kind: 'function' },
  { label: 'recvuntil', insert: "recvuntil(${1:b'> '})", detail: 'Receive until delimiter', kind: 'function' },
  { label: 'recvall', insert: 'recvall()', detail: 'Receive all output', kind: 'function' },
  { label: 'interactive', insert: 'interactive()', detail: 'Switch to interactive mode', kind: 'function' },
  { label: 'close', insert: 'close()', detail: 'Close connection', kind: 'function' },
  { label: 'clean', insert: 'clean()', detail: 'Discard buffered data', kind: 'function' },

  // ── Packing ──
  { label: 'p64', insert: 'p64(${1:addr})', detail: 'Pack 64-bit little-endian', kind: 'function' },
  { label: 'p32', insert: 'p32(${1:addr})', detail: 'Pack 32-bit little-endian', kind: 'function' },
  { label: 'p16', insert: 'p16(${1:value})', detail: 'Pack 16-bit little-endian', kind: 'function' },
  { label: 'p8', insert: 'p8(${1:value})', detail: 'Pack 8-bit', kind: 'function' },
  { label: 'u64', insert: 'u64(${1:data})', detail: 'Unpack 64-bit little-endian', kind: 'function' },
  { label: 'u32', insert: 'u32(${1:data})', detail: 'Unpack 32-bit little-endian', kind: 'function' },
  { label: 'flat', insert: 'flat(${1:values})', detail: 'Flatten list to packed bytes', kind: 'function' },
  { label: 'fit', insert: 'fit(${1:dict})', detail: 'Fit dict of offset → value', kind: 'function' },

  // ── Cyclic ──
  { label: 'cyclic', insert: 'cyclic(${1:200})', detail: 'Generate cyclic pattern', kind: 'function' },
  { label: 'cyclic_find', insert: 'cyclic_find(${1:value})', detail: 'Find offset in cyclic pattern', kind: 'function' },

  // ── ROP ──
  { label: 'ROP', insert: 'ROP(${1:elf})', detail: 'Create ROP chain builder', kind: 'class', doc: 'ROP(elfs, base=None) → ROP object for building chains' },
  { label: 'rop.find_gadget', insert: "rop.find_gadget(['${1:pop rdi}', '${2:ret}'])", detail: 'Find gadget by instructions', kind: 'function' },
  { label: 'rop.chain', insert: 'rop.chain()', detail: 'Build ROP chain bytes', kind: 'function' },
  { label: 'rop.dump', insert: 'rop.dump()', detail: 'Print ROP chain', kind: 'function' },
  { label: 'rop.call', insert: "rop.call('${1:system}', [${2:next(elf.search(b'/bin/sh'))}])", detail: 'Add function call to chain', kind: 'function' },
  { label: 'rop.raw', insert: 'rop.raw(${1:gadget_addr})', detail: 'Add raw address to chain', kind: 'function' },
  { label: 'rop.ret', insert: 'rop.raw(rop.ret)', detail: 'Add ret sled for alignment', kind: 'snippet' },

  // ── Format string ──
  { label: 'FmtStr', insert: 'FmtStr(${1:exec_fmt})', detail: 'Format string automator', kind: 'class' },
  { label: 'fmtstr_payload', insert: 'fmtstr_payload(${1:offset}, {${2:addr}: ${3:value}})', detail: 'Generate fmt string payload', kind: 'function' },

  // ── Shellcraft ──
  { label: 'shellcraft.sh', insert: 'shellcraft.sh()', detail: 'execve("/bin/sh") shellcode', kind: 'function' },
  { label: 'shellcraft.cat', insert: "shellcraft.cat('${1:flag.txt}')", detail: 'cat(filename) shellcode', kind: 'function' },
  { label: 'shellcraft.nop', insert: 'shellcraft.nop()', detail: 'NOP instruction', kind: 'function' },
  { label: 'shellcraft.connect', insert: "shellcraft.connect('${1:host}', ${2:port})", detail: 'Connect-back shellcode', kind: 'function' },

  // ── Assembly ──
  { label: 'asm', insert: "asm('${1:nop}')", detail: 'Assemble instruction(s)', kind: 'function' },
  { label: 'disasm', insert: 'disasm(${1:shellcode})', detail: 'Disassemble bytes', kind: 'function' },

  // ── Encoding ──
  { label: 'xor', insert: 'xor(${1:data}, ${2:key})', detail: 'XOR encode bytes', kind: 'function' },
  { label: 'b64e', insert: 'b64e(${1:data})', detail: 'Base64 encode', kind: 'function' },
  { label: 'b64d', insert: 'b64d(${1:data})', detail: 'Base64 decode', kind: 'function' },
  { label: 'enhex', insert: 'enhex(${1:data})', detail: 'Bytes to hex string', kind: 'function' },
  { label: 'unhex', insert: "unhex('${1:hex}')", detail: 'Hex string to bytes', kind: 'function' },
  { label: 'urlencode', insert: 'urlencode(${1:data})', detail: 'URL-encode bytes', kind: 'function' },

  // ── Logging / Utility ──
  { label: 'log.info', insert: "log.info('${1:message}')", detail: 'Log info message', kind: 'function' },
  { label: 'log.success', insert: "log.success('${1:message}')", detail: 'Log success message', kind: 'function' },
  { label: 'log.warning', insert: "log.warning('${1:message}')", detail: 'Log warning', kind: 'function' },
  { label: 'log.error', insert: "log.error('${1:message}')", detail: 'Log error', kind: 'function' },
  { label: 'success', insert: "success('${1:message}')", detail: 'Print success', kind: 'function' },
  { label: 'info', insert: "info('${1:message}')", detail: 'Print info', kind: 'function' },
  { label: 'warn', insert: "warn('${1:message}')", detail: 'Print warning', kind: 'function' },
  { label: 'pause', insert: 'pause()', detail: 'Pause execution', kind: 'function' },
  { label: 'sleep', insert: 'sleep(${1:1})', detail: 'Sleep n seconds', kind: 'function' },
  { label: 'hexdump', insert: 'hexdump(${1:data})', detail: 'Pretty hex dump', kind: 'function' },

  // ── Snippets ──
  { label: 'exploit template', insert: `#!/usr/bin/env python3
from pwn import *

context.arch = 'amd64'
context.os = 'linux'
context.log_level = 'info'

binary = './\${1:vuln}'
elf = ELF(binary)
rop = ROP(elf)

def exploit():
    p = process(binary)
    # p = remote('host', port)

    \${2:# payload here}

    p.interactive()

if __name__ == '__main__':
    exploit()`, detail: 'Full exploit template', kind: 'snippet' },
  { label: 'ret2libc template', insert: `# ret2libc
libc = ELF('\${1:/lib/x86_64-linux-gnu/libc.so.6}')
puts_got = elf.got['puts']
puts_plt = elf.plt['puts']
main = elf.symbols['main']
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret = rop.find_gadget(['ret'])[0]

# Leak libc
payload = b'A' * \${2:offset}
payload += p64(pop_rdi) + p64(puts_got) + p64(puts_plt) + p64(main)
p.sendline(payload)
leak = u64(p.recvline().strip().ljust(8, b'\\x00'))
libc.address = leak - libc.symbols['puts']
log.success(f'libc base: {hex(libc.address)}')

# System("/bin/sh")
payload = b'A' * \${2:offset}
payload += p64(ret) + p64(pop_rdi) + p64(next(libc.search(b'/bin/sh'))) + p64(libc.symbols['system'])
p.sendline(payload)`, detail: 'ret2libc exploit', kind: 'snippet' },
]

/* ═══════════════════════════════════════════════════════════
   Python stdlib completions
   ═══════════════════════════════════════════════════════════ */

const PYTHON_ITEMS: PwnItem[] = [
  // ── Built-in types/functions ──
  { label: 'print', insert: 'print(${1:value})', detail: 'Print to stdout', kind: 'function' },
  { label: 'len', insert: 'len(${1:obj})', detail: 'Length of object', kind: 'function' },
  { label: 'range', insert: 'range(${1:n})', detail: 'Range iterator', kind: 'function' },
  { label: 'enumerate', insert: 'enumerate(${1:iterable})', detail: 'Enumerate with index', kind: 'function' },
  { label: 'zip', insert: 'zip(${1:a}, ${2:b})', detail: 'Zip iterables', kind: 'function' },
  { label: 'map', insert: 'map(${1:func}, ${2:iterable})', detail: 'Map function', kind: 'function' },
  { label: 'filter', insert: 'filter(${1:func}, ${2:iterable})', detail: 'Filter iterable', kind: 'function' },
  { label: 'sorted', insert: 'sorted(${1:iterable})', detail: 'Sort iterable', kind: 'function' },
  { label: 'reversed', insert: 'reversed(${1:seq})', detail: 'Reverse sequence', kind: 'function' },
  { label: 'int', insert: 'int(${1:value})', detail: 'Convert to int', kind: 'function' },
  { label: 'str', insert: 'str(${1:value})', detail: 'Convert to string', kind: 'function' },
  { label: 'bytes', insert: 'bytes(${1:value})', detail: 'Create bytes', kind: 'function' },
  { label: 'bytearray', insert: 'bytearray(${1:value})', detail: 'Mutable byte array', kind: 'function' },
  { label: 'hex', insert: 'hex(${1:n})', detail: 'Int to hex string', kind: 'function' },
  { label: 'oct', insert: 'oct(${1:n})', detail: 'Int to octal string', kind: 'function' },
  { label: 'bin', insert: 'bin(${1:n})', detail: 'Int to binary string', kind: 'function' },
  { label: 'chr', insert: 'chr(${1:code})', detail: 'Codepoint to char', kind: 'function' },
  { label: 'ord', insert: "ord('${1:c}')", detail: 'Char to codepoint', kind: 'function' },
  { label: 'isinstance', insert: 'isinstance(${1:obj}, ${2:type})', detail: 'Type check', kind: 'function' },
  { label: 'type', insert: 'type(${1:obj})', detail: 'Get type', kind: 'function' },
  { label: 'dir', insert: 'dir(${1:obj})', detail: 'List attributes', kind: 'function' },
  { label: 'hasattr', insert: "hasattr(${1:obj}, '${2:attr}')", detail: 'Check attribute', kind: 'function' },
  { label: 'getattr', insert: "getattr(${1:obj}, '${2:attr}')", detail: 'Get attribute', kind: 'function' },
  { label: 'setattr', insert: "setattr(${1:obj}, '${2:attr}', ${3:value})", detail: 'Set attribute', kind: 'function' },
  { label: 'open', insert: "open('${1:file}', '${2|r,rb,w,wb|}')", detail: 'Open file', kind: 'function' },
  { label: 'input', insert: "input('${1:prompt}')", detail: 'Read user input', kind: 'function' },
  { label: 'abs', insert: 'abs(${1:n})', detail: 'Absolute value', kind: 'function' },
  { label: 'max', insert: 'max(${1:iterable})', detail: 'Maximum value', kind: 'function' },
  { label: 'min', insert: 'min(${1:iterable})', detail: 'Minimum value', kind: 'function' },
  { label: 'sum', insert: 'sum(${1:iterable})', detail: 'Sum of iterable', kind: 'function' },
  { label: 'list', insert: 'list(${1:iterable})', detail: 'Create list', kind: 'function' },
  { label: 'dict', insert: 'dict(${1:})', detail: 'Create dict', kind: 'function' },
  { label: 'set', insert: 'set(${1:iterable})', detail: 'Create set', kind: 'function' },
  { label: 'tuple', insert: 'tuple(${1:iterable})', detail: 'Create tuple', kind: 'function' },

  // ── Keywords ──
  ...['if', 'elif', 'else', 'for', 'while', 'break', 'continue', 'return', 'yield',
    'def', 'class', 'import', 'from', 'as', 'try', 'except', 'finally', 'raise',
    'with', 'pass', 'lambda', 'global', 'nonlocal', 'assert', 'del', 'in', 'not',
    'and', 'or', 'is', 'None', 'True', 'False',
  ].map(k => ({ label: k, insert: k, detail: 'Python keyword', kind: 'keyword' as const })),

  // ── Common stdlib modules ──
  { label: 'import struct', insert: 'import struct', detail: 'Binary packing module', kind: 'module' },
  { label: 'import os', insert: 'import os', detail: 'OS interface', kind: 'module' },
  { label: 'import sys', insert: 'import sys', detail: 'System module', kind: 'module' },
  { label: 'import re', insert: 'import re', detail: 'Regex module', kind: 'module' },
  { label: 'import socket', insert: 'import socket', detail: 'Socket module', kind: 'module' },
  { label: 'import subprocess', insert: 'import subprocess', detail: 'Subprocess module', kind: 'module' },
  { label: 'import json', insert: 'import json', detail: 'JSON module', kind: 'module' },
  { label: 'import base64', insert: 'import base64', detail: 'Base64 module', kind: 'module' },
  { label: 'import hashlib', insert: 'import hashlib', detail: 'Hashing module', kind: 'module' },
  { label: 'import itertools', insert: 'import itertools', detail: 'Iterator tools', kind: 'module' },
  { label: 'import collections', insert: 'import collections', detail: 'Container types', kind: 'module' },
  { label: 'import time', insert: 'import time', detail: 'Time module', kind: 'module' },

  // ── struct (common for pwn) ──
  { label: 'struct.pack', insert: "struct.pack('${1:<Q}', ${2:value})", detail: 'Pack binary data', kind: 'function' },
  { label: 'struct.unpack', insert: "struct.unpack('${1:<Q}', ${2:data})", detail: 'Unpack binary data', kind: 'function' },

  // ── Common string/bytes methods ──
  { label: '.encode', insert: ".encode('${1:utf-8}')", detail: 'Str to bytes', kind: 'function' },
  { label: '.decode', insert: ".decode('${1:utf-8}')", detail: 'Bytes to str', kind: 'function' },
  { label: '.strip', insert: '.strip()', detail: 'Strip whitespace', kind: 'function' },
  { label: '.split', insert: ".split('${1: }')", detail: 'Split string', kind: 'function' },
  { label: '.join', insert: ".join(${1:iterable})", detail: 'Join strings', kind: 'function' },
  { label: '.replace', insert: ".replace('${1:old}', '${2:new}')", detail: 'Replace substring', kind: 'function' },
  { label: '.find', insert: ".find('${1:sub}')", detail: 'Find substring index', kind: 'function' },
  { label: '.ljust', insert: '.ljust(${1:width}, ${2:b"\\x00"})', detail: 'Left-justify / pad', kind: 'function' },
  { label: '.rjust', insert: '.rjust(${1:width}, ${2:b"\\x00"})', detail: 'Right-justify / pad', kind: 'function' },
  { label: '.hex', insert: '.hex()', detail: 'Bytes to hex', kind: 'function' },
]

/* ═══════════════════════════════════════════════════════════
   Registration
   ═══════════════════════════════════════════════════════════ */

const ALL_ITEMS = [...PWN_ITEMS, ...PYTHON_ITEMS]

function toMonacoKind(k: PwnItem['kind'], kinds: typeof Monaco.languages.CompletionItemKind): Monaco.languages.CompletionItemKind {
  switch (k) {
    case 'function': return kinds.Function
    case 'class': return kinds.Class
    case 'constant': return kinds.Constant
    case 'snippet': return kinds.Snippet
    case 'keyword': return kinds.Keyword
    case 'module': return kinds.Module
    default: return kinds.Text
  }
}

let _registered = false

export function registerPwnCompletions(monaco: typeof Monaco): void {
  if (_registered) return
  _registered = true

  monaco.languages.registerCompletionItemProvider('python', {
    triggerCharacters: ['.', ' ', '(', "'", '"'],
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endLineNumber: position.lineNumber,
        endColumn: word.endColumn,
      }

      // Get the text of the current line up to cursor for context
      const lineContent = model.getLineContent(position.lineNumber)
      const textBefore = lineContent.substring(0, position.column - 1)

      // Filter suggestions based on context
      const suggestions = ALL_ITEMS
        .filter(item => {
          // After a dot, only show method completions
          if (textBefore.endsWith('.')) {
            return item.label.startsWith('.')
          }
          // Don't show dot methods without a dot
          if (item.label.startsWith('.')) return false
          return true
        })
        .map((item, idx) => ({
          label: item.label,
          kind: toMonacoKind(item.kind, monaco.languages.CompletionItemKind),
          insertText: item.insert,
          insertTextRules: item.insert.includes('${')
            ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
            : undefined,
          detail: item.detail,
          documentation: item.doc,
          range,
          sortText: String(idx).padStart(4, '0'),
        }))

      return { suggestions }
    },
  })
}
