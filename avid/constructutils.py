#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import inspect, re, sys, os, time

from construct import *
from construct.core import evaluate
from construct.lib import HexDisplayedInteger, stringtypes, reprstring
from .utils import *
from math import ceil

def ZPadding(size):
    return Const(bytes(size), Bytes(size))

class Ver:
    pass

class ReloadableMeta(type):
    def __new__(cls, name, bases, dct):
        m = super().__new__(cls, name, bases, dct)
        m._load_time = time.time()
        return m

class Reloadable(metaclass=ReloadableMeta):
    @classmethod
    def _reloadcls(cls, force=False):
        mods = []
        for c in cls.mro():
            mod = sys.modules[c.__module__]
            cur_cls = getattr(mod, c.__name__)
            mods.append((cur_cls, mod))
            if c.__name__ == "Reloadable":
                break

        reloaded = set()
        newest = 0
        for pcls, mod in mods[::-1]:
            source = getattr(mod, "__file__", None)
            if not source:
                continue
            newest = max(newest, os.stat(source).st_mtime, pcls._load_time)
            if (force or reloaded or pcls._load_time < newest) and mod.__name__ not in reloaded:
                print(f"Reload: {mod.__name__}")
                mod = importlib.reload(mod)
                reloaded.add(mod.__name__)

        return getattr(mods[0][1], cls.__name__)

    def _reloadme(self):
        self.__class__ = self._reloadcls()

def recusive_reload(obj, token=None):
    global g_depth

    if token is None:
        g_depth = 0
        token = object()

    cur_token = getattr(obj, "_token", None)
    if cur_token is token:
        return

    g_depth += 1
    #print("  " * g_depth + f"> {obj}", id(obj), id(token))
    if isinstance(obj, Construct) and hasattr(obj, 'subcon'):
        # Single subcon types
        if inspect.isclass(obj.subcon):
            #print("> isclass")
            if hasattr(obj.subcon, "_reloadcls"):
                #print("> Recursive (subcon)")
                obj.subcon = obj.subcon._reloadcls(token=token)
        else:
            if isinstance(obj.subcon, Construct):
                recusive_reload(obj.subcon, token)
    if isinstance(obj, Construct) and hasattr(obj, 'subcons'):
        # Construct types that have lists
        new_subcons = []
        for i, item in enumerate(obj.subcons):
            if inspect.isclass(item):
                if hasattr(item, "_reloadcls"):
                    #print("> Recursive (subcons)")
                    item = item._reloadcls()
            else:
                if isinstance(item, Construct):
                    recusive_reload(item, token)
            new_subcons.append(item)
            obj.subcons = new_subcons

    if isinstance(obj, Construct) and hasattr(obj, 'cases'):
        # Construct types that have lists
        for i, item in list(obj.cases.items()):
            if inspect.isclass(item):
                if hasattr(item, "_reloadcls"):
                    #print("> Recursive (cases)")
                    obj.cases[i] = item._reloadcls(token=token)
            else:
                if isinstance(item, Construct):
                    recusive_reload(item, token)

    for field in dir(obj):
        value = getattr(obj, field)
        if inspect.isclass(value):
            if hasattr(value, "_reloadcls"):
                #print("> Recursive (value)")
                setattr(obj, field, value._reloadcls(token=token))
        else:
            if isinstance(value, Construct):
                recusive_reload(value, token)

    obj._token = token

    g_depth -= 1

def str_value(value, repr=False):
    if isinstance(value, bytes) and value == bytes(len(value)):
        return f"bytes({len(value):#x})"
    if isinstance(value, bytes) and repr:
        return f"bytes.fromhex('{value.hex()}')"
    if isinstance(value, DecDisplayedInteger):
        return str(value)
    if isinstance(value, int):
        if value in g_struct_addrmap:
            desc = g_struct_addrmap[value]
            return f"{value:#x} ({desc})"
        else:
            return f"{value:#x}"
    if isinstance(value, ListContainer):
        om = ""
        while len(value) > 1 and not value[-1]:
            value = value[:-1]
            om = " ..."
        if len(value) <= 16:
            return "[" + ", ".join(map(str_value, value)) + f"{om}]"
        else:
            sv = ["[\n"]
            for off in range(0, len(value), 16):
                sv.append("  " + ", ".join(map(str_value, value[off:off+16])) + ",\n")
            sv.append(f"{om}]\n")
            return "".join(sv)

    return str(value)

