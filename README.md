# Task Tracker — Claude Code 桌面任务进度悬浮窗

一个常驻桌面的任务进度悬浮窗。Claude Code 在长对话中会把任务清单写入一个 JSON 文件，这个悬浮窗实时显示清单和完成进度，让你**一眼看到最初的任务全貌，不再因为聊深了而忘记做到哪一步**。

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

- **前端**：Python + tkinter（深色主题，置顶，可缩放，1 秒轮询自动刷新）
- **数据源**：`~/.claude-tasks/tasks.json`（纯 JSON，人可读可改）
- **集成**：`CLAUDE.md` 里的指令让 Claude Code 自动维护这个文件

## 快速开始

### 1. 运行悬浮窗

需要 Python 3.7+（自带 tkinter）：

```bash
python task_tracker.py
```

Windows 上也可以直接双击 `启动悬浮窗.bat`（用 `pythonw` 无窗口后台运行）。

### 2. 让 Claude Code 自动维护任务清单

把 `CLAUDE.md` 的内容复制到你的**全局**配置 `~/.claude/CLAUDE.md`（或项目的 `CLAUDE.md`）。
之后每次开始多步骤任务，Claude 就会自动先写任务清单，并在过程中持续更新。

### 3. 示例

`sample_tasks.json` 是任务文件的格式示例，可复制为 `~/.claude-tasks/tasks.json` 试试效果。

## 任务文件格式

```json
{
  "project": "当前任务名称",
  "updated_at": "2026-08-07T12:40:00+08:00",
  "tasks": [
    {
      "id": "1",
      "title": "主任务标题",
      "done": false,
      "subtasks": [
        { "id": "1-1", "title": "子任务标题", "done": false }
      ]
    }
  ]
}
```

- `done`：布尔值。主任务没有子任务时用主任务的 `done`；有子任务时子任务各自标记。
- `updated_at`：每次写入更新为当前时间（ISO 8601）。
- 悬浮窗在文件变更后 1 秒内自动刷新。

## 自定义

窗口尺寸、颜色主题等都在 `task_tracker.py` 顶部的配置区，直接改常量即可。

- `COLOR_BG` / `COLOR_HEADER` / `COLOR_ACCENT` 等：配色
- `POLL_INTERVAL_MS`：文件监听频率（默认 1000ms）

## License

MIT
