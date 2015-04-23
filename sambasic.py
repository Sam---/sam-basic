#!/usr/bin/python3
import sys, re, math, random, subprocess
import traceback
import tty, termios
import os
from contextlib import contextmanager

from myblocks import blockdrawing

class LazyFile:
    def __init__(self, name):
        self.name = name
        self.opened = False

    def mode(self, inmode):
        if not self.opened:
            self.file = open(self.name, inmode)
            self.opened = inmode 
            return self.file
        elif self.opened == inmode:
            return self.file
        else:
            return None

    def close(self):
        self.opened = False
        self.file.close()

class Ref:
    def __init__(self, obj):
        self.d = obj

class VarList(dict):
    def __index__(self, key):
        if key not in self:
            global gerrno
            gerrno = "UNDEFINED"
            raise Exception()
        else:
            return super[key]

codelines = []
svars = VarList()
nvars = VarList()
bvars = VarList()
fvars = VarList()
handlers = {}
gerrno = None
gerrln = -1
gerrmeta = None

def hsyntaxerror():
    print("SYNTAX ERROR ON LINE {} [SYNTAXERROR]".format(gerrln))
    sys.exit(1)

def heof():
    print("UNHANDLED END OF FILE ON LINE {} FROM FILE {} [EOF]".format(
        gerrln, stdin.name))
    sys.exit(1)

def hnomatch():
    print("COULD NOT EXPLODE STRING ON LINE {} [NOMATCH]".format(gerrln))
    sys.exit(1)

def hlisterror():
    print("INVAILD LIST STATEMENT INTERVAL ON LINE {} [LISTERROR]".format(
        gerrln))
    sys.exit(1)

def hundefined():
    print("REFERENCE TO UNDEFINED VARIABLE ON LINE {} [UNDEFINED]".format(
        gerrln))
    sys.exit(1)

def hctrlc():
    sys.exit(0)

def hfail():
    print("COMMAND ON LINE {} EXITED WITH NON-ZERO STATUS CODE [FAIL]".format(
        gerrln))
    sys.exit(1)

builtin_handlers = {
    "SYNTAXERROR": hsyntaxerror,
    "EOF": heof,
    "NOMATCH": hnomatch,
    "LISTERROR": hlisterror,
    "UNDEFINED": hundefined,
    "CTRLC": hctrlc,
    "FAIL": hfail
}

stdin = sys.stdin
stdout = sys.stdout

letexprs = {
    "SQRT": math.sqrt,
    "COS": math.cos,
    "SIN": math.sin,
    "TAN": math.tan,
    "POW": lambda b, p: b ** p,
    "RAND": random.randrange
}

def run(stream):
    for line in stream:
        m = re.match(r"(\d+)\s+(.+)$", line)
        if m:
            n = int(m.group(1))
            while len(codelines) <= n:
                codelines.append(None)

            codelines[int(m.group(1))] = m.group(2)
        else:
            if not execute(line, Ref(-1)):
                global gerrno, gerrln
                if gerrno in handlers:
                    execute(handlers[gerrno], Ref(-1))
                elif gerrno in builtin_handlers:
                    builtin_handlers[gerrno]()
                else:
                    print("UNHANDLED {} ON LINE {}".format(gerrno, gerrln))
                    sys.exit(0)
                gerrno = None

def execute(line, cl):
    global gerrno, gerrln
    if not line:
        return True
    m = re.match(r"(\w+)\s*(.*)$", line)
    if m:
        stat = m.group(1)
        args = m.group(2)
        if stat in statements:
            try:
                return statements[stat](args, cl)
            except EOFError:
                gerrno = "EOF"
                gerrln = cl.d
                return False
            except Exception:
                if gerrno:
                    gerrln = cl.d
                    return False
                else:
                    raise
            except KeyboardInterrupt:
                gerrno = "CTRLC"
                gerrln = cl.d
                return False
        else:
            return syntaxerror(cl)
    else:
        return syntaxerror(cl)

