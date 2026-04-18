# SSH 免密和远程 Codex

## 1. 文档用途

本文档记录本地 Ubuntu 20.04 通过 VSCode Remote-SSH 连接 AutoDL 云服务器，并在远程 VSCode 中使用 Codex 插件直接操作云端 `KGN-main` 工作区的配置过程。

本文档记录：

- SSH key 免密登录
- VSCode Remote-SSH Host 配置
- 本地 Clash Party 代理通过 SSH 反向转发给云端
- 远程 VSCode / 远程终端代理配置
- 本地 `.codex` 授权信息迁移到云端
- 远程 Codex 沙箱诊断结果
- 远程 Codex 后续使用规则建议

本文档不记录：

- AutoDL 登录密码
- SSH 私钥内容
- Codex `auth.json` 内容
- GitHub token
- 任何可直接复用的账号凭据

## 2. 当前目标

目标是在本地 VSCode 通过 Remote-SSH 连接云服务器后，让远程 VSCode 中的 Codex 插件把云端目录作为工作区：

```text
/root/autodl-tmp/KGN-main
```

从而支持：

- 直接阅读云端代码
- 直接修改云端代码
- 直接审查云端 `git diff`
- 直接运行云端环境检查和短测试
- 后续配合 GitHub 在本地与云端之间同步代码

当前阶段已经从单纯环境搭建进入 T3.1 验证与算法修改阶段，因此允许云端 Codex 参与小范围算法修改、训练侧验证和日志分析。

## 3. 本地与云端角色

本地机器：

```text
系统：Ubuntu 20.04
本地用户：xyk
本地项目：/home/xyk/KGN-main
本地 Codex：/home/xyk/.codex
本地代理：Clash Party
Clash mixed 端口：7890
```

云服务器：

```text
平台：AutoDL
用户：root
云端项目：/root/autodl-tmp/KGN-main
云端 Codex：/root/.codex
GPU：RTX 4090 24GB
系统：Ubuntu 20.04
```

两套 Codex 目录关系：

```text
本地 Codex: /home/xyk/.codex
云端 Codex: /root/.codex
```

迁移时刻之前，云端复制了一份本地 `.codex` 历史和授权。迁移之后，本地和云端各自记录新会话，互不自动同步。

推荐分工：

- 本地 Codex：适合论文整理、文档、本地代码开发、较大重构。
- 云端 Codex：适合云端环境检查、训练日志分析、小范围算法修改、短验证和 Git 管理。
- GitHub：作为本地与云端代码同步中心。

## 4. SSH key 免密登录

本地生成 SSH key：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh

ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_autodl_kgn -C "autodl-kgn"

chmod 600 ~/.ssh/id_ed25519_autodl_kgn
chmod 644 ~/.ssh/id_ed25519_autodl_kgn.pub
```

已生成：

```text
私钥：/home/xyk/.ssh/id_ed25519_autodl_kgn
公钥：/home/xyk/.ssh/id_ed25519_autodl_kgn.pub
```

已确认 key fingerprint：

```text
SHA256:J04SqPAZMBfu40ZwOqxL6aeCIW0ldvbLds0zUHR5Zzw autodl-kgn
```

上传公钥到 AutoDL：

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_autodl_kgn.pub -p 46224 root@connect.nmb1.seetacloud.com
```

已确认：

```text
Number of key(s) added: 1
```

说明：

- `46224` 是当前 AutoDL 实例 SSH 端口，释放/重开实例后可能变化。
- SSH 密码只在 `ssh-copy-id` 时手动输入，不写入文档。
- 私钥不能上传到 GitHub，不能放进项目目录。

## 5. SSH config

本地 SSH 配置文件：

```text
/home/xyk/.ssh/config
```

当前推荐 Host：

```sshconfig
Host autodl-kgn
    HostName connect.nmb1.seetacloud.com
    Port 46224
    User root
    IdentityFile ~/.ssh/id_ed25519_autodl_kgn
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    ExitOnForwardFailure yes
    RemoteForward 127.0.0.1:17890 127.0.0.1:7890
```

