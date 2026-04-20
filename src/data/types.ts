export interface LexiconInstr {
  cat: string
  name: string
  syntax: string
  desc: string
}

export interface Syscall {
  num: number
  name: string
  args: string
  desc: string
}

export interface SubReg {
  name: string
  bits: string
  val: number
}