def unescape(string):
    return re.sub(r"\\(.)", lambda c: {
        "N": "\n",
        " ": " ",
        '"': '"',
        "R": "\r",
        "T": "\t",
        "$": "$",
        "#": "#",
        "!": "!"
        }[c.group(1)], sunescape(nunescape(string)))

def sunescape(string):
    return re.sub(r"\$(.)", lambda c: svars[c.group(1)], string)

def nunescape(string):
    def repl(m):
        name = m.group(1)
        if name.startswith('('):
            name = name[1:-1]

        return str(nvars[name])

    return re.sub(r"#(\w+|\(\w+\))", repl, string)

def safexpr(expr):
    return eval(expr, {"__builtins__": None}, letexprs)

def litvar(v):
    if v[0] == '(':
        return v[1:-1]
    else:
        return v

def syntaxerror(cl):
    global gerrno
    global gerrln
    gerrno = "SYNTAXERROR"
    gerrln = cl.d
    return False


def strun(a, cl):
    cl = Ref(0)
    while cl.d < len(codelines):
        if not execute(codelines[cl.d], cl):
            return False
        cl.d += 1

    return True

def stlist(a, cl):
    m = re.match(r"(\d+)\s*(:\s*(\d+))\s*$", a)
    if m:
        line = int(m.group(1))
        if m.group(2):
            end = int(m.group(3))
            if end < line:
                global gerrno, gerrln
                gerrno = "LISTERROR"
                gerrln = cl.d
                return False
            while line < end:
                if codelines[line]:
                    print(line, codelines[line])
            return True
        else:
            for n, codeline in enumerate(codelines[line:]):
                if codeline:
                    print(n, codeline, file=stdout)
            return True
    else:
        for n, codeline in enumerate(codelines):
            if codeline:
                print(n, codeline, file=stdout)
        return True

def stprint(a, cl):
    print(unescape(a), file=stdout)
    return True

def stwrite(a, cl):
    print(unescape(a), file=stdout, end="", flush=True)
    return True

def stspr(a, cl):
    m = re.match(r"\$(\w+|\(\w+\))\s*(.*)$", a)
    if m:
        val = m.group(2)
        if val.startswith('('):
            val = val[1:-1]
        svars[m.group(1)] = unescape(m.group(2))
        return True
    else:
        return syntaxerror(cl)

def stlet(a, cl):
    m = re.match(r"#(\w+)\s+BE\s*(.*?)\s*$", a)
    if m:
        v = m.group(1)
        nvars[v] = safexpr(nunescape(m.group(2)))
    else:
        m = re.match(r"\?(\w+)\s+BE\s+(NOT)?\s*(TRUE|FALSE|\?\w+)\s*$", a)
        if m:
            v = m.group(1)
            inv = bool(m.group(2))
            val = m.group(3)
            if val[0] == '?':
                bvars[v] = bvars[val[1:]]
            elif val[0] == 'T':
                bvars[v] = True
            else:
                bvars[v] = False

            if inv:
                bvars[v] = not bvars[v]
        else:
            return syntaxerror(cl)
    return True

def stread(a, cl):
    m = re.match(r"(.*)\$(.)$", a)
    if m:
        print(m.group(1), end="", file=stdout, flush=True)
        svars[m.group(2)] = stdin.readline()[:-1]
        return True
    else:
        m = re.match(r"(.*)#(\w+)$", a)
        if m:
            print(m.group(1), end="", file=stdout, flush=True)
            nvars[m.group(2)] = float(stdin.readline()[:-1])
            return True
        else:
            return syntaxerror(cl)

def stgoto(a, cl):
    cl.d = int(a) - 1
    return True

