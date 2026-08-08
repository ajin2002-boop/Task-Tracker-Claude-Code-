#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Claude Code 桌面任务进度悬浮窗
读取 ~/.claude-tasks/tasks.json，置顶显示任务清单和进度。
文件变更时自动刷新。
"""
import json
import os
import sys
import time
from pathlib import Path

import tkinter as tk
from tkinter import font as tkfont

# ---------- 配置 ----------
TASKS_FILE = Path.home() / ".claude-tasks" / "tasks.json"
POLL_INTERVAL_MS = 1000   # 轮询检测文件变更的频率

# 颜色主题（深色）
COLOR_BG        = "#1a1a2e"
COLOR_HEADER    = "#16213e"
COLOR_BORDER    = "#0f3460"
COLOR_TEXT      = "#e0e0e0"
COLOR_TITLE     = "#ffffff"
COLOR_MUTED     = "#94a3b8"
COLOR_DIM       = "#64748b"
COLOR_DONE_BG   = "#4ade80"   # 已完成复选框
COLOR_PARTIAL   = "#fbbf24"   # 部分完成
COLOR_SUB_DONE  = "#22d3ee"   # 子任务已完成
COLOR_PROG_END  = "#22d3ee"
COLOR_HOVER     = "#222244"


class TaskTracker:
    def __init__(self, root):
        self.root = root
        root.title("Task Tracker")
        root.configure(bg=COLOR_BG)

        # 置顶 + 基础尺寸
        root.attributes("-topmost", True)
        root.geometry("380x600")
        root.minsize(280, 200)

        self._last_sig = None  # 记录上次文件签名(mtime,size)，用于检测变更

        # 字体（Segoe UI 在 Windows 上美观，回退到默认）
        self.f_title = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.f_header = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.f_task = tkfont.Font(family="Segoe UI", size=11)
        self.f_sub = tkfont.Font(family="Segoe UI", size=10)
        self.f_small = tkfont.Font(family="Segoe UI", size=9)

        self._build_ui()

        # 初始加载 + 启动轮询
        self.load_tasks()
        self.root.after(POLL_INTERVAL_MS, self._poll)

    # ---------- UI 构建 ----------
    def _build_ui(self):
        # 顶部：项目名 + 进度文字 + 刷新按钮
        header = tk.Frame(self.root, bg=COLOR_HEADER, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        # 状态指示灯
        self.light = tk.Canvas(header, width=10, height=10, bg=COLOR_HEADER,
                               highlightthickness=0)
        self.light.pack(side="left", padx=(14, 8))
        self._light_dot = self.light.create_oval(1, 1, 9, 9, fill=COLOR_DONE_BG,
                                                 outline="")

        self.project_var = tk.StringVar(value="Claude Code 任务")
        tk.Label(header, textvariable=self.project_var, font=self.f_header,
                 fg=COLOR_TITLE, bg=COLOR_HEADER).pack(side="left")

        self.progress_var = tk.StringVar(value="0/0")
        tk.Label(header, textvariable=self.progress_var, font=self.f_small,
                 fg=COLOR_MUTED, bg=COLOR_HEADER).pack(side="right", padx=(0, 8))

        self.refresh_btn = tk.Button(header, text="↻", font=self.f_header,
                                     fg=COLOR_MUTED, bg=COLOR_HEADER,
                                     activeforeground=COLOR_TITLE,
                                     activebackground=COLOR_BORDER,
                                     relief="flat", bd=0, width=2,
                                     cursor="hand2", command=self.load_tasks)
        self.refresh_btn.pack(side="right", padx=(0, 10))

        # 进度条
        prog_bar = tk.Frame(self.root, bg=COLOR_BORDER, height=3)
        prog_bar.pack(fill="x")
        prog_bar.pack_propagate(False)
        self.prog_fill = tk.Frame(prog_bar, bg=COLOR_DONE_BG, width=0)
        self.prog_fill.place(x=0, y=0, relheight=1.0)

        # 任务列表（可滚动）
        self.canvas = tk.Canvas(self.root, bg=COLOR_BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.tasks_frame = tk.Frame(self.canvas, bg=COLOR_BG)
        self._win = self.canvas.create_window((0, 0), window=self.tasks_frame,
                                              anchor="nw")
        self.tasks_frame.bind("<Configure>",
                              lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))
        # 鼠标滚轮
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.tasks_frame.bind("<MouseWheel>", self._on_scroll)

        # 底部：更新时间
        footer = tk.Frame(self.root, bg=COLOR_HEADER, height=24)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        self.updated_var = tk.StringVar(value="--")
        tk.Label(footer, textvariable=self.updated_var, font=self.f_small,
                 fg=COLOR_DIM, bg=COLOR_HEADER).pack(expand=True)

    def _on_scroll(self, event):
        self.canvas.yview_scroll(-event.delta // 120, "units")

    # ---------- 数据加载 ----------
    def load_tasks(self):
        """读取 JSON 并渲染。文件缺失/损坏时显示占位信息。"""
        data = self._read_file()
        self._render(data)

    def _read_file(self):
        if not TASKS_FILE.exists():
            return None
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _poll(self):
        """轮询检测文件变更"""
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
        # 清空
        for w in self.tasks_frame.winfo_children():
            w.destroy()

        # 顶部信息
        if not data or not data.get("tasks"):
            self.project_var.set("暂无任务")
            self.progress_var.set("0/0")
            self.updated_var.set("更新 ~/.claude-tasks/tasks.json 后自动显示")
            self.prog_fill.configure(width=0)
            self._set_light(False)
            self._render_empty()
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
        # 统计进度（含子任务）
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
        pct = int(done / total * 100) if total else 0
        self.progress_var.set("%d/%d" % (done, total))
        self.prog_fill.configure(width=int(self.canvas.winfo_width() * pct / 100))

        self._set_light(True)

        for task in tasks:
            self._render_task(task)

    def _render_empty(self):
        tk.Label(self.tasks_frame, text="还没有任务", font=self.f_task,
                 fg=COLOR_DIM, bg=COLOR_BG).pack(pady=(40, 4))
        tk.Label(self.tasks_frame, text="让 Claude 更新 ~/.claude-tasks/tasks.json",
                 font=self.f_small, fg=COLOR_MUTED, bg=COLOR_BG).pack()

    def _render_task(self, task):
        subs = task.get("subtasks") or []
        task_done = bool(task.get("done"))
        sub_done = sum(1 for s in subs if s.get("done"))

        # 主任务行
        row = tk.Frame(self.tasks_frame, bg=COLOR_BG)
        row.pack(fill="x", padx=12, pady=(8, 2))
        row.bind("<Enter>", lambda e, r=row: r.configure(bg=COLOR_HOVER))
        row.bind("<Leave>", lambda e, r=row: r.configure(bg=COLOR_BG))

        # 复选框指示
        box = tk.Label(row, text="☑" if task_done else "☐", font=self.f_header,
                       fg=COLOR_DONE_BG if task_done else
                          (COLOR_PARTIAL if sub_done else COLOR_MUTED),
                       bg=COLOR_BG, width=2)
        box.pack(side="left")
        box.bind("<Enter>", lambda e, r=row: r.configure(bg=COLOR_HOVER))
        box.bind("<Leave>", lambda e, r=row: r.configure(bg=COLOR_BG))

        # 标题
        title_fg = COLOR_DIM if task_done else COLOR_TEXT
        title_font = self.f_task
        if not task_done and (subs and sub_done):
            title_fg = COLOR_TITLE
        title = tk.Label(row, text=task.get("title", ""), font=title_font,
                         fg=title_fg, bg=COLOR_BG, justify="left",
                         anchor="w", wraplength=300)
        title.pack(side="left", fill="x", expand=True)
        title.bind("<Enter>", lambda e, r=row: r.configure(bg=COLOR_HOVER))
        title.bind("<Leave>", lambda e, r=row: r.configure(bg=COLOR_BG))

        # 子任务
        for s in subs:
            self._render_subtask(s, task_done)

    def _render_subtask(self, sub, parent_done):
        row = tk.Frame(self.tasks_frame, bg=COLOR_BG)
        row.pack(fill="x", padx=(34, 12), pady=1)

        s_done = bool(sub.get("done"))
        box = tk.Label(row, text="✓" if s_done else "·", font=self.f_sub,
                       fg=COLOR_SUB_DONE if s_done else COLOR_DIM, bg=COLOR_BG,
                       width=2)
        box.pack(side="left")

        fg = COLOR_DIM if (s_done or parent_done) else COLOR_MUTED
        tk.Label(row, text=sub.get("title", ""), font=self.f_sub, fg=fg,
                 bg=COLOR_BG, justify="left", anchor="w",
                 wraplength=280).pack(side="left", fill="x", expand=True)

    # ---------- 辅助 ----------
    def _set_light(self, on):
        self.light.itemconfig(self._light_dot,
                              fill=COLOR_DONE_BG if on else COLOR_DIM)


def main():
    root = tk.Tk()
    TaskTracker(root)
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