配置含义：

```text
Host autodl-kgn
  VSCode 和终端使用的别名。

HostName connect.nmb1.seetacloud.com
  AutoDL SSH 域名。

Port 46224
  AutoDL 当前实例端口。

IdentityFile ~/.ssh/id_ed25519_autodl_kgn
  使用本地专用私钥登录。

RemoteForward 127.0.0.1:17890 127.0.0.1:7890
  云端 127.0.0.1:17890 反向映射到本地 127.0.0.1:7890。

ExitOnForwardFailure yes
  如果反向代理端口绑定失败，则 SSH 直接失败，避免静默无代理。
```

免密测试：

```bash
ssh autodl-kgn
```

已确认可免密登录。

注意：

- 如果本地已经开着一个 `ssh autodl-kgn` 会话，它会占用云端 `127.0.0.1:17890`。
- VSCode 再连接同一个 Host 时也要绑定 `17890`，可能因为端口冲突失败。
- 解决方法是退出手动 SSH 会话，或给不同用途配置不同远程端口。

## 6. Clash Party 代理

本地 Clash Party 当前端口：

```text
mixed 端口：7890
socks 端口：7891
http 端口：7892
```

当前实际使用：

```text
本地 127.0.0.1:7890
```

本地代理测试：

```bash
curl -I --proxy http://127.0.0.1:7890 https://chatgpt.com
```

已观察到：

```text
HTTP/1.1 200 Connection established
HTTP/2 403
```

说明：

- `HTTP/2 403` 是 Cloudflare 对 `curl` 的 challenge。
- 该结果表示本地代理链路能连到 `chatgpt.com`，不是 timeout。

## 7. 远程代理验证

通过 `ssh autodl-kgn` 或 VSCode Remote-SSH 连接云端后，在云端执行：

```bash
curl -I -m 10 --proxy http://127.0.0.1:17890 https://chatgpt.com
```

已确认结果：

```text
HTTP/1.1 200 Connection established
HTTP/2 403
```

说明：

- 云端 `127.0.0.1:17890` 已经通过 SSH RemoteForward 转发到本地 Clash `127.0.0.1:7890`。
- 只要不是 `Connection timed out`，就说明网络链路打通。

## 8. 远程 VSCode 代理配置

远程 VSCode Settings JSON 已配置：

```json
{
  "http.proxy": "http://127.0.0.1:17890",
  "http.proxySupport": "on",
  "http.proxyStrictSSL": false,
  "terminal.integrated.env.linux": {
    "HTTP_PROXY": "http://127.0.0.1:17890",
    "HTTPS_PROXY": "http://127.0.0.1:17890",
    "http_proxy": "http://127.0.0.1:17890",
    "https_proxy": "http://127.0.0.1:17890"
  }
}
```

远程 VSCode Server 环境脚本：

```bash
mkdir -p ~/.vscode-server

cat > ~/.vscode-server/server-env-setup <<'EOF'
export HTTP_PROXY=http://127.0.0.1:17890
export HTTPS_PROXY=http://127.0.0.1:17890
export http_proxy=http://127.0.0.1:17890
export https_proxy=http://127.0.0.1:17890
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
EOF

chmod +x ~/.vscode-server/server-env-setup
```

生效方式：

```text
Ctrl + Shift + P
Remote-SSH: Kill VS Code Server on Host...
选择 autodl-kgn
重新连接 autodl-kgn
打开 /root/autodl-tmp/KGN-main
```

新终端验证：

```bash
echo $HTTP_PROXY
curl -I -m 10 https://chatgpt.com
```

已确认：

```text
http://127.0.0.1:17890
HTTP/1.1 200 Connection established
HTTP/2 403
```

## 9. Codex 授权迁移

本地 `.codex` 检查：

```bash
ls -lah ~/.codex
```

本地 `.codex` 中关键文件：

```text
auth.json
config.toml
installation_id
session_index.jsonl
sessions/
archived_sessions/
logs_2.sqlite
state_5.sqlite
```

用户希望保留 Codex 历史和 IDE 背景，因此采用带历史迁移方案，但排除临时目录和部分缓存。