def stif(a, cl):
    m = re.match(r"(NOT)?\s*\((.*?)\s*(==|>=|<=|[=<>])\s*(.*?)\)\s*(.*)$", a)
    if m:
        a1 = unescape(m.group(2))
        oper = m.group(3)
        a2 = unescape(m.group(4))
        stat = m.group(5)
        if {
                "=": lambda: safexpr(a1) == safexpr(a2),
                ">": lambda: safexpr(a1) > safexpr(a2),
                "<": lambda: safexpr(a1) < safexpr(a2),
                ">=": lambda: safexpr(a1) >= safexpr(a2),
                "<=": lambda: safexpr(a1) <= safexpr(a2),
                "==": lambda: a1 == a2
                }[oper]() ^ bool(m.group(1)):
            return execute(stat, cl)
        else:
            return True
    else:
        m = re.match(r"(NOT)?\s*\?(\w+)\s*(.*)$", a)
        if m:
            inv = False
            if m.group(1):
                inv = True
            if bool(bvars[m.group(2)]) ^ inv:
                return execute(m.group(3), cl)
            else:
                return True
        else:
            return syntaxerror(cl)

def stwhile(a, cl):
    m = re.match(r"(NOT)?\s*\((.*?)\s*(==|>=|<=|[=<>])\s*(.*?)\)\s*(.*)$", a)
    if m:
        a1 = unescape(m.group(2))
        oper = m.group(3)
        a2 = unescape(m.group(4))
        stat = m.group(5)
        inv = True if m.group(1) else False
        while {
                "=": lambda: safexpr(a1) == safexpr(a2),
                ">": lambda: safexpr(a1) > safexpr(a2),
                "<": lambda: safexpr(a1) < safexpr(a2),
                ">=": lambda: safexpr(a1) >= safexpr(a2),
                "<=": lambda: safexpr(a1) <= safexpr(a2),
                "==": lambda: a1 == a2
                }[oper]() ^ inv:
            if not execute(stat, cl):
                return False
        else:
            return True
    else:
        m = re.match(r"(NOT)?\s*\?(\w+)\s*(.*)$", a)
        if m:
            inv = False
            if m.group(1):
                inv = True
            while bool(bvars[m.group(2)]) ^ inv:
                if not execute(m.group(3), cl):
                    return False
            else:
                return True
        else:
            return syntaxerror(cl)


def strem(a, cl):
    return True

def stexit(a, cl):
    try:
        sys.exit(int(unescape(a).strip()))
        return True
    except ValueError:
        if not re.match(r"\s*\d+\.?\d*\s*", a):
            return syntaxerror(cl)
        else:
            raise

def stopen(a, cl):
    m = re.match(r"\s*(\w+)\s+AS\s+(.+)$", a)
    if m:
        fvars[m.group(1)] = LazyFile(unescape(m.group(2)))
        return True
    else:
        m = re.match(r"\s*(.+)$", a)
        if m:
            name = unescape(m.group(1))
            fvars[name] = LazyFile(name)
            return True
        else:
            return syntaxerror(cl)

def stclose(a, cl):
    m = re.match(r"\s*(.+)$", a)
    if m:
        name = unescape(m.group(1))
        fvars[name].close()
        del fvars[name]
        return True
    else:
        return syntaxerror(cl)

def stsource(a, cl):
    m = re.match(r"\s*(.+)$", a)
    if m:
        name = m.group(1)
        if name == "STDIN":
            global stdin
            stdin = sys.stdin
        else:
            name = unescape(name)
            stdin = fvars[name].mode('r')
        return True
    else:
        return syntaxerror(cl)

def stoutput(a, cl):
    m = re.match(r"\s*(.+)$", a)
    if m:
        name = m.group(1)
        if name == "STDOUT":
            global stdout
            stdout = sys.stdout
        else:
            name = unescape(name)
            stdout = fvars[name].mode('w')
        return True
    else:
        return syntaxerror(cl)



def stappend(a, cl):
    m = re.match(r"\s*(.+)$", a)
    if m:
        name = m.group(1)
        if name == "STDOUT":
            global stdout
            stdout = sys.stdout
            return True
        else:
            name = unescape(name)
            stdout = fvars[name].mode('a')
            return True
    else:
        return syntaxerror(cl)

