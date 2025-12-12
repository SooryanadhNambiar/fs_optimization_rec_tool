import os
import json
import pickle
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox



BLOCK_SIZE = 4096
NUM_BLOCKS = 1024
JOURNAL_FILE = "journal.log"
DISK_IMAGE = "disk.img"


class Timer:
    @staticmethod
    def now():
        return time.time()


class BlockDevice:
    def __init__(self):
        self.blocks = [bytearray(BLOCK_SIZE) for _ in range(NUM_BLOCKS)]

    def read_block(self, bno):
        return bytes(self.blocks[bno])

    def write_block(self, bno, data):
        self.blocks[bno][:len(data)] = data
        if len(data) < BLOCK_SIZE:
            self.blocks[bno][len(data):] = b'\x00' * (BLOCK_SIZE - len(data))


class Bitmap:
    def __init__(self):
        self.map = [0] * NUM_BLOCKS

    def allocate(self, n=1):
        result = []
        for i in range(NUM_BLOCKS):
            if self.map[i] == 0:
                self.map[i] = 1
                result.append(i)
                if len(result) == n:
                    return result
        raise RuntimeError("Out of disk space.")

    def free(self, blocks):
        for b in blocks:
            self.map[b] = 0


class Inode:
    def __init__(self, ino, is_dir=False):
        self.ino = ino
        self.is_dir = is_dir
        self.blocks = []
        self.size = 0
        self.ctime = Timer.now()
        self.mtime = Timer.now()


class Directory:
    def __init__(self):
        self.entries = {}   # name → inode number


class Journal:
    def __init__(self):
        open(JOURNAL_FILE, "a").close()

    def append(self, record):
        with open(JOURNAL_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self):
        if not os.path.exists(JOURNAL_FILE):
            return []
        lines = open(JOURNAL_FILE).read().splitlines()
        return [json.loads(l) for l in lines if l.strip()]

    def clear(self):
        open(JOURNAL_FILE, "w").close()


class FileSystem:
    def __init__(self):
        self.disk = BlockDevice()
        self.bitmap = Bitmap()
        self.inodes = {}
        self.directories = {}
        self.journal = Journal()
        self.next_ino = 1

        # Create root directory
        root_ino = self._new_inode(is_dir=True)
        self.root = root_ino
        self.directories[root_ino] = Directory()

    def _new_inode(self, is_dir=False):
        ino = self.next_ino
        self.next_ino += 1
        self.inodes[ino] = Inode(ino, is_dir)
        if is_dir:
            self.directories[ino] = Directory()
        return ino


    def _get_inode(self, path):
        if path == "/" or path.strip() == "":
            return self.root

        parts = [p for p in path.strip("/").split("/") if p]

        cur = self.root
        for p in parts:
            if cur not in self.directories:
                return None
            if p not in self.directories[cur].entries:
                return None
            cur = self.directories[cur].entries[p]

        return cur

    def _get_parent(self, path):
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) == 0:
            return None, None

        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        parent_ino = self._get_inode(parent_path)
        return parent_ino, name

    # -------------------- Directory Actions --------------------
    def mkdir(self, path):
        parent, name = self._get_parent(path)
        if parent is None:
            raise FileNotFoundError("Parent directory does not exist.")
        if name in self.directories[parent].entries:
            raise FileExistsError("Directory already exists.")
        ino = self._new_inode(is_dir=True)
        self.directories[parent].entries[name] = ino

    def create(self, path):
        parent, name = self._get_parent(path)
        if parent is None:
            raise FileNotFoundError("Parent directory does not exist.")
        if name in self.directories[parent].entries:
            raise FileExistsError("File already exists.")
        ino = self._new_inode(is_dir=False)
        self.directories[parent].entries[name] = ino


    def write(self, path, text):
        data = text.encode()

        self.journal.append({"type": "intent", "action": "write", "path": path})

        ino = self._get_inode(path)

        if ino is None:
            parent, name = self._get_parent(path)
            if parent is None:
                raise FileNotFoundError("Parent directory does not exist.")
            ino = self._new_inode(False)
            self.directories[parent].entries[name] = ino

        inode = self.inodes[ino]

        # free old blocks
        if inode.blocks:
            self.bitmap.free(inode.blocks)

        needed = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
        blocks = self.bitmap.allocate(needed)

        inode.blocks = blocks
        inode.size = len(data)

        for i, b in enumerate(blocks):
            chunk = data[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE]
            self.disk.write_block(b, chunk)

        self.journal.append({"type": "commit", "action": "write", "path": path})


    def read(self, path):
        ino = self._get_inode(path)
        if ino is None:
            raise FileNotFoundError("File not found.")

        inode = self.inodes[ino]
        content = b""
        for b in inode.blocks:
            content += self.disk.read_block(b)

        return content[:inode.size].decode()


    def ls(self, path):
        ino = self._get_inode(path)
        if ino is None:
            raise FileNotFoundError("Directory does not exist.")
        if not self.inodes[ino].is_dir:
            raise NotADirectoryError("Not a directory.")
        return list(self.directories[ino].entries.keys())


    def delete(self, path):
        parent, name = self._get_parent(path)
        ino = self._get_inode(path)
        if ino is None:
            raise FileNotFoundError("File not found.")
        inode = self.inodes[ino]
        if inode.blocks:
            self.bitmap.free(inode.blocks)
        del self.directories[parent].entries[name]




class FSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File System GUI - Working Version")
        self.geometry("900x600")
        self.fs = FileSystem()
        self.build()

    def build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=10)

        ttk.Label(header, text="Path:").pack(side="left")
        self.path_entry = ttk.Entry(header, width=50)
        self.path_entry.pack(side="left", padx=10)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=5)

        ttk.Button(btns, text="Create Dir", command=self.gui_mkdir).pack(side="left", padx=5)
        ttk.Button(btns, text="Create File", command=self.gui_create).pack(side="left", padx=5)
        ttk.Button(btns, text="Write", command=self.gui_write).pack(side="left", padx=5)
        ttk.Button(btns, text="Read", command=self.gui_read).pack(side="left", padx=5)
        ttk.Button(btns, text="List", command=self.gui_ls).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.gui_delete).pack(side="left", padx=5)

        ttk.Label(self, text="Content / Output:").pack(anchor="w", padx=10)

        self.output = scrolledtext.ScrolledText(self, width=110, height=27)
        self.output.pack(padx=10, pady=10)


    def get_path(self):
        p = self.path_entry.get().strip()
        if not p.startswith("/"):
            p = "/" + p
        return p


    def log(self, msg):
        self.output.insert(tk.END, msg + "\n")
        self.output.see(tk.END)



    def gui_mkdir(self):
        try:
            self.fs.mkdir(self.get_path())
            self.log("Directory created.")
        except Exception as e:
            self.log("ERROR: " + str(e))

    def gui_create(self):
        try:
            self.fs.create(self.get_path())
            self.log("File created.")
        except Exception as e:
            self.log("ERROR: " + str(e))

    def gui_write(self):
        text = self.output.get("1.0", tk.END)   # DO NOT strip newlines!
        try:
            self.fs.write(self.get_path(), text)
            self.log("Write successful.")
        except Exception as e:
            self.log("ERROR: " + str(e))

    def gui_read(self):
        try:
            data = self.fs.read(self.get_path())
            self.output.delete("1.0", tk.END)
            self.output.insert("1.0", data + "\n")  # Insert at TOP
            self.log("Read successful.")
            self.output.see("1.0")  # Scroll to top to show the file content
        except Exception as e:
            self.log("ERROR: " + str(e))

    def gui_ls(self):
        try:
            items = self.fs.ls(self.get_path())
            self.log("Directory contains: " + ", ".join(items))
        except Exception as e:
            self.log("ERROR: " + str(e))

    def gui_delete(self):
        try:
            self.fs.delete(self.get_path())
            self.log("Deleted successfully.")
        except Exception as e:
            self.log("ERROR: " + str(e))


if __name__ == "__main__":
    app = FSApp()
    app.mainloop()
