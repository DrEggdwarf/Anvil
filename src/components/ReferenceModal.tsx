import { useState, useMemo } from 'react'
import {
  // ASM
  SYSCALLS_FULL, INSTRUCTIONS_FULL, SYSV_ABI, SYSCALL_CONVENTION,
  FUNC_CONVENTION, STACK_LAYOUT, NASM_DIRECTIVES, ASM_PATTERNS,
  // RE
  RIZIN_CMDS, RIZIN_CATS, ELF_FORMAT, ELF_SECTIONS, RE_PATTERNS,
  // Pwn
  PROTECTIONS, FORMAT_STRING_REF, PWNTOOLS_CHEATSHEET, PWN_TECHNIQUES,
  // Debug
  GDB_CMDS, GDB_CATS, PWNDBG_CMDS, GDB_EXAMINE_FORMATS,
  // Firmware
  BINWALK_OPTS, BINWALK_CATS, MAGIC_SIGNATURES, ENTROPY_GUIDE, FW_PATTERNS,
  // Protocols
  MODBUS_FUNCTIONS, MODBUS_REG_TYPES, MODBUS_EXCEPTIONS, MODBUS_FRAME, PROTOCOL_PATTERNS,
} from '../data'
import type {
  Syscall, LexiconInstr, RegRole, DirectiveInfo,
  RizinCmd, GdbCmd, BinwalkOpt, ModbusFunc, ModbusRegType,
} from '../data'

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */

export type AppMode = 'asm' | 're' | 'pwn' | 'dbg' | 'fw' | 'hw'

interface ReferenceModalProps {
  open: boolean
  onClose: () => void
  mode: AppMode
}

interface TabDef { id: string; label: string; icon: string }

interface FilterBarProps {
  cats: string[]; active: string; onChange: (c: string) => void; count: number; label: string
}

interface SearchProps { search: string }

interface PatternsViewProps {
  patterns: { name: string; desc: string; code: string[] }[]
}

interface TabContentProps { tabId: string; search: string }

const MODE_TITLES: Record<AppMode, string> = {
  asm: 'Reference x86-64',
  re: 'Reference Reverse Engineering',
  pwn: 'Reference Exploitation',
  dbg: 'Reference Debug (GDB)',
  fw: 'Reference Firmware',
  hw: 'Reference Protocoles',
}

const MODE_TABS: Record<AppMode, TabDef[]> = {
  asm: [
    { id: 'syscalls', label: 'Syscalls', icon: 'fa-terminal' },
    { id: 'instructions', label: 'Instructions', icon: 'fa-microchip' },
    { id: 'conventions', label: 'ABI', icon: 'fa-handshake' },
    { id: 'directives', label: 'Directives', icon: 'fa-code' },
    { id: 'patterns', label: 'Patterns', icon: 'fa-puzzle-piece' },
  ],
  re: [
    { id: 'rizin', label: 'Commandes', icon: 'fa-terminal' },
    { id: 'elf-format', label: 'ELF', icon: 'fa-file-code' },
    { id: 'elf-sections', label: 'Sections', icon: 'fa-layer-group' },
    { id: 're-patterns', label: 'Patterns', icon: 'fa-puzzle-piece' },
  ],
  pwn: [
    { id: 'protections', label: 'Protections', icon: 'fa-shield-halved' },
    { id: 'techniques', label: 'Techniques', icon: 'fa-crosshairs' },
    { id: 'fmtstr', label: 'Format String', icon: 'fa-percent' },
    { id: 'pwntools', label: 'pwntools', icon: 'fa-screwdriver-wrench' },
    { id: 'syscalls', label: 'Syscalls', icon: 'fa-terminal' },
  ],
  dbg: [
    { id: 'gdb', label: 'GDB', icon: 'fa-terminal' },
    { id: 'pwndbg', label: 'pwndbg', icon: 'fa-bug' },
    { id: 'examine', label: 'x/ Format', icon: 'fa-magnifying-glass' },
    { id: 'conventions', label: 'ABI', icon: 'fa-handshake' },
  ],
  fw: [
    { id: 'binwalk', label: 'Binwalk', icon: 'fa-terminal' },
    { id: 'signatures', label: 'Signatures', icon: 'fa-fingerprint' },
    { id: 'entropy', label: 'Entropie', icon: 'fa-chart-area' },
    { id: 'fw-patterns', label: 'Patterns', icon: 'fa-puzzle-piece' },
  ],
  hw: [
    { id: 'modbus-func', label: 'Fonctions', icon: 'fa-list-ol' },
    { id: 'modbus-regs', label: 'Registres', icon: 'fa-table-cells' },
    { id: 'modbus-errors', label: 'Exceptions', icon: 'fa-triangle-exclamation' },
    { id: 'modbus-frame', label: 'Trames', icon: 'fa-diagram-project' },
    { id: 'hw-patterns', label: 'Patterns', icon: 'fa-puzzle-piece' },
  ],
}