def stdebug(a, cl):
    a = a.strip()
    exec(a)

def stexplode(a, cl):
    m = re.match(r"\s*\$(\w+)\s+INTO (.*)$", a)
    if m:
        var = m.group(1)

        targets = []

        def repl(m):
            c = m.group(1)
            if c[0] == '$':
                targets.append((svars, litvar(c[1:])))
                return '(.*?)'
            elif c[0] == '#':
                targets.append((nvars, litvar(c[1:])))
                return '(\d+\.?\d*)'
            elif c[0] == ' ':
                return '\s+'

        pattern = re.sub(r"([$#]\w+|[#$]\(\w+\)|\s+)", repl, m.group(2))

        rtm = re.match(pattern + '$', svars[var])
        if rtm:
            idx = 1
            while idx <= len(targets):
                target = targets[idx - 1]
                varl = target[0]
                name = target[1]
                varl[name] = rtm.group(idx)
                idx += 1
            return True
        else:
            global gerrno
            global gerrln
            gerrno = "NOMATCH"
            gerrln = cl.d
            return False
    else:
        return syntaxerror(cl)

def ston(a, cl):
    m = re.match("(\w+)(\(.*?\))?\s*(.*)$", a)
    if m:
        case = m.group(1)
        meta = m.group(2)
        stat = m.group(3)
        handlers[case] = stat
        return True
    else:
        return syntaxerror(cl)

def stclear(a, cl):
    print("\x1b[2J", file=stdout, end="", flush=True)
    return True

def stup(a, cl):
    n = int(safexpr(nunescape(a)))
    print('\x1b[{}A'.format(n), file=stdout, end="", flush=True)
    return True

def stdown(a, cl):
    n = int(safexpr(nunescape(a)))
    print('\x1b[{}B'.format(n), file=stdout, end="", flush=True)
    return True

def stleft(a, cl):
    n = int(safexpr(nunescape(a)))
    print('\x1b[{}C'.format(n), file=stdout, end="", flush=True)
    return True

def stright(a, cl):
    n = int(safexpr(nunescape(a)))
    print('\x1b[{}D'.format(n), file=stdout, end="", flush=True)
    return True

def sthome(a, cl):
    m = re.match(r"(.+?)\s*,\s*(.+?)\s*$", a)
    if m:
        x = int(nunescape(m.group(1)))
        y = int(nunescape(m.group(2)))
        print('\x1b[{1};{0}H'.format(x, y), file=stdout, end="", flush=True)
    else:
        print('\x1b[H', file=stdout, end="", flush=True)
    return True

def stcolor(a, cl):
    colors = "BLACK,RED,GREEN,YELLOW,BLUE,MAGENTA,CYAN,WHITE,DEFAULT".split(',')
    m = re.match(r"(BG\s)?\s*({0})\s*$".format('|'.join(colors)), a)
    if m:
        base = 40 if m.group(1) else 30
        color = colors.index(m.group(2))
        if color == 8: color = 9
        print('\x1b[{0}m'.format(base + color),
                file=stdout, end="", flush=True)
        return True
    else:
        color = safexpr(nunescape(a))
        if color.__iter__:
            for cc in color:
                print('\x1b[{0}m'.format(int(cc)),
                        file=stdout, end="", flush=True)
            return True
        else:
            print('\x1b[{0}m'.format(int(color)),
                    file=stdout, end="", flush=True)
            return True

def stfire(a, cl):
    m = re.match(r"(\w+)\s*", a)
    if m:
        global gerrno, gerrln
        gerrno = m.group(1)
        gerrln = cl.d
        return False
    else:
        return syntaxerror(cl)

def stline(a, cl):
    chdes = unescape(a).replace(" \t", "")
    if chdes in blockdrawing:
        stdout.write(blockdrawing[chdes])
        return True
    else:
        return syntaxerror(cl)