class DecDisplayedInteger(int):
    @staticmethod
    def new(intvalue):
        obj = DecDisplayedInteger(intvalue)
        return obj

class ConstructClassException(Exception):
    pass


# We need to inherrit Construct as a metaclass so things like If and Select will work
class ReloadableConstructMeta(ReloadableMeta, Construct):

    def __new__(cls, name, bases, attrs):
        cls = super().__new__(cls, name, bases, attrs)
        cls.name = name
        if cls.SHORT_NAME is not None:
            cls.short_name = cls.SHORT_NAME
        else:
            cls.short_name = re.sub('[a-z]', '', cls.name)
            if len(cls.short_name) > 5:
                cls.short_name = cls.short_name[:3] + cls.short_name[-2:]

        try:
            cls.flagbuildnone = cls.subcon.flagbuildnone
        except AttributeError:
            cls.flagbuildnone = False

        cls.docs = None

        cls._off = {}
        if "subcon" not in attrs:
            return cls

        subcon = attrs["subcon"]
        if isinstance(subcon, Struct):
            off = 0
            for subcon in subcon.subcons:
                try:
                    sizeof = subcon.sizeof()
                except:
                    sizeof = None
                if isinstance(subcon, Ver):
                    if not subcon._active():
                        cls._off[subcon.name] = -1, 0
                        continue
                    subcon = subcon.subcon
                if isinstance(subcon, Renamed):
                    name = subcon.name
                    subcon = subcon.subcon
                    cls._off[name] = off, sizeof
                if sizeof is None:
                    break
                off += sizeof
        return cls

class ConstructClassBase(Reloadable, metaclass=ReloadableConstructMeta):
    """ Offers two benifits over regular construct

        1. It's reloadable, and can recusrivly reload other refrenced ConstructClasses
        2. It's a class, so you can define methods

        Currently only supports parsing, but could be extended to support building

        Example:
            Instead of:
            MyStruct = Struct(
                "field1" / Int32ul
            )

            class MyClass(ConstructClass):
                subcon = Struct(
                    "field1" / Int32ul
                )

    """
    SHORT_NAME = None

    parsed = None

    def __init__(self):
        self._pointers = set()
        self._addr = None
        self._meta = {}

    def regmap(self):
        return ConstructRegMap(type(self), self._stream.to_accessor(), self._addr)

    @classmethod
    def sizeof(cls, **contextkw):
        context = Container(**contextkw)
        context._parsing = False
        context._building = False
        context._sizing = True
        context._params = context
        return cls._sizeof(context, "(sizeof)")

    def Apply(self, dict=None, **kwargs):
        if dict is None:
            dict = kwargs

        for key in dict:
            if not key.startswith('_'):
                setattr(self, key, dict[key])
                self._keys += [key]

    def set_addr(self, addr=None, stream=None):
        #print("set_addr", type(self), addr)
        if addr is not None:
            self._addr = addr
        self._set_meta(self, stream)

    @classmethod
    def _build(cls, obj, stream, context, path):
        cls._build_prepare(obj)

        addr = stream.tell()
        try:
            new_obj = cls.subcon._build(obj, stream, context, f"{path} -> {cls.name}")
        except ConstructClassException:
            raise
        except ConstructError:
            raise
        except Exception as e:
            raise ConstructClassException(f"at {path} -> {cls.name}") from e

        # if obj is a raw value or Container, instance a proper object for it
        if not isinstance(obj, ConstructClassBase):
            obj = cls.__new__(cls)

        # update the object with anything that build updated (such as defaults)
        obj._apply(new_obj)

        obj._addr = addr
        cls._set_meta(obj, stream)
        return obj

    @classmethod
    def _sizeof(cls, context, path):
        return cls.subcon._sizeof(context, f"{path} -> {cls.name}")

    @classmethod
    def _reloadcls(cls, force=False, token=None):
        #print(f"_reloadcls({cls})", id(cls))
        newcls = Reloadable._reloadcls.__func__(cls, force)
        if hasattr(newcls, "subcon"):
            recusive_reload(newcls.subcon, token)
        return newcls

    def _apply(self, obj):
        raise NotImplementedError()

    @classmethod
    def _set_meta(cls, self, stream=None):
        if stream is not None:
            self._pointers = set()
            self._meta = {}
            self._stream = stream

        if isinstance(cls.subcon, Struct):
            subaddr = int(self._addr)
            for subcon in cls.subcon.subcons:
                try:
                    sizeof = subcon.sizeof()
                except:
                    break
                if isinstance(subcon, Ver):
                    subcon = subcon.subcon
                if isinstance(subcon, Renamed):
                    name = subcon.name
                    #print(name, subcon)
                    subcon = subcon.subcon
                    if stream is not None and getattr(stream, "meta_fn", None):
                        meta = stream.meta_fn(subaddr, sizeof)
                        if meta is not None:
                            self._meta[name] = meta
                    if isinstance(subcon, Pointer):
                        self._pointers.add(name)
                        continue
                    try:
                        #print(name, subcon)
                        val = self[name]
                    except:
                        pass
                    else:
                        if isinstance(val, ConstructClassBase):
                            val.set_addr(subaddr)
                        if isinstance(val, list):
                            subaddr2 = subaddr
                            for i in val:
                                if isinstance(i, ConstructClassBase):
                                    i.set_addr(subaddr2)
                                    subaddr2 += i.sizeof()

                subaddr += sizeof

    @classmethod
    def _parse(cls, stream, context, path):
        #print(f"parse {cls} @ {stream.tell():#x} {path}")
        addr = stream.tell()
        obj = cls.subcon._parse(stream, context, path)
        size = stream.tell() - addr

        # Don't instance Selects
        if isinstance(cls.subcon, Select):
            return obj

        # Skip calling the __init__ constructor, so that it can be used for building
        # Use parsed instead, if you need a post-parsing constructor
        self = cls.__new__(cls)
        self._addr = addr
        self._path = path
        self._meta = {}
        cls._set_meta(self, stream)
        self._apply(obj)
        return self

    @classmethod
    def _build_prepare(cls, obj):
        pass

    def build_stream(self, obj=None, stream=None, **contextkw):
        assert stream != None
        if obj is None:
            obj = self

        return Construct.build_stream(self, obj, stream, **contextkw)

    def build(self, obj=None, **contextkw):
        if obj is None:
            obj = self
        for subcon in self.__class__.subcon.subcons:
            print(subcon)
        return Construct.build(self, obj, **contextkw)