本地打包：

```bash
cd ~

tar \
  --exclude='.codex/tmp' \
  --exclude='.codex/.tmp' \
  --exclude='.codex/cache' \
  --exclude='.codex/shell_snapshots' \
  -czf /tmp/codex-auth-with-history.tar.gz \
  .codex
```

已观察到包大小：

```text
183M
```

上传：

```bash
scp /tmp/codex-auth-with-history.tar.gz autodl-kgn:/root/
```

云端解包：

```bash
cd /root

if [ -d ~/.codex ]; then
  mv ~/.codex ~/.codex.backup.$(date +%Y%m%d-%H%M%S)
fi

tar -xzf codex-auth-with-history.tar.gz
```

因为本地打包保留了本地 UID，云端解压后曾显示所有者为 `1000:1000`。已修复：

```bash
chown -R root:root ~/.codex
chmod 700 ~/.codex
find ~/.codex -type d -exec chmod 700 {} \;
find ~/.codex -type f -exec chmod 600 {} \;

rm codex-auth-with-history.tar.gz
```

已确认：

```text
/root/.codex/auth.json      root root 600
/root/.codex/config.toml    root root 600
```

重要说明：

- `.codex` 只能放在 `/root/.codex`，不要放入 `/root/autodl-tmp/KGN-main`。
- 不要提交 `.codex`、`auth.json`、SSH key 或 token。
- 迁移后，本地和云端 `.codex` 各自记录新会话，不会自动同步。

## 10. Codex 项目信任配置

迁移后，云端 `~/.codex/config.toml` 已包含本地项目路径：

```toml
[projects."/home/xyk/KGN-main"]
trust_level = "trusted"
```

已补充云端项目路径：

```toml
[projects."/root/autodl-tmp/KGN-main"]
trust_level = "trusted"
```

完整相关片段：

```toml
model = "gpt-5.4"
model_reasoning_effort = "xhigh"

[plugins."github@openai-curated"]
enabled = true

[projects."/home/xyk/MakingGames"]
trust_level = "trusted"

[projects."/home/xyk/KGN-main"]
trust_level = "trusted"

[projects."/root/autodl-tmp/KGN-main"]
trust_level = "trusted"
```

说明：

- 本地路径和云端路径是两个不同 workspace。
- 云端 Codex 当前应使用 `/root/autodl-tmp/KGN-main` 作为主工作区。

## 11. 远程 Codex 可用状态

已确认：

```text
VSCode 左下角：SSH: autodl-kgn
工作区：KGN-main [SSH: autodl-kgn]
Codex 面板：可打开
输入框：Ask Codex anything...
IDE 背景信息：可见
当前分支显示：feat/t3-prob-pose-loss-clean
```

这说明：

- VSCode 正通过 `autodl-kgn` 连接云端。
- Codex 面板运行在远程 VSCode 工作区。
- Codex 能看到云端 `/root/autodl-tmp/KGN-main`，不是本地 `/home/xyk/KGN-main`。

## 12. 远程 Codex 沙箱诊断

现象：

- 本地 Codex 不频繁询问“是否允许沙箱外执行”。
- 远程 Codex 会提示沙箱启动失败，并要求确认在沙箱外执行命令。

诊断命令：

```bash
cd /root/autodl-tmp/KGN-main

sed -n '1,80p' ~/.codex/config.toml

unshare -Ur true
echo "unshare_userns_exit=$?"

cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null || true
grep -E 'CapEff|CapPrm|CapBnd|NoNewPrivs|Seccomp' /proc/self/status
```

已确认输出：

```text
unshare: unshare failed: Operation not permitted
unshare_userns_exit=1

cat /proc/sys/kernel/unprivileged_userns_clone
1

CapPrm: 00000000a80425fb
CapEff: 00000000a80425fb
CapBnd: 00000000a80425fb
NoNewPrivs: 0
Seccomp: 2
Seccomp_filters: 1
```

结论：