def stfor(a, cl):
    m = re.match(r"(#\w+)?\s*(.*?,)?(.+?)\s+(.*)$", a)
    if m:
        cachedval = None
        var = m.group(1) or None
        if var:
            var = var[1:]
            if var in nvars:
                cachedval = nvars[var]
        start = m.group(2) or "0,"
        start = safexpr(nunescape(start[:-1]))
        end = safexpr(nunescape(m.group(3)))

        st = m.group(4)

        for i in range(start, end):
            if var:
                nvars[var] = i
            if not execute(st, cl):
                return False
        if var and cachedval is not None:
            nvars[var] = cachedval
        return True
    else:
        return syntaxerror(cl)

def stsubp(a, cl):
    cmd = unescape(a)
    retc = subprocess.call(cmd, shell=True)
    if retc == 0:
        return True
    else:
        global gerrno, gerrln
        gerrln = cl.d
        gerrno = "FAIL"
        return False

def statoi(a, cl):
    global gerrno, gerrln
    m = re.match(r"\$(.*?)\s*#(.*?)\s*$", a)
    if m:
        svr = m.group(1)
        nvr = m.group(2)
        try:
            nvars[nvr] = float(svars[svr])
        except ValueError:
            gerrln = cl.d
            gerrno = "SYNTAXERROR"
            return False
        return True
    else:
        gerrln = cl.d
        gerrno = "SYNTAXERROR"
        return False

def stfork(a, cl):
    cmd = unescape(a)
    m = re.match(r"\s*(\d+)\s*(\d+)?\s*(\$CHILD)?\s*$", cmd)
    if m:
        pid = os.fork()
        if pid:
            if m.group(2):
                cl.d = int(m.group(2)) - 1
            if m.group(3):
                svars["CHILD"] = str(pid)
        else:
            cl.d = int(m.group(1)) - 1
        return True
    else:
        global gerrno, gerrln
        gerrno = "SYNTAXERROR"
        gerrln = cl.d
        return False

statements = {
    "PRINT": stprint,
    "WRITE": stwrite,
    "RUN": strun,
    "LIST": stlist,
    "SPR": stspr,
    "LET": stlet,
    "READ": stread,
    "GOTO": stgoto,
    "IF" : stif,
    "WHILE": stwhile,
    "REM": strem,
    "EXIT": stexit,
    "OPEN": stopen,
    "CLOSE": stclose,
    "SOURCE": stsource,
    "OUTPUT": stoutput,
    "APPEND": stappend,
    "EXPLODE": stexplode,
    "ON": ston,
    "CLEAR": stclear,
    "UP": stup,
    "DOWN": stdown,
    "LEFT": stleft,
    "RIGHT": stright,
    "HOME": sthome,
    "COLOR": stcolor,
    "FIRE": stfire,
    "LINE": stline,
    "FOR": stfor,
    "SUBP": stsubp,
    "ATOI": statoi,
    "FORK": stfork
}

if __name__=='__main__':
    try:
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as source:
                run(source)
                strun("", Ref(-1))
        else:
            run(sys.stdin)
    except Exception:
        fname = "ERROR{}.TXT".format(random.randrange(0xffff, 0xffffffff))
        with open(fname, 'w') as log:
            traceback.print_exc(file=log)
            print("DATA DUMP:", file=log)
            for svarn in svars:
                print("${}:{}".format(svarn,svars[svarn]), file=log)
            for nvarn in nvars:
                print("#{}:{}".format(nvarn, nvars[nvarn]), file=log)
            for bvarn in bvars:
                print("?{}:{}".format(
                    bvarn, "TRUE" if bvars[bvarn] else "FALSE"), file=log)
            for fvar in fvars:
                print("OPEN {}".format(fvar))
        print("FATAL INTERPRETER ERROR - DETAILS IN {}".format(fname))
        sys.exit(-1)


