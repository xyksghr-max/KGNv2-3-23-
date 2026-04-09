# T1：KGN-Pro 资产接入准备

## 1. 文档目标

本文档是 `T1：KGN-Pro 资产接入准备层` 的正式产出，目标是把 `KGN-Pro-main` 中与论文3相关的候选资产整理成一份可直接指导后续实现的迁移映射清单。

本模块只做：

- 静态审计
- 资产分类
- 迁移边界锁定
- 后续 `T2 / T3 / T4` 的挂接建议

本模块不做：

- 不修改 `KGN-main` 主训练链
- 不接入 `EPro-PnP`
- 不新增运行时目录
- 不替换当前 `KGN-main` 的测试 / 推理主链

## 2. 硬边界

### 2.1 本模块明确禁止的事情

- 禁止直接用 `KGN-Pro-main/src/test.py` 替换当前 `KGN-main` 的测试主链。
- 禁止直接用 `KGN-Pro-main/src/keypoint_graspnet.py` 替换当前 `KGN-main` 的推理主链。
- 禁止直接用 `KGN-Pro-main/src/lib/pose_recover/` 替换当前 `KGN-main` 的 PnP / pose recovery 主链。
- 禁止在 `T1` 中接入 `EPro-PnP-6DoF_v2/` 作为运行时依赖。
- 禁止把“论文3论文文本中的方法”直接等同于“KGN-Pro-main 已完整实现的方法”。

### 2.2 T1 的结论口径

- `KGN-Pro-main` 不是完整的论文3工程落地版。
- `KGN-Pro-main` 的真实形态更接近：
  - `KGNv2` 主链保留
  - 训练侧局部拼接了 `EPro-PnP / Monte-Carlo pose loss / w2d`
- 因此后续迁移策略必须是：
  - 只挑真正有用的局部资产
  - 只迁移能解释清楚、能独立验证的部分
  - 绝不整体照搬主链

## 3. KGN-Pro-main 主链接入事实

### 3.1 训练侧真正接入了什么

`KGN-Pro-main` 中，训练侧确实接入了部分论文3风格的新内容，主要调用链为：

- [main.py](/home/xyk/KGN-main/KGN-Pro-main/src/main.py)
  - 通过 `train_factory` 创建 `Trainer`
  - 调用 `trainer.train(...)` / `trainer.val(...)`
- [base_trainer.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/trains/base_trainer.py)
  - `run_epoch(...)` 中额外调用 `compute_loss(...)`
  - `compute_loss(...)` 中真实实例化并调用 `EProPnP6DoF`
  - 同时真实调用 `MonteCarloPoseLoss`
- [grasp_pose.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/trains/grasp_pose.py)
  - `post_process(...)` 中调用 `grasp_pose_post_process_pro(...)`
- [sample/grasp_pose.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/datasets/sample/grasp_pose.py)
  - 训练样本里额外打包 `ret['grasp_pose']`

因此可以确认：

- 论文3训练侧“概率姿态监督”的影子，不是只存在于目录里
- 它确实以“额外训练损失”的形式接到了训练流程中

### 3.2 推理侧没有被真正替换

`KGN-Pro-main` 的测试 / 推理主链并没有被论文3式 probabilistic PnP 主流程替换。真实调用链仍然是：

- [test.py](/home/xyk/KGN-main/KGN-Pro-main/src/test.py)
  - 使用 `PnPSolverFactory`
- [pnp_solver_factory.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/pose_recover/pnp_solver_factory.py)
  - 仍然只注册 `cvEPnP / cvP3P / cvIPPE`
- [keypoint_graspnet.py](/home/xyk/KGN-main/KGN-Pro-main/src/keypoint_graspnet.py)
  - 在 `generate(...)` 中逐候选调用 `self.pnp_solver.solve_pnp(...)`
  - 之后仍走 `sep_scale_branch` 的确定性修正链

因此可以确认：

- `KGN-Pro-main` 没有把论文3的 probabilistic inference 主张落成新的测试 / 推理主链
- 这也是为什么后续 T1 明确禁止替换当前 `KGN-main` 的主测试 / 主推理链

## 4. 迁移资产总表

下表统一使用以下表头：

- `论文角色`：该资产在论文3里服务什么思想
- `代码角色`：该资产在 `KGN-Pro-main` 中到底承担什么作用
- `主链接入情况`：是否真的进入 `KGN-Pro-main` 主训练或主推理链
- `迁移建议`：可直接迁移 / 可部分迁移 / 只能参考逻辑 / 明确不迁移
- `后续模块`：更适合归属到 `T2 / T3 / T4`
- `风险与禁止事项`：迁移时必须避免什么

