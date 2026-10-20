"""Runs every tests/direct/test_*.py module against the contract via the offline SDK shim.
Usage (from repo root):  python3 tests/offline/run_offline.py .
Not a substitute for gltest on StudioNet."""
import importlib.util, inspect, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
TESTS = os.path.join(REPO, "tests", "direct")
sys.path.insert(0, HERE)
sys.path.insert(1, TESTS)
os.chdir(REPO)

import genlayer  # shim
import pytest    # shim
import conftest  # repo fixtures

gl = sys.modules["genlayer.gl"]


class VM:
    sender = None
    value = 0

    def warp(self, iso):
        gl.message_raw["datetime"] = iso

    def mock_web(self, pattern, response):
        genlayer._STATE["web"].append((pattern, response))

    def mock_llm(self, pattern, text):
        genlayer._STATE["llm"].append((pattern, text))

    def clear_mocks(self):
        genlayer._STATE["web"].clear()
        genlayer._STATE["llm"].clear()


ADDR = {
    "direct_alice": "0x" + "a1" * 20,
    "direct_bob": "0x" + "b2" * 20,
    "direct_carol": "0x" + "c3" * 20,
    "direct_dave": "0x" + "d4" * 20,
    "direct_eve": "0x" + "e5" * 20,
}


class Proxy:
    def __init__(self, inst, vm):
        self._i, self._vm = inst, vm

    def __getattr__(self, name):
        attr = getattr(self._i, name)
        if not callable(attr):
            return attr

        def call(*a, **k):
            gl.message.sender_address = self._vm.sender
            gl.message.value = self._vm.value
            return attr(*a, **k)
        return call


def make_deploy(vm):
    def direct_deploy(path, args=()):
        src = open(os.path.join(REPO, path)).read()
        ns = {"__name__": "contract_under_test"}
        exec(compile(src, path, "exec"), ns)
        gl.message.sender_address = vm.sender
        gl.message.value = 0
        cls = [v for k, v in ns.items() if isinstance(v, type) and issubclass(v, genlayer.Contract) and v is not genlayer.Contract][0]
        return Proxy(cls(*args), vm)
    return direct_deploy


def run_test(fn, extra=None):
    extra = extra or {}
    vm = VM()
    vm.clear_mocks()
    gl.message_raw.clear()
    cache = {"direct_vm": vm, "direct_deploy": make_deploy(vm)}
    cache.update(ADDR)
    cache.update(extra)

    def resolve(name):
        if name in cache:
            return cache[name]
        f = pytest.FIXTURES[name]
        args = [resolve(p) for p in inspect.signature(f).parameters]
        cache[name] = f(*args)
        return cache[name]

    args = [resolve(p) for p in inspect.signature(fn).parameters]
    fn(*args)


def main():
    failed, total = [], 0
    for fname in sorted(os.listdir(TESTS)):
        if not (fname.startswith("test_") and fname.endswith(".py")):
            continue
        spec = importlib.util.spec_from_file_location(fname[:-3], os.path.join(TESTS, fname))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for n in sorted(dir(mod)):
            if not n.startswith("test_"):
                continue
            fn = getattr(mod, n)
            cases = [(n, {})]
            if hasattr(fn, "_params"):
                pname, vals = fn._params
                names = [x.strip() for x in pname.split(",")]
                cases = [(f"{n}[{i}]", dict(zip(names, v)) if len(names) > 1 else {pname: v}) for i, v in enumerate(vals)]
            for label, extra in cases:
                total += 1
                try:
                    run_test(fn, extra)
                    print(f"PASS {label}")
                except Exception as e:
                    failed.append(label)
                    print(f"FAIL {label}: {type(e).__name__}: {e}")
                    if os.environ.get("TB"):
                        traceback.print_exc()
    print(f"\n{total - len(failed)}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
