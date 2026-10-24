def main() -> None:
    test_eval()

def skip_space(s: str, idx: int) -> int:
    '''keep moving forward the offset until you encounter a character and handles comments (;)'''
    while True:
        save = idx
        #skip spaces
        while idx < len(s) and s[idx].isspace():
            idx += 1
        #skip comment line
        if idx < len(s) and s[idx] == ';':
            idx += 1
            while idx < len(s) and s[idx] != '\n':
                idx += 1
        if idx == save:
            break
    return idx

def parse_expr(s: str, idx: int):
    idx = skip_space(s, idx)
    if s[idx] == '(':
        #list
        idx += 1
        l = []
        while True:
            idx = skip_space(s, idx)
            if idx >= len(s):
                raise Exception("invalid parrenthesis")
            elif s[idx] == ')':
                idx += 1
                break
            idx, v = parse_expr(s, idx)
            l.append(v)
        return idx, l
    
    elif s[idx] == ')':
        raise Exception("invalid parenthesis")
    else:
        #atom
        start = idx
        while idx < len(s) and (not s[idx].isspace()) and s[idx] not in '()':
            idx += 1
        if start == idx:
            raise Exception("empty program")
        return idx, parse_atom(s[start:idx])

def parse_atom(s):
    import json
    try:
        return ['val', json.loads(s)]
    except json.JSONDecodeError:
        return s

def pl_parse(s):
    idx, node = parse_expr(s, 0)
    idx = skip_space(s, idx)
    if idx < len(s):
        raise Exception("trailing garbage")
    return node

class LoopBreak(Exception):
    def __init__(self):
        super().__init__('`break`` outside a loop')

class LoopContinue(Exception):
    def __init__(self):
        super().__init__('`continue`` outside a loop')

class FuncReturn(Exception):
    def __init__(self, val):
        super().__init__('`return` outside a function')
        self.val = val


def pl_eval(env, node):
    #if it is a string then it is a variable name so process it's value
    if not isinstance(node, list):
        assert isinstance(node, str)
        return name_loopup(env, node)[node]

    #empty shit
    if len(node) == 0:
        raise Exception("invalid expression")
    #if it is number, string, bool return its value
    if len(node) == 2 and node[0] == 'val':
        return node[1]
    #binary operation
    import operator
    binops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            'eq': operator.eq,
            'ne': operator.ne,
            'ge': operator.ge,
            'gt': operator.gt,
            'le': operator.le,
            'lt': operator.lt,
            'and': operator.and_,
            'or': operator.or_,
            }
    if len(node) == 3 and node[0] in binops:
        op = binops[node[0]]
        return op(pl_eval(env, node[1]), pl_eval(env, node[2]))
    #unary operation
    unops = {
            'not':operator.not_,
            '-': operator.neg,
            }
    if len(node) == 2 and node[0] in unops:
        op = unops[node[0]]
        return op(pl_eval(env, node[1]))
    #conditonals 
    if len(node) in (3, 4) and node[0] in ('?', 'if'):
        _, cond, yes, *no = node
        no = no[0] if no else ['val', None]
        new_env = (dict(), env)

        if pl_eval(new_env, cond):
            return pl_eval(new_env, yes)
        else:
            return pl_eval(new_env, no)
    #print
    if node[0] == 'print':
        return print(*(pl_eval(env, val) for val in node[1:]))

    
    if node[0] in ('do', 'then', 'else') and len(node)>1:
        new_env = (dict(), env)
        for val in node[1:]:
            val = pl_eval(new_env, val)
        return val
    if node[0] == 'var' and len(node) == 3:
        _, name, val = node
        scope, _ = env
        if name in scope:
            raise ValueError("duplicate name")
        val = pl_eval(env, val)
        scope[name] = val
        return val

    if node[0] == 'set' and len(node) == 3:
        _, name, val = node
        scope = name_loopup(env, name)
        val = pl_eval(env, val)
        scope[name] = val
        return val

    if node[0] == 'loop' and len(node) == 3:
        _, cond, body = node
        ret = None
        while True:
            new_env = (dict(), env)
            if not pl_eval(new_env, cond):
                break
            try:
                ret = pl_eval(new_env, body)
            except LoopBreak:
                break
            except LoopContinue:
                continue
        return ret

    if node[0] == 'break' and len(node) == 1:
        raise LoopBreak
    if node[0] == 'continue' and len(node) == 1:
        raise LoopContinue
    if node[0] == 'return' and len(node) == 1:
        raise FuncReturn(None)
    if node[0] == 'return' and len(node) == 2:
        _, val = node
        raise FuncReturn(pl_eval(env, val))   

    if node[0] == 'def' and len(node) == 4:
        _, name, args, body = node
        for arg in args:
            if not isinstance(arg, str):
                raise ValueError('argument name incorrect')
        if len(args) != len(set(args)):
            raise ValueError('duplicate argument names')
        cur_scope, _ = env
        key = (name, len(args))
        if key in cur_scope:
            raise ValueError('duplicate function')
        cur_scope[key] = (args, body, env)
        return
    if node[0] == 'call' and len(node) >= 2:
        _, name, *args = node
        key = (name, len(args))
        fargs, fbody, fenv = name_loopup(env, key)[key]
        new_env = dict()

        for arg_name, arg_val in zip(fargs, args):
            new_env[arg_name] = pl_eval(env, arg_val)
        try:
            return pl_eval((new_env, fenv), fbody)
        except FuncReturn as ret:
            return ret.val





    raise ValueError("invalid expression")



def name_loopup(env, key):
    while env:
        current, env = env
        if key in current:
            return current
    raise ValueError("undefined name")



def pl_parse_prog(s):
    return pl_parse('(do ' + s + ')')







def test_eval():
    def f(s):
        return pl_eval(None, pl_parse_prog(s))
    assert f('''
        (def fib (n)
            (if (le n 0)
                (then 0)
                (else (+ n (call fib (- n 1))))))
        (call fib 5)
    ''') == 15

    assert f('''
        (def fib (n) (do
            (var r 0)
            (loop (gt n 0) (do
                (set r (+ r n))
                (set n (- n 1))
            ))
            (return r)
        ))
        (call fib 5)
    ''') == 15

    
if __name__ == "__main__":
    main()
