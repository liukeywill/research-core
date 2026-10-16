# Research Core

Vibe Research 与 Auto Paper 共用的研究基础规范。这里维护研究问题与设计、文献证据、主张审查及版本追溯；人工核查和自动推进仍由各自 Skill 管理。

这是一组配套模块，不是新的自动触发 Skill。两个 Skill 随包内置同一提交的快照，安装和执行时无需再安装此仓库、联网下载或查找另一个 Skill。

| 模块 | 使用时机 |
|---|---|
| [question-design](references/question-design.md) | 选题、研究设计、最小验证与执行 |
| [evidence](references/evidence.md) | 检索、纳排、精读与证据登记 |
| [claims-review](references/claims-review.md) | 论证、论文写作、评审和最终核验 |
| [traceability](references/traceability.md) | 建项目、恢复、变更和版本追溯 |

使用入口：[Vibe Research](https://github.com/liukeywill/vibe-research)（逐阶段人工核查）、[Auto Paper](https://github.com/liukeywill/auto-paper)（连续科研成稿）。普通写作与表达编辑使用 [Vibe Writing](https://github.com/liukeywill/vibe-writing)。

## 维护方式

仅在本仓库修改共享规范，更新 module.json 的版本和文件哈希并提交。随后在本仓库运行：

```bash
python3 scripts/sync_consumers.py --target /path/to/vibe-research --target /path/to/auto-paper
python3 scripts/sync_consumers.py --target /path/to/vibe-research --target /path/to/auto-paper --check
```

脚本从本地已提交的来源读取模块，验证哈希并同步到目标 `shared/research-core/`，生成固定来源提交的 `shared/research-core.lock.json`。不联网、不提交、不推送；不覆盖检测到的消费者本地改动。更新后分别提交、验证并发布两个 Skill。正在进行的项目继续使用原快照，新项目使用更新版本。

Vibe Research 的 Markdown 记录和 Auto Paper 的 JSON 契约各自保留。共享的是研究语义与核验要求，不宣称已经实现项目格式自动转换。规范由两套工作流中共同的要求整理而来；原有第三方许可仍由相应技能与组件维护，本仓库不为它们重定许可证。
