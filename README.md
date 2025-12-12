# File System Recovery and Optimization Tool

A simulated **File System Recovery and Optimization Tool** built using Python.  
This project demonstrates how modern file systems work internally by simulating:

- File and directory management  
- Block-based storage  
- Free-space tracking using a bitmap  
- Inode-based metadata handling  
- Journaling for crash recovery  
- A graphical user interface (GUI) for interaction  

Designed as an educational tool to understand filesystem internals like EXT4, NTFS, and FAT.

---

## 🚀 Features

### ✔ Virtual Disk (Block Device)
The system simulates a disk divided into **4096-byte blocks**. All file data is stored inside these blocks.

### ✔ Free-Space Management (Bitmap)
A bitmap tracks which blocks are free or used, similar to real file systems.

### ✔ Inodes & Directories
Each file/directory has:
- inode number  
- metadata  
- list of data blocks  

Directories map filenames to inodes.

### ✔ File Operations
The tool supports:
- Creating directories  
- Creating files  
- Writing text to files  
- Reading files  
- Deleting files  
- Listing directory contents  

### ✔ Journaling (Crash Recovery)
Before writing, the system logs an **intent**.  
After writing, it logs a **commit**.  
This prevents corruption during simulated crashes.

### ✔ GUI Interface (Tkinter)
A fully interactive GUI lets users:
- Enter paths  
- Create files/folders  
- Write text  
- Read content  
- List items  
- Delete files  

---

## 🖥 GUI Preview

The GUI contains:
- **Path input box**  
- Buttons for each filesystem operation  
- A scrolling text area to write/read file content  
- Logging area to display system actions

---

## 📂 Project Structure

- fileSystem.py Main GUI and backend filesystem logic
  
- README.md Project documentation

  
---

## 🛠️ How to Run

### 1. Install Python  
Python 3.8+ recommended.

### 2. Run the GUI
python fileSystem.py