| 资产 | 论文角色 | 代码角色 | 主链接入情况 | 迁移建议 | 后续模块 | 风险与禁止事项 |
| --- | --- | --- | --- | --- | --- | --- |
| [src/lib/models/monte_carlo_pose_loss.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/models/monte_carlo_pose_loss.py) | 训练侧 pose distribution supervision | 独立的 `MonteCarloPoseLoss` 模块 | 已接入训练侧，通过 `base_trainer.compute_loss(...)` 调用 | 可直接迁移 | `T3` | 模块本身可迁，但不能单独迁入后就宣称“论文3已实现”；仍需新的数据流与损失接线 |
| [src/lib/trains/base_trainer.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/trains/base_trainer.py) 中的 `compute_loss(...)` | probabilistic PnP + MC pose supervision | 训练侧拼接式额外 loss 主体 | 已接入训练侧，但未替换测试/推理主链 | 可部分迁移 | `T3` | 不能直接复制；包含大量硬编码与强耦合，只能拆逻辑后重写 |
| [src/lib/utils/post_process.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/utils/post_process.py) 中的 `grasp_pose_post_process_pro(...)` | 训练侧 differentiable post-process / tensor化坐标变换 | 给 trainer-side `compute_loss(...)` 提供 tensor 版后处理 | 已接入训练侧 `GraspPoseTrainer.post_process(...)`，未进入测试主链 | 可部分迁移 | `T3` | 只适合作为训练侧辅助工具；不能拿它替换现有测试后处理 |
| [src/lib/datasets/sample/grasp_pose.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/datasets/sample/grasp_pose.py) 中的 `grasp_pose` 打包 | multi-grasp target supervision | 训练样本额外提供固定形状 `grasp_pose` | 已接入训练侧 batch，但实现强依赖固定形状 | 只能参考逻辑 | `T4` | 不可直接照搬；存在 `TARGET_NUM_POSES_PER_SAMPLE`、`TARGET_BATCH_SIZE` 等硬编码 |
| [EPro-PnP-6DoF_v2/](/home/xyk/KGN-main/KGN-Pro-main/EPro-PnP-6DoF_v2/) | probabilistic PnP 核心依赖 | 第三方/外带式依赖目录 | 训练侧通过 `sys.path` 与 `base_trainer.py` 局部引用 | 可部分迁移 | `T3` | 在 `T1` 只作为依赖候选；不得现在接入，不得整体并入主运行时 |
| [src/lib/opts.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/opts.py) 中的 `w2d/x2d` 头声明 | confidence / 2D correspondence 相关接口意图 | 新增了 `w2d:2`、`x2d:8` 头定义 | `w2d` 被训练侧消费；`x2d` 仅见声明，未见主链消费 | 只能参考逻辑 | `T2 / T3` | 不得直接把“有头定义”当成“主链已实现”；特别是 `x2d` 不能视为已落地能力 |
| [src/test.py](/home/xyk/KGN-main/KGN-Pro-main/src/test.py) | 论文3若完整实现应体现新的测试主链 | 实际仍是旧 KGNv2 测试入口 | 已接入主测试链，但逻辑未升级 | 明确不迁移 | 无 | 这是旧链，不可误判为论文3测试实现 |
| [src/keypoint_graspnet.py](/home/xyk/KGN-main/KGN-Pro-main/src/keypoint_graspnet.py) | 论文3若完整实现应体现新的推理恢复链 | 实际仍是 `solve_pnp + sep_scale_branch` | 已接入主推理链，但仍是旧逻辑 | 明确不迁移 | 无 | 禁止用它替换 `KGN-main` 主推理链 |
| [src/lib/pose_recover/pnp_solver_factory.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/pose_recover/pnp_solver_factory.py) | 论文3若完整实现应体现新的 pose recovery factory | 实际仅注册 `cvEPnP / cvP3P / cvIPPE` | 已接入主推理链，但无论文3主张的 probabilistic factory | 明确不迁移 | 无 | 这是旧 PnP 工厂，不可视作论文3接入证据 |

## 5. 五个重点资产逐项审计

### 5.1 `monte_carlo_pose_loss.py`

文件：

