"""Offline stand-in for the GenLayer SDK surface used by QuestVerifier.py.
Only for exercising contract logic locally; NOT a substitute for gltest/StudioNet."""
import re, sys, types

u256 = int
Address = str
TreeMap_marker = None

class TreeMap(dict):
    def __class_getitem__(cls, item):
        return cls

def allow_storage(cls):
    return cls

class UserError(Exception):
    pass

class _Deco:
    def __call__(self, f):
        return f
    def __getattr__(self, name):  # e.g. @gl.public.write.payable
        return lambda f: f

class _Public:
    write = _Deco()
    view = _Deco()

class Contract:
    def __new__(cls, *a, **k):
        obj = object.__new__(cls)
        for klass in cls.__mro__:
            for name, ann in klass.__dict__.get("__annotations__", {}).items():
                if ann is TreeMap and not hasattr(obj, name):
                    setattr(obj, name, TreeMap())
        return obj

def _contract_interface(cls):
    class _Iface:
        def __init__(self, addr):
            self._addr = addr
        def emit_transfer(self, value):
            _STATE["transfers"].append((self._addr, int(value)))
    return _Iface

_STATE = {"web": [], "llm": [], "transfers": []}

def _render(url, mode="text"):
    for pat, resp in _STATE["web"]:
        if re.search(pat, url, re.DOTALL):
            return resp["body"]
    raise UserError("no web mock for " + url)

def _exec_prompt(prompt, **kw):
    for pat, text in _STATE["llm"]:
        if re.search(pat, prompt, re.DOTALL):
            return text
    raise UserError("no llm mock")

gl = types.ModuleType("genlayer.gl")
gl.Contract = Contract
gl.public = _Public()
gl.vm = types.SimpleNamespace(UserError=UserError)
gl.message = types.SimpleNamespace(sender_address=None, value=0)
gl.message_raw = {}
gl.nondet = types.SimpleNamespace(
    web=types.SimpleNamespace(render=_render), exec_prompt=_exec_prompt)
gl.eq_principle = types.SimpleNamespace(strict_eq=lambda fn: fn())
gl.evm = types.SimpleNamespace(contract_interface=_contract_interface)
sys.modules["genlayer.gl"] = gl