class ConstructClass(ConstructClassBase, Container):
    def diff(self, other, show_all=False):
        return self.__str__(other=other, show_all=show_all)

    def __eq__(self, other):
        return all(self[k] == other[k] for k in self
                   if (not k.startswith("_"))
                   and (k not in self._pointers)
                   and not callable(self[k]))

    def __str__(self, ignore=[], other=None, show_all=False) -> str:
        str = "  \033[1;37m" + self.__class__.__name__ + ":\033[0m\n"

        keys = list(self)
        keys.sort(key = lambda x: self._off.get(x, (-1, 0))[0])
        for key in keys:
            if key in self._off:
                offv, sizeof = self._off[key]
                if offv == -1:
                    print(key, offv, sizeof)
                    continue
            if key in ignore or key.startswith('_'):
                continue
            if "pad" in key: continue

            str += f"\t\033[0;36m{key.ljust(32)}\033[0m = "

            v = getattr(self, key)
            if isinstance(v, stringtypes):
                val_repr = reprstring(v)
            elif isinstance(v, int):
                val_repr = hex(v)
            elif isinstance(v, ListContainer) or isinstance(v, list):
                tmp = []
                stride = 4
                for n in range(ceil(len(v) / stride)):
                    y = v[n*stride:(n+1)*stride]
                    if (not sum(y)):
                        t = "-"
                        continue
                    else:
                    	if ("lsb" in key):
                    		t = ", ".join(["0x%05x" % x for x in y])
                    	else:
                    		t = ", ".join([hex(x) for x in y])
                    if (n != 0):
                    	t = "\t".ljust(len("\t") + 32 + 3) + t
                    tmp.append(t)
                val_repr = "\n".join(tmp)
            else:
                continue
            str += val_repr + "\n"
        return str + "\n"

    def _dump(self):
        print(f"# {self.__class__.__name__}")
        if self._addr is not None:
            print(f"#  Address: 0x{self._addr:x}")

        keys = list(self)
        keys.sort(key = lambda x: self._off.get(x, (-1, 0))[0])
        for key in keys:
            if key.startswith('_'):
                continue
            value = getattr(self, key)
            val_repr = str_value(value, repr=True)
            print(f"self.{key} = {val_repr}")

    @classmethod
    def _build_prepare(cls, obj):
        if isinstance(cls.subcon, Struct):
            for subcon in cls.subcon.subcons:
                if isinstance(subcon, Ver):
                    subcon = subcon.subcon
                if not isinstance(subcon, Renamed):
                    continue
                name = subcon.name
                subcon = subcon.subcon
                if isinstance(subcon, Lazy):
                    subcon = subcon.subcon
                if not isinstance(subcon, Pointer):
                    continue
                addr_field = subcon.offset.__getfield__()
                # Ugh.
                parent = subcon.offset._Path__parent(obj)
                if not hasattr(obj, name) and hasattr(parent, addr_field):
                    # No need for building
                    setattr(obj, name, None)
                elif hasattr(obj, name):
                    subobj = getattr(obj, name)
                    try:
                        addr = subobj._addr
                    except (AttributeError, KeyError):
                        addr = None
                    if addr is not None:
                        setattr(parent, addr_field, addr)
    
    @classmethod
    def _parse(cls, stream, context, path):
        self = ConstructClassBase._parse.__func__(cls, stream, context, path)

        for key in self:
            if key.startswith('_'):
                continue
            try:
                val = int(self[key])
            except:
                continue
        return self

    def _apply_classful(self, obj):
        obj2 = dict(obj)
        if isinstance(self.__class__.subcon, Struct):
            for subcon in self.__class__.subcon.subcons:
                name = subcon.name
                if name is None:
                    continue
                subcon = subcon.subcon
                if isinstance(subcon, Lazy):
                    continue
                if isinstance(subcon, Pointer):
                    subcon = subcon.subcon
                if isinstance(subcon, Ver):
                    subcon = subcon.subcon
                if isinstance(subcon, Array):
                    subcon = subcon.subcon

                if name not in obj2:
                    continue

                val = obj2[name]
                if not isinstance(subcon, type) or not issubclass(subcon, ConstructClassBase):
                    continue

                def _map(v):
                    if not isinstance(v, subcon):
                        sc = subcon()
                        sc._apply(v)
                        return sc
                    return v

                if isinstance(val, list):
                    obj2[name] = list(map(_map, val))
                else:
                    obj2[name] = _map(val)

        self._apply(obj2)

    def _apply(self, obj):
        self.update(obj)

    def items(self):
        for k in list(self):
            if k.startswith("_"):
                continue
            v = self[k]
            if getattr(v, "HAS_VALUE", None):
                yield k, v.value
            else:
                yield k, v

    def addrof(self, name):
        return self._addr + self._off[name][0]

    @classmethod
    def offsetof(cls, name):
        return cls._off[name][0]

    def clone(self):
        obj = type(self)()
        obj.update(self)
        return obj

    @classmethod
    def is_versioned(cls):
        for subcon in cls.subcon.subcons:
            if isinstance(subcon, Ver):
                return True
            while True:
                try:
                    subcon = subcon.subcon
                    if isinstance(subcon, type) and issubclass(subcon, ConstructClass) and subcon.is_versioned():
                        return True
                except:
                    break
        return False

class ConstructValueClass(ConstructClassBase):
    """ Same as Construct, but for subcons that are single values, rather than containers

        the value is stored as .value
    """
    HAS_VALUE = True

    def __eq__(self, other):
        return self.value == other.value

    def __str__(self) -> str:
        str = f"{self.__class__.__name__} @ 0x{self._addr:x}:"
        str += f"\t{str_value(self.value)}"
        return str

    def __getitem__(self, i):
        if i == "value":
            return self.value
        raise Exception(f"Invalid index {i}")

    @classmethod
    def _build(cls, obj, stream, context, path):
        return super()._build(obj.value, stream, context, path)

    def _apply(self, obj):
        self.value = obj
    _apply_classful = _apply

__all__ = ["ConstructClass", "ConstructValueClass", "ZPadding"]