- `unprivileged_userns_clone=1` 表示宿主机内核层面允许非特权 user namespace。
- `unshare -Ur true` 失败，说明容器层仍然阻止了相关系统调用。
- `Seccomp: 2` 和 `Seccomp_filters: 1` 表示当前 AutoDL 容器启用了 seccomp syscall filter。
- 远程 Codex 沙箱不可用是 AutoDL 容器运行策略导致，不是 KGN-main、SSH、代理或 `.codex` 问题。

当前判断：

- 不能在容器内部通过普通配置把远程 Codex 调成与本地完全相同的沙箱体验。
- 除非 AutoDL 提供特权容器、放宽 seccomp 或支持 user namespace 的实例选项，否则完整沙箱大概率无法启用。

## 13. 权限策略

远程 Codex 可以用于算法修改，但需要区分权限风险。

可以长期允许的只读命令：

```text
pwd
ls
find
rg
sed -n
cat
head
tail
wc
du
df
git status
git branch
git remote -v
git log
git diff
which python
python -V
printenv
nvidia-smi
```

建议保留人工确认的命令：

```text
rm
mv
chmod -R
chown -R
git reset
git clean
pip install
conda install
apt-get install
python main.py
python test.py
python main_data_generate.py
git commit
git push
```

原因：

- 云端没有 Codex 沙箱时，命令直接作用于 `/root` 和 `/root/autodl-tmp`。
- 错误命令可能删除数据、污染环境、覆盖实验结果、误推 GitHub 或启动长训练。
- 云端不会直接删除本地 `/home/xyk/KGN-main`，但可能影响云端数据、环境、checkpoint 和 GitHub。

## 14. 全部权限与规则

如果后续为了减少弹窗选择给远程 Codex 更宽松权限，需要明确：

```text
规则不是硬沙箱。
规则能约束模型行为，但不能在系统层阻止命令。
```

推荐在项目根目录创建：

```text
/root/autodl-tmp/KGN-main/AGENTS.md
```

建议内容：

```markdown
# KGN-main Cloud Safety Rules

This is the AutoDL cloud workspace for KGN-main.

## Workspace

- Main workspace: `/root/autodl-tmp/KGN-main`
- Conda env: `kgnv2`
- Activate env with:
  `source /root/miniconda3/etc/profile.d/conda.sh && conda activate kgnv2`

## Absolute Prohibitions

- Never delete, overwrite, move, or mass-edit `data/`, `pretrained_weights/`, `exp/`, `.git/`, `.codex/`, or conda environments.
- Never run `rm -rf`, `git reset --hard`, `git clean`, `git checkout -- .`, or destructive `find -delete`.
- Never install, uninstall, or upgrade dependencies unless explicitly requested.
- Never upgrade `torch`, `torchvision`, or `torchaudio`.
- Never install `pyro-ppl`.
- Never run long training unless explicitly requested and using `tmux` or `screen`.
- Never run `git push` unless explicitly requested.

## Required Workflow

- Before changes: run `git status --short --branch`.
- Before editing: state intended files.
- After editing: show `git diff --stat` and summarize touched files.
- Before commit or push: ask the user.
- Before training longer than 10 minutes: ask the user.

## Allowed

- Read files.
- Search code.
- Edit source files related to the requested task.
- Run short checks and smoke tests.
- Update docs when requested.
```

可选软保护：

```bash
cd /root/autodl-tmp/KGN-main
chmod -R a-w data pretrained_weights
```

说明：

- 这能防止普通误写或误删数据和权重。
- 因为当前用户是 `root`，`root` 仍可恢复权限，所以这不是绝对保护。
- 恢复写权限：

```bash
chmod -R u+w data pretrained_weights
```

## 15. 当前推荐工作流

推荐云端 Codex 使用方式：

```text
云端 Codex：
  环境检查
  训练日志分析
  小范围算法修改
  短验证
  git status / git diff 审查

本地 Codex：
  较大代码设计
  文档整理
  本地分支维护
  论文相关材料

GitHub：
  本地与云端代码同步中心
```

T3.1 后续建议流程：