- [src/lib/models/monte_carlo_pose_loss.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/models/monte_carlo_pose_loss.py)

审计结论：

- 这是 `KGN-Pro-main` 中最干净、最独立、最适合后续迁移的论文3风格资产之一。
- 它的职责单一，只有 `MonteCarloPoseLoss` 一个模块。
- 它在 `KGN-Pro-main` 中不是摆设：
  - 被 [base_trainer.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/trains/base_trainer.py) 实例化并在 `compute_loss(...)` 中调用。
- 它本身不依赖当前 `KGN-main` 的推理主链，因此适合作为 `T3` 的“可直接迁移候选”。

迁移建议：

- 允许后续直接拷入 `KGN-main`，但只在 `T3` 实施。
- 拷入后仍需重新设计：
  - loss 入口
  - normalization 统计
  - 与 batch / pose sample 的对接方式

### 5.2 `base_trainer.py`

文件：

- [src/lib/trains/base_trainer.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/trains/base_trainer.py)

审计结论：

- 这是论文3训练侧真正“有货”的核心文件。
- 真实主链事实：
  - [main.py](/home/xyk/KGN-main/KGN-Pro-main/src/main.py) 调用 `trainer.train/val`
  - `BaseTrainer.run_epoch(...)` 中额外调用 `compute_loss(...)`
  - `compute_loss(...)` 中真实用了：
    - `EProPnP6DoF`
    - `PerspectiveCamera`
    - `AdaptiveHuberPnPCost`
    - `MonteCarloPoseLoss`
- 但该实现是“训练侧拼接原型”，不是干净可复用模块，存在大量强耦合硬编码，例如：
  - 固定 `device = cuda:0`
  - 固定 `meta['c'] = [320, 240]`
  - 固定 `meta['s'] = [672, 512]`
  - 固定相机内参矩阵
  - 固定 `K=128`
  - 固定 3D 点模板
  - 对 `w2d` 做特定的扁平化、排序、截断、均值处理

迁移建议：

- 只能作为 `T3` 的逻辑参考源，不允许整段复制到 `KGN-main`。
- 后续应拆成几个独立子问题重写：
  - 2D 点构造
  - 训练侧可微后处理
  - 置信权重构造
  - EPro-PnP 包装层
  - Monte-Carlo pose loss 接线

### 5.3 `post_process.py`

文件：

- [src/lib/utils/post_process.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/utils/post_process.py)

审计结论：

- `grasp_pose_post_process_pro(...)` 的价值在于：
  - 它保留 tensor 形式
  - 它服务训练侧 `compute_loss(...)`
- 它确实接到了训练链：
  - [grasp_pose.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/trains/grasp_pose.py) 中 `GraspPoseTrainer.post_process(...)` 调用了它
- 但它没有接入测试主链：
  - `save_result(...)` 仍然用旧 `grasp_pose_post_process(...)`

迁移建议：

- 可作为 `T3` 的局部可迁移函数参考。
- 不建议直接原样拷贝；建议按 `KGN-main` 当前训练接口重写一个最小版 tensor 后处理。

### 5.4 `sample/grasp_pose.py`

文件：

- [src/lib/datasets/sample/grasp_pose.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/datasets/sample/grasp_pose.py)

审计结论：

- 这部分体现了论文3式“多抓取 supervision”的真实工程需求：
  - 训练 batch 里额外提供 `grasp_pose`
- 但实现方式非常原型化，关键问题包括：
  - `TARGET_NUM_POSES_PER_SAMPLE = 80`
  - `TARGET_BATCH_SIZE` 根据 `len(grasp_poses_gt)` 做特殊判断
  - 长度不足时 repeat / pad
  - 长度过长时截断
- 它确实进入了训练 batch，但不适合作为 `KGN-main` 的 clean 实现模板。

迁移建议：

- 只保留“训练侧需要额外 GT pose supervision”这个思想。
- 后续 `T4` 应重新设计：
  - 可变长度 GT
  - 不绑定固定 batch 形状
  - 不绑定固定 `80` 个 pose

### 5.5 `EPro-PnP-6DoF_v2/`

目录：

- [EPro-PnP-6DoF_v2/](/home/xyk/KGN-main/KGN-Pro-main/EPro-PnP-6DoF_v2)

审计结论：

- 这是论文3训练侧概率姿态估计的重要依赖来源。
- 它不是 `KGN-Pro-main` 自己重写的一小段函数，而是一整套外带目录。
- 在当前 `KGN-Pro-main` 中，它通过 `sys.path.append(...)` 被训练侧引用。
- 它对 `T3` 有价值，但当前阶段只应被视作依赖候选，不应直接接入。

