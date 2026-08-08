# Task Tracker — Claude Code 桌面任务进度悬浮窗

**简体中文** | [English](README_EN.md)

一个常驻桌面的任务进度悬浮窗。Claude Code 在长对话中会把任务清单写入一个 JSON 文件，这个悬浮窗实时显示清单和完成进度，让你**一眼看到最初的任务全貌，不再因为聊深了而忘记做到哪一步**。

## 下载

[⬇ 下载 TaskTracker.exe (v0.2.0)](https://github.com/ajin2002-boop/Task-Tracker-Claude-Code-/releases/download/v0.2.0/TaskTracker.exe)

Windows 直接下载 exe 双击运行，**无需安装 Python**。

## 解决的问题

用 Claude Code 做多步骤任务时，任务列表会随对话滚动消失，一旦在某一步上聊得久，就容易丢失整体任务轨迹，还得回头问 agent"我们做到哪了"，浪费 token。

这个工具把任务清单**常驻桌面**：
- 完整任务清单 + 进度条 + 子任务一目了然
- agent 每完成一步，悬浮窗自动打勾
- 任务聊着聊着展开出子任务，agent 会自动加进清单

## 工作原理

```
你让 Claude 做多步骤任务
        ↓
Claude 按 CLAUDE.md 指令，写任务清单到 ~/.claude-tasks/tasks.json
        ↓
桌面悬浮窗 1 秒内自动刷新，显示完整清单 + 进度条
        ↓
Claude 完成一步 → 改 done → 悬浮窗自动打勾
```

- **前端**：Python + tkinter（浅色主题，置顶，可缩放，1 秒轮询自动刷新）
- **数据源**：`~/.claude-tasks/tasks.json`（纯 JSON，人可读可改）
- **集成**：软件首次运行时**自动配置**，无需手动操作

## 快速开始

### 1. 下载并运行

[⬇ 下载 TaskTracker.exe](https://github.com/ajin2002-boop/Task-Tracker-Claude-Code-/releases/download/v0.1.0/TaskTracker.exe)，双击即用，**无需安装 Python、无需任何手动配置**。

开发模式跑源码：

```bash
python task_tracker.py
```

Windows 上也可以直接双击 `启动悬浮窗.bat`（用 `pythonw` 无窗口后台运行）。

### 2. 自动完成与 Claude Code 集成

**第一次运行时，软件会自动完成这些配置（用户无感）：**
- 创建 `~/.claude-tasks/` 目录和 `tasks.json`
- 检查 `~/.claude/CLAUDE.md`，自动写入/追加"任务维护说明"

之后每次开始多步骤任务，Claude 就会自动先写任务清单，并在过程中持续更新——**你什么都不用做**。

### 3. 示例

`sample_tasks.json` 是任务文件的格式示例，可复制为 `~/.claude-tasks/tasks.json` 试试效果。

## 任务文件格式

```json
{
  "project": "当前任务名称",
  "updated_at": "2026-08-08T12:40:00+08:00",
  "tasks": [
    {
      "id": "1",
      "title": "主任务标题",
      "status": "pending",
      "subtasks": [
        { "id": "1-1", "title": "子任务标题", "done": false }
      ]
    }
  ]
}
```

- `status`（主任务）：`pending` 待办 / `in_progress` 进行中 / `completed` 完成 / `cancelled` 取消 / `paused` 暂停
- `done`（子任务）：布尔值
- 悬浮窗会用不同颜色和图标区分这 5 种状态
- `updated_at`：每次写入更新为当前时间（ISO 8601）。
- 悬浮窗在文件变更后 1 秒内自动刷新。

## 自定义

窗口尺寸、颜色主题等都在 `task_tracker.py` 顶部的配置区，直接改常量即可。

- `COLOR_BG` / `COLOR_HEADER` / `COLOR_ACCENT` 等：配色
- `POLL_INTERVAL_MS`：文件监听频率（默认 1000ms）

## License

MIT
