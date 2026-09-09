from pathlib import Path
import os
from abc import ABC, abstractmethod
from .config import settings

class Storage(ABC):
    @abstractmethod
    def save_bytes(self, key:str, data:bytes)->str: ...
    @abstractmethod
    def read_bytes(self,key:str)->bytes: ...
    @abstractmethod
    def atomic_publish(self,key:str,data:bytes)->str: ...

class LocalStorage(Storage):
    def __init__(self, root=None): self.root=Path(root or settings.storage_root); self.root.mkdir(parents=True,exist_ok=True)
    def _path(self,key):
        p=self.root/key; p.parent.mkdir(parents=True,exist_ok=True); return p
    def save_bytes(self,key,data):
        p=self._path(key); p.write_bytes(data); return str(p)
    def read_bytes(self,key): return self._path(key).read_bytes()
    def atomic_publish(self,key,data):
        final=self._path(key)
        tmp=final.with_name(final.name+'.tmp')
        with open(tmp,'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,final)
        return str(final)

storage=LocalStorage()