迁移建议：

- `T1` 不接入、不 vendor、不改 `KGN-main` 运行时。
- `T3` 再决定是：
  - vendor 最小子集
  - 还是保留外部依赖方式

## 6. 非重点旧逻辑隔离说明

以下区域虽然在 `KGN-Pro-main` 中真实存在并被主流程调用，但它们本质上仍是旧 `KGNv2` 逻辑，因此必须写进“禁止直接迁移”区。

### 6.1 旧测试主链

文件：

- [src/test.py](/home/xyk/KGN-main/KGN-Pro-main/src/test.py)

结论：

- 主测试入口仍然是：
  - 构建 `Detector`
  - 构建 `PnPSolver`
  - 调 `KeypointGraspNet.generate(...)`
- 没有体现论文3式 probabilistic inference 主链。

### 6.2 旧推理主链

文件：

- [src/keypoint_graspnet.py](/home/xyk/KGN-main/KGN-Pro-main/src/keypoint_graspnet.py)

结论：

- `generate(...)` 里仍逐候选调用 `self.pnp_solver.solve_pnp(...)`
- 之后仍按 `sep_scale_branch` 做平移尺度修正
- 这说明 `KGN-Pro-main` 的推理侧仍是旧 KGN/KGNv2 确定性恢复链

### 6.3 旧 PnP 工厂

文件：

- [src/lib/pose_recover/pnp_solver_factory.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/pose_recover/pnp_solver_factory.py)

结论：

- 工厂里仍然只有：
  - `cvEPnP`
  - `cvP3P`
  - `cvIPPE`
- 没有论文3主张的 probabilistic solver factory

### 6.4 `x2d` 头只见声明、不见消费

文件：

- [src/lib/opts.py](/home/xyk/KGN-main/KGN-Pro-main/src/lib/opts.py)

结论：

- `opts.py` 中声明了：
  - `w2d: 2`
  - `x2d: 8`
- 但从 `src/` 范围的静态搜索看：
  - `w2d` 被 `base_trainer.py` 消费
  - `x2d` 未见实际主链消费

因此：

- `x2d` 不能被当成“已经接入主链的论文3实现”
- 它最多只能当作接口意图参考

## 7. 后续模块挂接建议

### 7.1 T2 优先吸收什么

`T2` 不应直接搬 `KGN-Pro-main` 某个完整文件。更合理的是吸收：

- `w2d` 所代表的“2D correspondence reliability / confidence weighting”思想
- 但应落在 `KGN-main` 现有 `conf_branch / conf_loss / conf_fusion` 主线上做低风险升级

建议：

- `T2` 以思想迁移为主
- 不直接复制 `base_trainer.py` 或 `post_process.py`

### 7.2 T3 才考虑吸收什么

`T3` 更适合吸收的资产是：

- `monte_carlo_pose_loss.py`
- `base_trainer.py` 中 `compute_loss(...)` 的分解逻辑
- `post_process.py` 中的 tensor 版后处理思路
- `EPro-PnP-6DoF_v2/` 作为依赖候选

建议：

- `T3` 只在训练侧做 clean prototype
- 仍不替换 `KGN-main` 当前测试 / 推理主链

### 7.3 T4 可能复用什么

`T4` 可以参考：

- `sample/grasp_pose.py` 中“训练 batch 里额外打包 pose GT”这个方向

但必须重写：

- GT matching 方案
- 变长处理
- batch 对齐策略

## 8. T1 通过标准核对

本次 T1 文档已满足以下静态验证要求：

- 覆盖了 5 个重点资产：
  - `monte_carlo_pose_loss.py`
  - `base_trainer.py`
  - `post_process.py`
  - `sample/grasp_pose.py`
  - `EPro-PnP-6DoF_v2/`
- 覆盖了至少 3 个“明确不迁移”的旧逻辑区域：
  - `test.py`
  - `keypoint_graspnet.py`
  - `pose_recover/pnp_solver_factory.py`
- 每个结论都能追溯到具体文件
- 没有修改 `KGN-main` 主训练链
- 没有引入新运行时依赖

因此后续进入 `T2 / T3 / T4` 时，可以直接以本文档为迁移边界，不需要重新对整份 `KGN-Pro-main` 做一轮全面真实性审计。