/* ═══════════════════════════════════════════════════════════════
   Shared sub-components
   ═══════════════════════════════════════════════════════════════ */

function FilterBar({ cats, active, onChange, count, label }: FilterBarProps) {
  return (
    <div className="anvil-ref-filters">
      {cats.map(c => (
        <button key={c} className={`anvil-ref-filter ${active === c ? 'active' : ''}`}
          onClick={() => onChange(c)}>{c}</button>
      ))}
      <span className="anvil-ref-count">{count} {label}</span>
    </div>
  )
}

function PatternsView({ patterns }: PatternsViewProps) {
  return (
    <div className="anvil-ref-content anvil-ref-patterns">
      {patterns.map((p, i) => (
        <div key={i} className="anvil-ref-pattern">
          <div className="anvil-ref-pattern-header">
            <span className="anvil-ref-pattern-name">{p.name}</span>
            <span className="anvil-ref-pattern-desc">{p.desc}</span>
          </div>
          <pre className="anvil-ref-pre">{p.code.join('\n')}</pre>
        </div>
      ))}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   ASM tabs
   ═══════════════════════════════════════════════════════════════ */

const SYSCALL_CATS = [
  { label: 'Tout', filter: '' },
  { label: 'File I/O', filter: 'file' },
  { label: 'Memory', filter: 'mem' },
  { label: 'Process', filter: 'proc' },
  { label: 'Socket', filter: 'sock' },
  { label: 'Signal', filter: 'sig' },
  { label: 'Time', filter: 'time' },
  { label: 'System', filter: 'sys' },
]

function categorizeSyscall(s: Syscall): string {
  const n = s.name
  if (['socket', 'connect', 'accept', 'accept4', 'sendto', 'recvfrom', 'sendmsg', 'recvmsg',
    'shutdown', 'bind', 'listen', 'getsockname', 'getpeername', 'socketpair',
    'setsockopt', 'getsockopt'].includes(n)) return 'sock'
  if (n.includes('sig') || n === 'kill' || n === 'tkill' || n === 'pause') return 'sig'
  if (['mmap', 'munmap', 'mprotect', 'mremap', 'msync', 'mincore', 'madvise', 'brk', 'mbind',
    'shmget', 'shmat', 'shmctl', 'shmdt'].includes(n)) return 'mem'
  if (['fork', 'vfork', 'clone', 'clone3', 'execve', 'execveat', 'exit', 'exit_group',
    'wait4', 'getpid', 'getppid', 'gettid', 'getuid', 'getgid', 'geteuid', 'getegid',
    'setuid', 'setgid', 'setpgid', 'setsid', 'prctl', 'ptrace', 'futex',
    'sched_setaffinity', 'sched_getaffinity', 'sched_yield', 'set_tid_address',
    'set_robust_list', 'seccomp', 'capget', 'capset', 'unshare', 'setns',
    'pidfd_open', 'pidfd_send_signal'].includes(n)) return 'proc'
  if (['nanosleep', 'getitimer', 'setitimer', 'alarm', 'gettimeofday',
    'clock_gettime', 'clock_getres', 'clock_nanosleep', 'times',
    'timerfd_create', 'timerfd_settime', 'timerfd_gettime'].includes(n)) return 'time'
  if (s.num <= 100 || n.includes('at') || ['sendfile', 'dup', 'dup2', 'dup3',
    'pipe', 'pipe2', 'fcntl', 'flock', 'fsync', 'fdatasync', 'truncate',
    'ftruncate', 'getdents', 'getcwd', 'chdir', 'fchdir', 'rename',
    'mkdir', 'rmdir', 'creat', 'link', 'unlink', 'symlink', 'readlink',
    'chmod', 'fchmod', 'chown', 'fchown', 'lchown', 'chroot',
    'mount', 'umount2', 'statfs', 'fstatfs', 'inotify_init',
    'inotify_add_watch', 'inotify_rm_watch', 'eventfd', 'signalfd',
    'memfd_create'].includes(n)) return 'file'
  return 'sys'
}

function SyscallsTab({ search }: SearchProps) {
  const [cat, setCat] = useState('')
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return SYSCALLS_FULL.filter(s => {
      if (cat && categorizeSyscall(s) !== cat) return false
      if (q && !s.name.includes(q) && !s.desc.toLowerCase().includes(q) && !String(s.num).includes(q)) return false
      return true
    })
  }, [search, cat])

  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-filters">
        {SYSCALL_CATS.map(c => (
          <button key={c.label} className={`anvil-ref-filter ${cat === c.filter ? 'active' : ''}`}
            onClick={() => setCat(c.filter)}>{c.label}</button>
        ))}
        <span className="anvil-ref-count">{filtered.length} syscalls</span>
      </div>
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>#</th><th>Name</th><th>Arguments</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map(s => (
              <tr key={`${s.num}-${s.name}`}>
                <td className="anvil-ref-num">{s.num}</td>
                <td className="anvil-ref-name">{s.name}</td>
                <td className="anvil-ref-args">{s.args}</td>
                <td className="anvil-ref-desc">{s.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const INSTR_CATS = ['Tout', 'Donnees', 'Arithmetique', 'Logique', 'Sauts', 'Fonctions', 'Chaines', 'Systeme', 'SIMD']

function InstructionsTab({ search }: SearchProps) {
  const [cat, setCat] = useState('Tout')
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return INSTRUCTIONS_FULL.filter(i => {
      if (cat !== 'Tout' && i.cat !== cat) return false
      if (q && !i.name.toLowerCase().includes(q) && !i.desc.toLowerCase().includes(q)) return false
      return true
    })
  }, [search, cat])

  return (
    <div className="anvil-ref-content">
      <FilterBar cats={INSTR_CATS} active={cat} onChange={setCat} count={filtered.length} label="instructions" />
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Cat</th><th>Instruction</th><th>Syntaxe</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((i: LexiconInstr, idx: number) => (
              <tr key={idx}>
                <td className="anvil-ref-cat-badge">{i.cat}</td>
                <td className="anvil-ref-name">{i.name}</td>
                <td className="anvil-ref-syntax">{i.syntax}</td>
                <td className="anvil-ref-desc">{i.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ConventionsTab() {
  return (
    <div className="anvil-ref-content anvil-ref-abi">
      <h3 className="anvil-ref-h3"><i className="fa-solid fa-list-check" /> Registres — Roles System V AMD64</h3>
      <table className="anvil-ref-table">
        <thead><tr><th>Registre</th><th>Role</th><th>Sauvegarde</th><th>Detail</th></tr></thead>
        <tbody>
          {SYSV_ABI.map((r: RegRole) => (
            <tr key={r.reg}>
              <td className="anvil-ref-name">{r.reg}</td>
              <td className="anvil-ref-args">{r.role}</td>
              <td className={r.callerSaved ? 'anvil-ref-caller' : 'anvil-ref-callee'}>
                {r.callerSaved ? 'Caller-saved' : 'Callee-saved'}
              </td>
              <td className="anvil-ref-desc">{r.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 className="anvil-ref-h3"><i className="fa-solid fa-terminal" /> {SYSCALL_CONVENTION.title}</h3>
      <div className="anvil-ref-box">
        <div className="anvil-ref-box-label">Mecanisme</div>
        <div className="anvil-ref-box-val">{SYSCALL_CONVENTION.mechanism}</div>
        <div className="anvil-ref-box-label">Numero</div>
        <div className="anvil-ref-box-val anvil-ref-code">{SYSCALL_CONVENTION.number}</div>
        <div className="anvil-ref-box-label">Arguments</div>
        <div className="anvil-ref-box-val">{SYSCALL_CONVENTION.args.map((a, i) => <div key={i} className="anvil-ref-code">{a}</div>)}</div>
        <div className="anvil-ref-box-label">Retour</div>
        <div className="anvil-ref-box-val anvil-ref-code">{SYSCALL_CONVENTION.ret}</div>
        <div className="anvil-ref-box-label">Detruits</div>
        <div className="anvil-ref-box-val">{SYSCALL_CONVENTION.clobbered.join(', ')}</div>
        <div className="anvil-ref-box-label">Notes</div>
        <div className="anvil-ref-box-val">{SYSCALL_CONVENTION.notes.map((n, i) => <div key={i}>• {n}</div>)}</div>
      </div>

      <h3 className="anvil-ref-h3"><i className="fa-solid fa-right-left" /> {FUNC_CONVENTION.title}</h3>
      <div className="anvil-ref-box">
        <div className="anvil-ref-box-label">Args entiers</div>
        <div className="anvil-ref-box-val anvil-ref-code">{FUNC_CONVENTION.args_int.join(' → ')}</div>
        <div className="anvil-ref-box-label">Args float</div>
        <div className="anvil-ref-box-val anvil-ref-code">{FUNC_CONVENTION.args_float.join(' → ')}</div>
        <div className="anvil-ref-box-label">Retour</div>
        <div className="anvil-ref-box-val anvil-ref-code">{FUNC_CONVENTION.ret_int}</div>
        <div className="anvil-ref-box-label">Caller-saved</div>
        <div className="anvil-ref-box-val anvil-ref-caller">{FUNC_CONVENTION.callerSaved.join(', ')}</div>
        <div className="anvil-ref-box-label">Callee-saved</div>
        <div className="anvil-ref-box-val anvil-ref-callee">{FUNC_CONVENTION.calleeSaved.join(', ')}</div>
        <div className="anvil-ref-box-label">Stack align</div>
        <div className="anvil-ref-box-val">{FUNC_CONVENTION.stackAlign}</div>
        <div className="anvil-ref-box-label">Red Zone</div>
        <div className="anvil-ref-box-val">{FUNC_CONVENTION.redZone}</div>
        <div className="anvil-ref-box-label">Notes</div>
        <div className="anvil-ref-box-val">{FUNC_CONVENTION.notes.map((n, i) => <div key={i}>• {n}</div>)}</div>
      </div>

      <h3 className="anvil-ref-h3"><i className="fa-solid fa-layer-group" /> {STACK_LAYOUT.title}</h3>
      <pre className="anvil-ref-diagram">{STACK_LAYOUT.diagram.join('\n')}</pre>
      <div className="anvil-ref-code-block">
        <div className="anvil-ref-box-label">Prologue</div>
        <pre className="anvil-ref-pre">{STACK_LAYOUT.prologue.join('\n')}</pre>
        <div className="anvil-ref-box-label">Epilogue</div>
        <pre className="anvil-ref-pre">{STACK_LAYOUT.epilogue.join('\n')}</pre>
      </div>
    </div>
  )
}

function DirectivesTab({ search }: SearchProps) {
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return NASM_DIRECTIVES.filter((d: DirectiveInfo) =>
      !q || d.name.toLowerCase().includes(q) || d.desc.toLowerCase().includes(q)
    )
  }, [search])

  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Directive</th><th>Syntaxe</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((d: DirectiveInfo) => (
              <tr key={d.name}>
                <td className="anvil-ref-name">{d.name}</td>
                <td className="anvil-ref-syntax">{d.syntax}</td>
                <td className="anvil-ref-desc">{d.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   RE tabs
   ═══════════════════════════════════════════════════════════════ */

function RizinTab({ search }: SearchProps) {
  const [cat, setCat] = useState('Tout')
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return RIZIN_CMDS.filter((c: RizinCmd) => {
      if (cat !== 'Tout' && c.cat !== cat) return false
      if (q && !c.cmd.toLowerCase().includes(q) && !c.desc.toLowerCase().includes(q)) return false
      return true
    })
  }, [search, cat])

  return (
    <div className="anvil-ref-content">
      <FilterBar cats={RIZIN_CATS} active={cat} onChange={setCat} count={filtered.length} label="commandes" />
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Cat</th><th>Commande</th><th>Args</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={i}>
                <td className="anvil-ref-cat-badge">{c.cat}</td>
                <td className="anvil-ref-name">{c.cmd}</td>
                <td className="anvil-ref-args">{c.args}</td>
                <td className="anvil-ref-desc">{c.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ElfFormatTab() {
  return (
    <div className="anvil-ref-content anvil-ref-abi">
      <h3 className="anvil-ref-h3"><i className="fa-solid fa-file-code" /> {ELF_FORMAT.name}</h3>
      <table className="anvil-ref-table">
        <thead><tr><th>Champ</th><th>Offset</th><th>Taille</th><th>Description</th></tr></thead>
        <tbody>
          {ELF_FORMAT.fields.map(f => (
            <tr key={f.field}>
              <td className="anvil-ref-name">{f.field}</td>
              <td className="anvil-ref-num">{f.offset}</td>
              <td className="anvil-ref-num">{f.size}</td>
              <td className="anvil-ref-desc">{f.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ElfSectionsTab({ search }: SearchProps) {
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return ELF_SECTIONS.filter(s => !q || s.name.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q))
  }, [search])

  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Section</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map(s => (
              <tr key={s.name}>
                <td className="anvil-ref-name">{s.name}</td>
                <td className="anvil-ref-desc">{s.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Pwn tabs
   ═══════════════════════════════════════════════════════════════ */

function ProtectionsTab() {
  return (
    <div className="anvil-ref-content anvil-ref-patterns">
      {PROTECTIONS.map((p, i) => (
        <div key={i} className="anvil-ref-pattern">
          <div className="anvil-ref-pattern-header">
            <span className="anvil-ref-pattern-name">{p.protection}</span>
            <span className="anvil-ref-pattern-desc">{p.what}</span>
          </div>
          <div className="anvil-ref-bypass-list">
            {p.bypass.map((b, j) => <div key={j} className="anvil-ref-bypass-item">→ {b}</div>)}
          </div>
        </div>
      ))}
    </div>
  )
}

function TechniquesTab() {
  return (
    <div className="anvil-ref-content anvil-ref-patterns">
      {PWN_TECHNIQUES.map((t, i) => (
        <div key={i} className="anvil-ref-pattern">
          <div className="anvil-ref-pattern-header">
            <span className="anvil-ref-pattern-name">{t.name}</span>
            <span className="anvil-ref-pattern-desc">{t.desc}</span>
          </div>
          <pre className="anvil-ref-pre">{t.steps.join('\n')}</pre>
        </div>
      ))}
    </div>
  )
}

function FmtStrTab() {
  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Specifier</th><th>Effet</th><th>Exemple</th></tr></thead>
          <tbody>
            {FORMAT_STRING_REF.map((f, i) => (
              <tr key={i}>
                <td className="anvil-ref-name">{f.specifier}</td>
                <td className="anvil-ref-desc">{f.effect}</td>
                <td className="anvil-ref-args">{f.example}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PwntoolsTab() {
  return (
    <div className="anvil-ref-content anvil-ref-patterns">
      {PWNTOOLS_CHEATSHEET.map((s, i) => (
        <div key={i} className="anvil-ref-pattern">
          <div className="anvil-ref-pattern-header">
            <span className="anvil-ref-pattern-name">{s.name}</span>
          </div>
          <pre className="anvil-ref-pre">{s.code.join('\n')}</pre>
        </div>
      ))}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Debug tabs
   ═══════════════════════════════════════════════════════════════ */

function GdbTab({ search }: SearchProps) {
  const [cat, setCat] = useState('Tout')
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return GDB_CMDS.filter((c: GdbCmd) => {
      if (cat !== 'Tout' && c.cat !== cat) return false
      if (q && !c.cmd.toLowerCase().includes(q) && !c.desc.toLowerCase().includes(q)) return false
      return true
    })
  }, [search, cat])

  return (
    <div className="anvil-ref-content">
      <FilterBar cats={GDB_CATS} active={cat} onChange={setCat} count={filtered.length} label="commandes" />
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Commande</th><th>Raccourci</th><th>Args</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={i}>
                <td className="anvil-ref-name">{c.cmd}</td>
                <td className="anvil-ref-syntax">{c.shortcut || '—'}</td>
                <td className="anvil-ref-args">{c.args}</td>
                <td className="anvil-ref-desc">{c.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PwndbgTab({ search }: SearchProps) {
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return PWNDBG_CMDS.filter(c => !q || c.cmd.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q))
  }, [search])

  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Commande</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={i}>
                <td className="anvil-ref-name">{c.cmd}</td>
                <td className="anvil-ref-desc">{c.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ExamineTab() {
  const fmt = GDB_EXAMINE_FORMATS
  return (
    <div className="anvil-ref-content anvil-ref-abi">
      <h3 className="anvil-ref-h3"><i className="fa-solid fa-magnifying-glass" /> {fmt.title}</h3>

      <h3 className="anvil-ref-h3">Formats</h3>
      <table className="anvil-ref-table">
        <thead><tr><th>Code</th><th>Format</th></tr></thead>
        <tbody>
          {fmt.formats.map(f => <tr key={f.code}><td className="anvil-ref-name">{f.code}</td><td className="anvil-ref-desc">{f.desc}</td></tr>)}
        </tbody>
      </table>

      <h3 className="anvil-ref-h3">Tailles</h3>
      <table className="anvil-ref-table">
        <thead><tr><th>Code</th><th>Taille</th></tr></thead>
        <tbody>
          {fmt.sizes.map(s => <tr key={s.code}><td className="anvil-ref-name">{s.code}</td><td className="anvil-ref-desc">{s.desc}</td></tr>)}
        </tbody>
      </table>

      <h3 className="anvil-ref-h3">Exemples</h3>
      <pre className="anvil-ref-pre">{fmt.examples.join('\n')}</pre>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Firmware tabs
   ═══════════════════════════════════════════════════════════════ */

function BinwalkTab({ search }: SearchProps) {
  const [cat, setCat] = useState('Tout')
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return BINWALK_OPTS.filter((o: BinwalkOpt) => {
      if (cat !== 'Tout' && o.cat !== cat) return false
      if (q && !o.flag.toLowerCase().includes(q) && !o.desc.toLowerCase().includes(q)) return false
      return true
    })
  }, [search, cat])

  return (
    <div className="anvil-ref-content">
      <FilterBar cats={BINWALK_CATS} active={cat} onChange={setCat} count={filtered.length} label="options" />
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Option</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((o, i) => (
              <tr key={i}>
                <td className="anvil-ref-name">{o.flag}</td>
                <td className="anvil-ref-desc">{o.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SignaturesTab({ search }: SearchProps) {
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return MAGIC_SIGNATURES.filter(s => !q || s.name.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q) || s.hex.toLowerCase().includes(q))
  }, [search])

  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Magic Bytes</th><th>Format</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map((s, i) => (
              <tr key={i}>
                <td className="anvil-ref-name">{s.hex}</td>
                <td className="anvil-ref-syntax">{s.name}</td>
                <td className="anvil-ref-desc">{s.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function EntropyTab() {
  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Plage</th><th>Signification</th></tr></thead>
          <tbody>
            {ENTROPY_GUIDE.map((e, i) => (
              <tr key={i}>
                <td className="anvil-ref-name">{e.range}</td>
                <td className="anvil-ref-desc">{e.meaning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Protocols tabs
   ═══════════════════════════════════════════════════════════════ */

function ModbusFuncTab({ search }: SearchProps) {
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return MODBUS_FUNCTIONS.filter((f: ModbusFunc) =>
      !q || f.name.toLowerCase().includes(q) || f.desc.toLowerCase().includes(q) || ('0x' + f.code.toString(16)).includes(q)
    )
  }, [search])

  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Code</th><th>Nom</th><th>Acces</th><th>Description</th></tr></thead>
          <tbody>
            {filtered.map(f => (
              <tr key={f.code}>
                <td className="anvil-ref-num">0x{f.code.toString(16).padStart(2, '0').toUpperCase()}</td>
                <td className="anvil-ref-name">{f.name}</td>
                <td className="anvil-ref-syntax">{f.access}</td>
                <td className="anvil-ref-desc">{f.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ModbusRegsTab() {
  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Type</th><th>Adresse</th><th>Acces</th><th>Taille</th><th>Description</th></tr></thead>
          <tbody>
            {MODBUS_REG_TYPES.map((r: ModbusRegType) => (
              <tr key={r.type}>
                <td className="anvil-ref-name">{r.type}</td>
                <td className="anvil-ref-num">{r.address}</td>
                <td className="anvil-ref-syntax">{r.access}</td>
                <td className="anvil-ref-args">{r.size}</td>
                <td className="anvil-ref-desc">{r.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ModbusErrorsTab() {
  return (
    <div className="anvil-ref-content">
      <div className="anvil-ref-table-wrap">
        <table className="anvil-ref-table">
          <thead><tr><th>Code</th><th>Nom</th><th>Description</th></tr></thead>
          <tbody>
            {MODBUS_EXCEPTIONS.map(e => (
              <tr key={e.code}>
                <td className="anvil-ref-num">0x{e.code.toString(16).padStart(2, '0').toUpperCase()}</td>
                <td className="anvil-ref-name">{e.name}</td>
                <td className="anvil-ref-desc">{e.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ModbusFrameTab() {
  return (
    <div className="anvil-ref-content anvil-ref-abi">
      <h3 className="anvil-ref-h3"><i className="fa-solid fa-network-wired" /> {MODBUS_FRAME.tcp.name}</h3>
      <table className="anvil-ref-table">
        <thead><tr><th>Champ</th><th>Taille</th><th>Description</th></tr></thead>
        <tbody>
          {MODBUS_FRAME.tcp.fields.map(f => (
            <tr key={f.field}><td className="anvil-ref-name">{f.field}</td><td className="anvil-ref-num">{f.size}</td><td className="anvil-ref-desc">{f.desc}</td></tr>
          ))}
        </tbody>
      </table>

      <h3 className="anvil-ref-h3"><i className="fa-solid fa-plug" /> {MODBUS_FRAME.rtu.name}</h3>
      <table className="anvil-ref-table">
        <thead><tr><th>Champ</th><th>Taille</th><th>Description</th></tr></thead>
        <tbody>
          {MODBUS_FRAME.rtu.fields.map(f => (
            <tr key={f.field}><td className="anvil-ref-name">{f.field}</td><td className="anvil-ref-num">{f.size}</td><td className="anvil-ref-desc">{f.desc}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   Tab router
   ═══════════════════════════════════════════════════════════════ */

function TabContent({ tabId, search }: TabContentProps) {
  switch (tabId) {
    // ASM
    case 'syscalls': return <SyscallsTab search={search} />
    case 'instructions': return <InstructionsTab search={search} />
    case 'conventions': return <ConventionsTab />
    case 'directives': return <DirectivesTab search={search} />
    case 'patterns': return <PatternsView patterns={ASM_PATTERNS} />
    // RE
    case 'rizin': return <RizinTab search={search} />
    case 'elf-format': return <ElfFormatTab />
    case 'elf-sections': return <ElfSectionsTab search={search} />
    case 're-patterns': return <PatternsView patterns={RE_PATTERNS} />
    // Pwn
    case 'protections': return <ProtectionsTab />
    case 'techniques': return <TechniquesTab />
    case 'fmtstr': return <FmtStrTab />
    case 'pwntools': return <PwntoolsTab />
    // Debug
    case 'gdb': return <GdbTab search={search} />
    case 'pwndbg': return <PwndbgTab search={search} />
    case 'examine': return <ExamineTab />
    // Firmware
    case 'binwalk': return <BinwalkTab search={search} />
    case 'signatures': return <SignaturesTab search={search} />
    case 'entropy': return <EntropyTab />
    case 'fw-patterns': return <PatternsView patterns={FW_PATTERNS} />
    // Protocols
    case 'modbus-func': return <ModbusFuncTab search={search} />
    case 'modbus-regs': return <ModbusRegsTab />
    case 'modbus-errors': return <ModbusErrorsTab />
    case 'modbus-frame': return <ModbusFrameTab />
    case 'hw-patterns': return <PatternsView patterns={PROTOCOL_PATTERNS} />
    default: return null
  }
}

/* ═══════════════════════════════════════════════════════════════
   Main modal
   ═══════════════════════════════════════════════════════════════ */

export function ReferenceModal({ open, onClose, mode }: ReferenceModalProps) {
  const tabs = MODE_TABS[mode]
  const [tab, setTab] = useState(tabs[0].id)
  const [search, setSearch] = useState('')

  // Reset tab when mode changes — fallback to first tab if current doesn't exist
  const activeTab = tabs.find(t => t.id === tab) ? tab : tabs[0].id

  if (!open) return null

  return (
    <div className="anvil-modal-backdrop" onClick={onClose}>
      <div className="anvil-modal anvil-ref-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="anvil-modal-header">
          <i className="fa-solid fa-book" />
          <span className="anvil-modal-title">{MODE_TITLES[mode]}</span>
          <div className="anvil-ref-search-wrap">
            <i className="fa-solid fa-search" />
            <input
              className="anvil-ref-search"
              placeholder="Rechercher..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoFocus
            />
            {search && (
              <button className="anvil-ref-search-clear" onClick={() => setSearch('')}>
                <i className="fa-solid fa-xmark" />
              </button>
            )}
          </div>
          <button className="anvil-modal-close" onClick={onClose}>
            <i className="fa-solid fa-xmark" />
          </button>
        </div>

        {/* Tabs */}
        <div className="anvil-ref-tabs">
          {tabs.map(t => (
            <button
              key={t.id}
              className={`anvil-ref-tab ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => { setTab(t.id); setSearch('') }}
            >
              <i className={`fa-solid ${t.icon}`} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="anvil-ref-body">
          <TabContent tabId={activeTab} search={search} />
        </div>
      </div>
    </div>
  )
}