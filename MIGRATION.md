# 迁移到另一台电脑

这份文档说明：**哪些东西交给 git，哪些必须一次性整目录拷贝，以及在新机器上怎么把它跑起来。**

> 这段话是给人看的。**如果你是新那台电脑上的 AI 代理**，请改读
> `E:\deepseek-work\_migration\AI-RUNBOOK.md`（或 U 盘 `_transfer\AI-RUNBOOK.md`），
> 那份是按「可自动执行」写的：有侦察、分支判断、逐步校验和失败处理表。

---

## 一、结论先说

| 内容 | 体积 | 怎么搬 | 为什么 |
| --- | --- | --- | --- |
| 源码 / 配置 / 插件 / 人设文本 | ~25 MB | **git** | 小、经常改、值得有历史 |
| `runtime\`（uv + Python 3.12 + AstrBot 4.29.1） | 1008 MB | 一次性**整目录拷贝** | venv 里写死了绝对路径，复制到别的路径就废了 |
| `snowluma\`（自带 node.exe 的发行版 2.1.1） | 204 MB | 一次性整目录拷贝 | 二进制发行包，git 存了也没意义 |
| `downloads\SnowLuma-v2.1.1-win-x64.zip` | 41 MB | 整目录拷贝或重新下载 | 同上 |
| `astrbot\data\cmd_config.json`（**含 API Key**） | 9 KB | 整目录拷贝，**不入库** | 密钥不该进任何仓库 |
| `astrbot\data\data_v4.db` + WAL（聊天记录） | ~5 MB | 整目录拷贝，**不入库** | 二进制、每条消息都变，git 里会疯狂膨胀 |
| QQ 登录状态 | — | **无法迁移** | 新机要用小号重新登录一次 |

一句话：**git 管「会改的文本」，整目录拷贝管「又大又不能重建的二进制」。** 两者都需要，不能只靠一个。

---

## 二、硬约束：新机器的路径必须一模一样

必须是：

```
D:\deepseek-work\qqbot
```

原因：

1. `runtime\bin\astrbot.exe` 和 `runtime\tools\astrbot\` 里的环境把安装时的绝对路径写死了，
   换个盘符或目录名，`astrbot run` 会直接找不到解释器和依赖。
2. `start-snowluma.bat` 用 `%ROOT%` 相对路径，本身没问题，但它依赖的 `snowluma\node.exe` 是完整发行包，同样按原目录布局运行。

另外：**不要把它放到 E 盘或任何 DSH 工作区目录下。** 那些目录带 Windows「低完整性（Low）」标签，
继承标签后 SnowLuma 会报「Node 完整性过低，无法连接 QQ」。D 盘普通目录是 Medium，才正常。

---

## 三、迁移步骤

### 1) 新机器先装 Git

任选一种：

```powershell
# 方式 A：winget（需要能弹 UAC，装到 Program Files）
winget install --id Git.Git -e --source winget

# 方式 B：免管理员 —— PortableGit（本机就是这么装的）
# 下载 https://registry.npmmirror.com/-/binary/git-for-windows/v2.55.0.windows.5/PortableGit-2.55.0.5-64-bit.7z.exe
# 自解压到 C:\Users\<你>\Tools\PortableGit，再把 ...\PortableGit\cmd 加进 PATH
```

### 2) 整目录拷贝

U 盘 / 移动硬盘直接拷最省事（带上 `.git`，历史一起过去）：

```powershell
robocopy "D:\deepseek-work\qqbot" "F:\qqbot" /E /COPY:DAT /R:1 /W:1
```

拷到新机后放回 `D:\deepseek-work\qqbot`。若走网盘，先压成一个包（Windows 自带 bsdtar）：

```powershell
tar -a -c -f qqbot.zip -C "D:\deepseek-work" qqbot
```

> 拷贝前先把 AstrBot / SnowLuma **停掉**（`stop-all.bat`），否则 `data_v4.db-wal` 可能拷到一半状态。

### 3) 校验环境

```powershell
cd D:\deepseek-work\qqbot
powershell -ExecutionPolicy Bypass -File scripts\verify-env.ps1
```

全绿再往下走。

### 4) 让 git 认出这个仓库

整目录拷贝会把 `.git` 一起带过去，那新机上直接：

```powershell
cd D:\deepseek-work\qqbot
git status          # 应该干净
git remote -v       # 若为空，按第 5 步加远程
```

如果只拷了源码没带 `.git`，就在新机重新起一个：

```powershell
cd D:\deepseek-work\qqbot
git init -b main
git add .
git commit -m "从旧机迁移"
```

### 5) 配远程仓库（可选，用于以后两台机同步）

```powershell
git remote add origin <你的私有仓库地址>
git push -u origin main
```

### 6) 恢复密钥

`astrbot\data\cmd_config.json` 不入库。如果它是跟着整目录拷贝过来的，不用管；
如果丢了，用脱敏模板重建：

```powershell
copy astrbot\data\cmd_config.example.json astrbot\data\cmd_config.json
runtime\python\cpython-3.12.15-windows-x86_64-none\python.exe tools\apply_key_and_test.py sk-你的新key
```

### 7) 启动

```powershell
.\start-all.bat
```

- AstrBot 控制台 <http://127.0.0.1:6185>
- SnowLuma 控制台 <http://127.0.0.1:5099>（初始密码在 `snowluma\logs\console.log` 的 `initial credentials` 行）

**最后一步必须在 SnowLuma 面板里重新挂载一次 QQ**：SnowLuma 是挂在「本机已登录的 QQ 进程」上的，
登录状态不随文件迁移。先在新机上把小号 QQ 登好，再在面板里选中该进程加载。
挂上后 `config\onebot.json` 里预置的 `astrbot` 连接会自动连 `ws://127.0.0.1:6199/ws`，
AstrBot 日志出现 `aiocqhttp(OneBot v11) 适配器已连接` 即打通。

---

## 四、两台机器之后怎么同步

```powershell
# 改完东西，在改的那台
git add .
git commit -m "说明改了什么"
git push

# 另一台开工前
git pull
```

几条规矩：

- **不要两台机同时跑同一个 QQ 号**，会互相踢下线、OneBot 连接打架。
- `runtime\` / `snowluma\` 已被 `.gitignore` 排除，两台机各自保留自己那份，**永远不要试图用 git 同步它们**。
- 真实配置和数据库也不入库。要在两台机之间搬聊天记录/好感度，用 `scripts\export-state.ps1` 打个快照包手工搬。

---

## 五、常见问题

**`astrbot run` 报找不到模块 / 解释器**
路径变了。挪回 `D:\deepseek-work\qqbot`。

**SnowLuma 报「Node 完整性过低，当前进程可能无法连接 QQ」**
目录跑到了低完整性位置（E 盘、DSH 工作区、某些下载目录）。挪回 D 盘普通目录。

**AstrBot 起来了但 QQ 不回消息**
按顺序查：小号 QQ 是否已登录 → SnowLuma 是否加载到该进程 → 5099 面板里 onebot 连接是否「已连接」 → 6185 日志里适配器是否连上。

**控制台密码忘了**
`cmd_config.json` 里 `dashboard.pbkdf2_password` 是哈希。要么从旧机拷真实配置，要么删掉 `dashboard` 段让它重新初始化。