1. 云端确认当前基线分支为 `feat/t3-prob-pose-loss-clean`。
2. 云端 `git status --short --branch`，确认工作区干净。
3. 确认 `src/lib/models/prob_pose_aux_loss.py`、`src/lib/models/monte_carlo_pose_loss.py`、`src/lib/third_party/epropnp/pnp/` 存在。
4. 确认 `KGN-Pro-main/` 只作为参考目录存在，且 `git status --short --ignored | grep KGN-Pro-main` 输出 `!! KGN-Pro-main/`。
5. 不直接在 `feat/t3-prob-pose-loss-clean` 上做功能修改；开始验证或修复前先新建分支。
6. 云端 Codex 审查 T3.1 相关文件，不碰数据和依赖。
7. 运行最小 forward / dataset / loss 检查。
8. 运行 1 epoch 或更短 smoke train。
9. 记录命令和结果到 `docs/云服务器实验命令记录.md` 与 `docs/云服务器现状.md`。
10. `git diff` 审查后再决定是否 commit / push。

当前云端交接状态：

```text
基线分支：feat/t3-prob-pose-loss-clean
远程跟踪：origin/feat/t3-prob-pose-loss-clean
工作区：clean
T3.1 代码：已同步
KGN-Pro-main：已上传并解压到 /root/autodl-tmp/KGN-main/KGN-Pro-main
KGN-Pro-main Git 状态：被 .gitignore 忽略，仅作参考
```

## 16. 常见问题

### VSCode 无法连接 `autodl-kgn`

可能原因：

- 本地已有手动 `ssh autodl-kgn` 会话占用了远程 `17890`。
- `ExitOnForwardFailure yes` 导致端口转发失败后 VSCode 直接断开。

处理：

```bash
exit
```

退出手动 SSH 会话后，用 VSCode 重新连接：

```text
Remote-SSH: Connect to Host... -> autodl-kgn
```

### 云端 `curl https://chatgpt.com` timeout

先检查是否带代理：

```bash
echo $HTTP_PROXY
curl -I -m 10 --proxy http://127.0.0.1:17890 https://chatgpt.com
```

如果带代理能返回 `HTTP/2 403`，说明隧道正常。需要检查远程 VSCode settings 或重新打开终端。

### `HTTP/2 403` 是否是失败

不是当前目标下的失败。`curl` 被 Cloudflare challenge 返回 403 是常见现象。判断重点是：

```text
timeout：失败
HTTP/1.1 200 Connection established + HTTP/2 403：代理链路可用
```

### 远程 Codex 为什么比本地多确认

因为 AutoDL 容器中 Codex 沙箱启动失败。命令退化为沙箱外执行，为安全起见会要求更多确认。

### 远程 Codex 会不会删除本地文件

不会直接删除本地 `/home/xyk/KGN-main`，因为当前工作区是：

```text
KGN-main [SSH: autodl-kgn]
```

它直接影响的是云端：

```text
/root/autodl-tmp/KGN-main
/root/.codex
/root/autodl-tmp/conda
```

但如果它执行 `git push`、`scp` 或其他跨机器命令，可能间接影响本地/远程同步结果，所以仍需谨慎。

## 17. 当前结论

当前链路已经完成：

```text
本地 VSCode
  -> Remote-SSH Host autodl-kgn
  -> AutoDL 云服务器
  -> /root/autodl-tmp/KGN-main
  -> 远程 VSCode Codex 插件
  -> SSH RemoteForward
  -> 本地 Clash 7890
  -> Codex / ChatGPT 服务
```

当前可用能力：

- 本地 VSCode 免密连接云服务器。
- 远程 VSCode 打开云端 `KGN-main`。
- 远程 Codex 能读取云端工作区上下文。
- 云端终端和 VSCode 能通过本地 Clash 访问外网。
- 云端 `.codex` 授权与历史已经迁移。

当前限制：

- AutoDL 容器内远程 Codex 沙箱不可用。
- 远程 Codex 执行命令会比本地更频繁要求确认。
- 若开启宽松权限，需要依靠 `AGENTS.md`、Git diff、人工确认和目录软保护降低风险。
