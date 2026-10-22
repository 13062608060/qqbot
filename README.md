# QQ 小号 AI 机器人（AstrBot + SnowLuma）

部署路径：`D:\deepseek-work\qqbot`

> **为什么在 D 盘而不是 E 盘**：E:\deepseek-work 是 DSH 的工作区，里面的文件带 Windows「低完整性（Low）」标签，
> 从这些文件启动的进程也会变成 Low。SnowLuma 运行在低完整性下没有权限读写 QQ 进程，面板会报
> 「Node 完整性过低，当前进程可能无法连接 QQ」。D 盘普通目录是 Medium，所以整个部署放在这里。
> 不要把这个目录再复制回 E:\deepseek-work 下运行。

```
qqbot\
├─ start-all.bat        一键启动（先 AstrBot，再 SnowLuma）
├─ start-astrbot.bat    只启动 AstrBot
├─ start-snowluma.bat   只启动 SnowLuma
├─ stop-all.bat         停止两个服务
├─ runtime\             uv + Python 3.12 + AstrBot 工具环境（不要手动改）
├─ astrbot\             AstrBot 工作目录（data\cmd_config.json 是主配置）
├─ snowluma\            SnowLuma 运行时（自带 node.exe，无需装 Node）
├─ tools\               apply_key_and_test.py / set_api_key.py / bench_model.py / test_onebot_ws.py / patch_astrbot_config.py
└─ downloads\           SnowLuma 发行包 zip
```

## 端口

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| AstrBot WebUI | http://127.0.0.1:6185 | 机器人、模型、插件、日志都在这里配 |
| AstrBot OneBot 反向 WS | ws://127.0.0.1:6199/ws | 只监听本机，已与 SnowLuma 预配好 |
| SnowLuma WebUI | http://127.0.0.1:5099 | QQ 登录/账号与 OneBot 连接管理 |

## 初始账号

- AstrBot：用户 `astrbot`，密码 `xZgL3zjm4K2rzwTBhmDXagEF`（首次登录后请改）
- SnowLuma：用户 `admin`，密码 `3c8319c1daadde3b`
  - 这个密码**每次重启都会重新生成**（写进 `snowluma\logs\console.log` 的 `initial credentials` 行），
    首次登录务必在面板里改掉，之后就一直用你自己的密码。
- 登录后建议确认面板不再弹「Node 完整性过低」；正常启动日志应为
  `Node integrity: pid=..., process=Medium (RID=8192)`。

## 把 QQ 小号接进来

1. 先在这台机器上把 QQ 切换到你的小号并保持登录（SnowLuma 是挂在已登录的 QQ 进程上的）。
2. 启动 `start-all.bat`。
3. 打开 http://127.0.0.1:5099 → 用 admin 登录 → 勾选同意 EULA/隐私协议 → 改密码。
4. 面板里“接入 QQ 进程/账号” → 选中当前登录的小号 QQ 进程加载。
5. OneBot 连接已预置：`config\onebot.json` 里名为 `astrbot` 的 WS 客户端指向 `ws://127.0.0.1:6199/ws`，账号加载后会自动连上。
6. 回到 http://127.0.0.1:6185 → `数据与日志 → 日志`，出现 `aiocqhttp(OneBot v11) 适配器已连接。` 即打通。

## 配置大模型

WebUI → `模型提供商` → 已建好 `deepseek`（`https://api.deepseek.com/v1`，模型 `deepseek-flash`），只需填 API Key。

命令行方式：

```
runtime\python\cpython-3.12.15-windows-x86_64-none\python.exe tools\apply_key_and_test.py sk-xxxx
```

`apply_key_and_test.py` 会先实际请求一次接口验证 key，再写入配置；`tools\set_api_key.py` 只写配置不验证。

**思考模式已关闭**（`provider[].custom_extra_body = {"thinking": {"type": "disabled"}}`）。实测同一个问题：

| 模式 | 耗时 | 输出 tokens |
| --- | --- | --- |
| 关闭思考 | 1.03s | 51 |
| 开启思考 | 2.09s | 263（含 315 字思维链） |

群聊场景建议保持关闭（更快更省）；想要更高质量就把它改回 `enabled`，重启 AstrBot 生效。
注意开启后 AstrBot 带工具调用时若没回传 `reasoning_content`，DeepSeek 会返回 400，这也是默认关闭的原因之一。

改完重启 AstrBot。

## 群聊行为

- 群里 **@机器人** 就会回复；`/` 开头的指令（`/reset`、`/help`、`/sid` 等）也生效。
- 私聊默认直接回复。
- 想让它只在指定群/人说话：`配置文件 → 访问控制 → 白名单` 填会话 ID（发 `/sid` 可查）。
- 建议给号设个「机器人」人设：`配置文件 → 人设`。

## 风险

SnowLuma 走的是非官方协议，违反《QQ 用户协议》，存在封号风险。小号相对安全，但仍建议：不要进大群刷屏、不要高频主动发言、不要频繁异地登录。介意风险就走官方 QQ 机器人开放平台。
