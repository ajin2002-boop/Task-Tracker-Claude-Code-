#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task Tracker — Claude Code 桌面任务进度悬浮窗
现代深色 UI + 系统托盘常驻。

读取 ~/.claude-tasks/tasks.json，实时显示任务清单与进度。
- 无边框圆角窗口，自定义标题栏可拖拽
- 最小化 / 关闭 → 隐藏到系统托盘
- 托盘双击 → 显示/隐藏窗口；右键 → 退出
"""
import ctypes
import json
import sys
import threading
import time
from pathlib import Path

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import pystray
from PIL import Image, ImageDraw, ImageTk

# ---------- 配置 ----------
TASKS_FILE = Path.home() / ".claude-tasks" / "tasks.json"
POLL_INTERVAL_MS = 1000
WINDOW_W = 380
WINDOW_H = 600
MIN_W = 300
MIN_H = 200

SCALE = 1.0  # 显示缩放系数，main() 里根据系统 DPI 计算


def _enable_dpi_awareness():
    """声明 DPI 感知，否则 Windows 会位图放大导致界面模糊"""
    global SCALE
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        SCALE = max(1.0, dpi / 96.0)
    except Exception:
        SCALE = 1.0

# ---------- 现代浅色配色 ----------
BG          = "#f5f6f8"
SURFACE     = "#ffffff"
SURFACE_HOV = "#e9ecf0"
BORDER      = "#e2e5ea"
TEXT        = "#1a1d24"
MUTED       = "#6b7280"
DIM         = "#a3aab4"
ACCENT      = "#22c55e"
ACCENT2     = "#06b6d4"
PARTIAL     = "#f59e0b"
DANGER      = "#ef4444"


def _img_box(size, state, accent=ACCENT):
    """用 PIL 画一个现代圆角复选框图片。state: empty / partial / done"""
    size = max(8, int(size * SCALE))
    r = max(3, size // 5)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = max(2, size // 10)
    if state == "done":
        d.rounded_rectangle([m, m, size - m - 1, size - m - 1],
                            radius=r, fill=accent)
        # 对勾
        cw = max(2, int(size * 0.16))
        d.line([size*0.30, size*0.52, size*0.45, size*0.66, size*0.70, size*0.36],
               fill="#ffffff", width=cw, joint="curve")
    elif state == "partial":
        d.rounded_rectangle([m, m, size - m - 1, size - m - 1],
                            radius=r, outline=PARTIAL, width=max(2, size // 9))
        # 短横线
        d.line([size*0.30, size*0.50, size*0.70, size*0.50],
               fill=PARTIAL, width=max(2, int(size * 0.14)))
    else:
        d.rounded_rectangle([m, m, size - m - 1, size - m - 1],
                            radius=r, outline=DIM, width=max(2, size // 9))
    return ImageTk.PhotoImage(img)


class TaskTracker:
    def __init__(self, root):
        self.root = root
        self._quitting = False
        self._drag = None
        self._imgs = []  # 保存 PhotoImage 引用，防止被 GC

        root.title("Task Tracker")
        root.configure(bg=BG)
        root.overrideredirect(True)          # 无边框
        root.geometry(f"{int(WINDOW_W*SCALE)}x{int(WINDOW_H*SCALE)}")
        root.minsize(int(MIN_W*SCALE), int(MIN_H*SCALE))
        root.attributes("-topmost", True)

        # 字体
        self.f_brand   = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.f_project = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.f_meta    = tkfont.Font(family="Segoe UI", size=9)
        self.f_task    = tkfont.Font(family="Segoe UI", size=11)
        self.f_sub     = tkfont.Font(family="Segoe UI", size=10)
        self.f_small   = tkfont.Font(family="Segoe UI", size=8)

        # 预生成图标图片
        self.img_box_done    = _img_box(22, "done")
        self.img_box_partial = _img_box(22, "partial")
        self.img_box_empty   = _img_box(22, "empty")
        self.img_sub_done    = _img_box(16, "done", accent=ACCENT2)
        self.img_sub_empty   = _img_box(16, "empty")
        self._imgs = [self.img_box_done, self.img_box_partial, self.img_box_empty,
                      self.img_sub_done, self.img_sub_empty]

        self._last_sig = None

        self._build_ui()
        # 圆角需要在窗口映射后设置，重试几次确保生效
        for delay in (100, 400, 1000):
            self.root.after(delay, self._apply_win_style)
        self.load_tasks()
        self.root.after(POLL_INTERVAL_MS, self._poll)

        # 窗口关闭 / Alt+F4 → 隐藏到托盘
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        self._setup_tray()

    def _refresh_tray_icon(self):
        """窗口稳定后强制重加一次托盘图标（启动时偶尔不显示）"""
        try:
            self.tray_icon.visible = False
            self.tray_icon.visible = True
        except Exception:
            pass

    # ---------- Windows 外观（圆角） ----------
    def _apply_win_style(self):
        try:
            # GA_ROOT = 2，取真正的顶层窗口句柄
            hwnd = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), 2)
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33 ; 2 = round (Win11)
            val = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

    # ---------- UI 构建 ----------
    def _build_ui(self):
        # ===== 自定义标题栏 =====
        bar = tk.Frame(self.root, bg=SURFACE, height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        bar.bind("<Button-1>", self._drag_start)
        bar.bind("<B1-Motion>", self._drag_move)

        dot = tk.Canvas(bar, width=8, height=8, bg=SURFACE, highlightthickness=0, bd=0)
        dot.pack(side="left", padx=(14, 7))
        dot.create_oval(1, 1, 7, 7, fill=ACCENT, outline="")
        tk.Label(bar, text="Task Tracker", font=self.f_brand, fg=TEXT,
                 bg=SURFACE).pack(side="left")

        # 最小化 / 关闭按钮（都隐藏到托盘）
        close_btn = self._btn(bar, "✕", self._hide_to_tray, hover_bg=DANGER)
        close_btn.pack(side="right", padx=(0, 8), pady=6)
        min_btn = self._btn(bar, "—", self._hide_to_tray)
        min_btn.pack(side="right", padx=4, pady=6)

        # ===== 项目名 + 进度 =====
        info = tk.Frame(self.root, bg=BG)
        info.pack(fill="x", padx=16, pady=(14, 4))

        row = tk.Frame(info, bg=BG)
        row.pack(fill="x")
        self.project_var = tk.StringVar(value="Claude Code 任务")
        tk.Label(row, textvariable=self.project_var, font=self.f_project,
                 fg=TEXT, bg=BG, anchor="w").pack(side="left")
        self.progress_var = tk.StringVar(value="0/0")
        tk.Label(row, textvariable=self.progress_var, font=self.f_meta,
                 fg=MUTED, bg=BG).pack(side="right")

        # ===== 进度条 =====
        self.prog_canvas = tk.Canvas(self.root, height=6, bg=BG,
                                     highlightthickness=0, bd=0)
        self.prog_canvas.pack(fill="x", padx=16, pady=(0, 6))

        # ===== 任务列表（可滚动） =====
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.tasks_frame = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=self.tasks_frame,
                                              anchor="nw")
        self.tasks_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.root.bind("<MouseWheel>", self._on_scroll)

        # ===== 底部状态栏（含右下角缩放柄） =====
        footer = tk.Frame(self.root, bg=SURFACE, height=24)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        self.updated_var = tk.StringVar(value="--")
        tk.Label(footer, textvariable=self.updated_var, font=self.f_small,
                 fg=DIM, bg=SURFACE).pack(side="left", padx=12)

        grip = tk.Label(footer, text="⤡", font=self.f_small, fg=DIM,
                        bg=SURFACE, cursor="size_nw_se")
        grip.pack(side="right", padx=(0, 8))
        grip.bind("<B1-Motion>", self._resize)

        # ===== 空态 / 错误占位 =====
        self.empty_frame = tk.Frame(self.tasks_frame, bg=BG)
        self.empty_title = tk.Label(self.empty_frame, text="暂无任务",
                                    font=self.f_task, fg=DIM, bg=BG)
        self.empty_title.pack(pady=(40, 2))
        tk.Label(self.empty_frame, text="让 Claude 更新 ~/.claude-tasks/tasks.json",
                 font=self.f_small, fg=MUTED, bg=BG).pack()

    def _btn(self, parent, text, cmd, hover_bg=SURFACE_HOV):
        """现代标题栏按钮：悬停变色"""
        b = tk.Label(parent, text=text, font=self.f_brand, fg=MUTED,
                     bg=SURFACE, width=2)
        b.bind("<Enter>", lambda e: b.configure(bg=hover_bg, fg=TEXT))
        b.bind("<Leave>", lambda e: b.configure(bg=SURFACE, fg=MUTED))
        b.bind("<Button-1>", lambda e: cmd())
        return b

    # ---------- 窗口拖拽 / 缩放 ----------
    def _drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(),
                      e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        if self._drag:
            self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _resize(self, e):
        w = max(int(MIN_W * SCALE), e.x_root - self.root.winfo_x())
        h = max(int(MIN_H * SCALE), e.y_root - self.root.winfo_y())
        self.root.geometry(f"{w}x{h}")

    def _on_scroll(self, e):
        self.canvas.yview_scroll(-e.delta // 120, "units")

    # ---------- 系统托盘 ----------
    def _setup_tray(self):
        try:
            image = self._tray_image()
            menu = pystray.Menu(
                pystray.MenuItem("显示 / 隐藏", self._tray_toggle, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._tray_quit),
            )
            self.tray_icon = pystray.Icon("task_tracker", image,
                                          "Task Tracker", menu)
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
            # 启动时图标偶尔不显示，窗口稳定后强制重加一次
            self.root.after(2000, self._refresh_tray_icon)
        except Exception:
            self.tray_icon = None
            # 托盘不可用时：关闭按钮直接退出
            self.root.protocol("WM_DELETE_WINDOW", self.root.quit)

    def _tray_image(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([3, 3, 61, 61], radius=14, fill=ACCENT)
        d.line([20, 33, 29, 42, 46, 23], fill="#ffffff", width=7, joint="curve")
        return img

    def _tray_toggle(self, icon=None, item=None):
        self.root.event_generate("<<TrayToggle>>")

    def _tray_quit(self, icon=None, item=None):
        self.root.event_generate("<<TrayQuit>>")

    def toggle_window(self):
        if self.root.state() == "withdrawn":
            self._show_window()
        else:
            self._hide_to_tray()

    def _hide_to_tray(self):
        self.root.withdraw()

    def _show_window(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()

    def _quit(self):
        if self._quitting:
            return
        self._quitting = True
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()

    # ---------- 数据加载 ----------
    def load_tasks(self):
        data = self._read_file()
        self._render(data)

    def _read_file(self):
        if not TASKS_FILE.exists():
            return None
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return "error"

    def _poll(self):
        sig = None
        if TASKS_FILE.exists():
            try:
                st = TASKS_FILE.stat()
                sig = (st.st_mtime, st.st_size)
            except OSError:
                sig = None
        if sig != self._last_sig:
            self._last_sig = sig
            self.load_tasks()
        self.root.after(POLL_INTERVAL_MS, self._poll)

    # ---------- 渲染 ----------
    def _render(self, data):
        # 清空任务区（保留 empty_frame 复用）
        for w in list(self.tasks_frame.winfo_children()):
            if w is not self.empty_frame:
                w.destroy()
        self.empty_frame.pack_forget()

        if data == "error":
            self.project_var.set("任务文件解析失败")
            self.progress_var.set("")
            self.empty_title.config(text="tasks.json 格式错误", fg=DANGER)
            self.empty_frame.pack(fill="both")
            return

        if not data or not data.get("tasks"):
            self.project_var.set("暂无任务")
            self.progress_var.set("0/0")
            self.empty_title.config(text="暂无任务", fg=DIM)
            self.empty_frame.pack(fill="both")
            return

        self.project_var.set(data.get("project") or "Claude Code 任务")

        updated = data.get("updated_at", "")
        if updated:
            try:
                t = time.strptime(updated[:19], "%Y-%m-%dT%H:%M:%S")
                self.updated_var.set("更新于 " + time.strftime("%H:%M:%S", t))
            except ValueError:
                self.updated_var.set("")

        tasks = data["tasks"]
        total = 0
        done = 0
        for t in tasks:
            subs = t.get("subtasks") or []
            if subs:
                total += len(subs)
                done += sum(1 for s in subs if s.get("done"))
            else:
                total += 1
                done += 1 if t.get("done") else 0

        self.progress_var.set(f"{done}/{total}")
        frac = (done / total) if total else 0
        self._draw_progress(frac)

        for task in tasks:
            self._render_task(task)

    def _draw_progress(self, frac):
        w = self.prog_canvas.winfo_width()
        h = 6
        if w < 10:
            w = int(WINDOW_W * SCALE) - 32
        self.prog_canvas.delete("all")
        self.prog_canvas.create_oval(0, 0, h, h, fill=BORDER, outline="")
        self.prog_canvas.create_oval(w - h, 0, w, h, fill=BORDER, outline="")
        self.prog_canvas.create_rectangle(h // 2, 0, w - h // 2, h,
                                          fill=BORDER, outline="")
        if frac > 0:
            fw = max(h, int(w * frac))
            self.prog_canvas.create_oval(0, 0, h, h, fill=ACCENT, outline="")
            self.prog_canvas.create_rectangle(h // 2, 0, fw - h // 2, h,
                                              fill=ACCENT, outline="")
            if fw > w - h:
                self.prog_canvas.create_oval(w - h, 0, w, h,
                                             fill=ACCENT, outline="")

    def _render_task(self, task):
        subs = task.get("subtasks") or []
        task_done = bool(task.get("done"))
        sub_done = sum(1 for s in subs if s.get("done"))

        # 复选框状态
        if task_done:
            box_img = self.img_box_done
        elif subs and sub_done:
            box_img = self.img_box_partial
        else:
            box_img = self.img_box_empty

        # 主任务行
        row = tk.Frame(self.tasks_frame, bg=BG)
        row.pack(fill="x", padx=14, pady=(8, 2))
        row.bind("<Enter>", lambda e, r=row: r.configure(bg=SURFACE_HOV))
        row.bind("<Leave>", lambda e, r=row: r.configure(bg=BG))

        box = tk.Label(row, image=box_img, bg=BG)
        box.pack(side="left", padx=(2, 8))
        box.bind("<Enter>", lambda e, r=row: r.configure(bg=SURFACE_HOV))
        box.bind("<Leave>", lambda e, r=row: r.configure(bg=BG))

        if task_done:
            fg = DIM
        else:
            fg = TEXT
        title = tk.Label(row, text=task.get("title", ""), font=self.f_task,
                         fg=fg, bg=BG, justify="left", anchor="w", wraplength=290)
        title.pack(side="left", fill="x", expand=True)
        title.bind("<Enter>", lambda e, r=row: r.configure(bg=SURFACE_HOV))
        title.bind("<Leave>", lambda e, r=row: r.configure(bg=BG))

        # 子任务
        for s in subs:
            self._render_subtask(s, task_done)

    def _render_subtask(self, sub, parent_done):
        row = tk.Frame(self.tasks_frame, bg=BG)
        row.pack(fill="x", padx=(36, 14), pady=1)

        s_done = bool(sub.get("done"))
        box_img = self.img_sub_done if s_done else self.img_sub_empty
        tk.Label(row, image=box_img, bg=BG).pack(side="left", padx=(2, 8))

        fg = DIM if (s_done or parent_done) else MUTED
        tk.Label(row, text=sub.get("title", ""), font=self.f_sub, fg=fg,
                 bg=BG, justify="left", anchor="w",
                 wraplength=270).pack(side="left", fill="x", expand=True)


def main():
    _enable_dpi_awareness()  # 必须在创建窗口之前调用
    root = tk.Tk()
    app = TaskTracker(root)
    root._tray_app = app
    root.bind("<<TrayToggle>>", lambda e: app.toggle_window())
    root.bind("<<TrayQuit>>", lambda e: app._quit())
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
