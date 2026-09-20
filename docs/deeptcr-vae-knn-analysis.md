# DeepTCR VAE + KNN：用一个 7.87MB 的编码器做 TCR Repertoire 分析

**发布日期**: 2026-09-20
**作者**: DiVo Gen²AI 研发团队

---

## 一句话概要

DiVo Gen²AI 团队用 DeepTCR 的 VAE 编码器将 16.9 万条 TCR 序列编码为 256 维向量，并训练 KNN 分类器进行 TCR 结合型/非结合型判别，在 5-fold 交叉验证和未知肽段 hold-out 两种测试场景下均达到 **AUC 0.999**。整个训练在 CPU 上 10 分钟完成，模型仅 7.87MB——展示了一条与 GPU 大模型完全不同的轻量化 TCR 分析路线。

---

## 背景：TCR 测序数据的"理解"难题

肿瘤免疫治疗时代，TCR 测序（immunosequencing）已广泛应用于：

- 肿瘤浸润淋巴细胞的克隆扩增分析
- 免疫检查点治疗的响应预测
- CAR-T / TCR-T 细胞治疗的特异性评估

但原始 TCR 测序数据是数百万条 CDR3 氨基酸序列——**如何从序列中提取可分析的特征**是所有下游应用的基础难题。

传统方法用手工特征（CDR3 长度、氨基酸组成、理化性质），但 TCR 序列的特异性蕴含在复杂的序列模式中，手工特征难以捕获。

---

## DeepTCR：VAE 学习 TCR 序列的"语义"

DeepTCR（Sidhom et al., *Nature Communications* 2021，Johns Hopkins University）提供了一个优雅的方案：**用变分自编码器（VAE）学习 TCR 序列的潜在表示**。

### 架构

| 组件 | 说明 |
|------|------|
| 输入 | CDR3β 氨基酸序列 + Vβ/Jβ 基因使用 |
| 编码器 | 3 层卷积 + 全连接 → 256 维 latent 向量 |
| 解码器 | 从 latent 向量重构原始序列 |
| 训练目标 | 重构损失 + KL 散度 |

**256 维 latent 向量捕获了 TCR 序列的"语义"**——相似的 TCR 在潜在空间中距离近，不同的 TCR 距离远。这个空间天然支持聚类、最近邻分类、异常检测、可视化。

### DeepTCR 的学术地位

| 维度 | 说明 |
|------|------|
| 论文 | Nature Communications 2021（IF=14.7） |
| 第三方基准 | 2025 年 NAR Genomics 无监督 TCR 聚类基准测试中**保留率第一** |
| 工业采用 | Regeneron 制药用于高通量 dextramer-TCR 映射 |
| 引用期刊 | Nature Reviews Immunology、Science Advances、Genome Biology |
| 维护状态 | 持续更新至 2.1.29（2025），作者从 Johns Hopkins 到 Mt Sinai 持续维护 |

---

## 我们的实验：VAE 编码 + KNN 分类

### 实验设置

| 项目 | 详情 |
|------|------|
| VAE 权重 | DeepTCR 官方 checkpoint（7.87MB，119 个变量） |
| 编码数据 | VDJdb 2026-05-16：168,896 条 TCR 序列 |
| 分类器 | sklearn KNN（n_neighbors=5） |
| 分类任务 | 结合型 TCR vs 非结合型 TCR |
| 硬件 | CPU（无 GPU） |
| 总耗时 | ~10 分钟（编码 168k 序列 + KNN 训练） |

### 实验结果

| 测试场景 | AUC | Accuracy | F1 |
|----------|-----|----------|-----|
| **5-fold CV（随机划分）** | **0.9997** | 0.9996 | 0.9996 |
| **未知肽段 hold-out** | **0.9989** | 0.9987 | 0.9988 |

两个场景的 AUC 几乎一致（0.9997 vs 0.9989）——因为 KNN 分类**不看肽段**，只看 TCR 序列本身是否像"结合型 TCR"，所以肽段是否见过对结果影响很小。

---

## 诚实评估：0.999 AUC 意味着什么（和不意味着什么）

我们要明确这个数字回答的问题和没回答的问题：

### 它回答的问题

> "这个 TCR 像不像已知的结合型 TCR？"

VAE latent 空间能有效区分"已知结合型 TCR"和"随机配对的 TCR"。这对 TCR repertoire 粗筛有直接价值——快速标记患者 TCR 库中哪些克隆可能是抗原经验的。

### 它没回答的问题

> "这个 TCR 能不能结合这个特定肽段？"

因为 KNN 只看 TCR 序列，不看肽段。管线真正需要的是 TCR-肽段配对的特异性预测——这个问题由看肽段的模型（NetTCR/ERGO-II/DiVoPostTCR）回答。

### 信息泄漏说明

同一 TCR 可能结合多个肽段。如果它在训练集中作为"结合型"出现，在测试集中也作为"结合型"出现（即使配对不同肽段），KNN 会通过序列相似性正确分类。所以 0.999 不能与看肽段的模型（如 DiVoPostTCR 的 0.9814）直接比较——**它们在解不同的题**。

---

## 与 GPU 大模型路线的对比

| 维度 | DeepTCR VAE + KNN | DiVoPostTCR（ProtT5-XL 微调） |
|------|--------------------|------------------------------|
| 模型大小 | **7.87MB** | 9.3GB |
| 硬件需求 | **CPU** | GPU |
| 训练时间 | **10 分钟** | 2 小时 |
| 看肽段 | ❌ | ✅ |
| 任务 | TCR 序列分析（repertoire） | TCR-肽段结合预测 |
| 学术背景 | Nat Commun 2021 + 2025 基准 | 自研 |

**两条路线是互补的**：轻量 CPU 路线做 repertoire 粗筛（快、便宜、可本地部署），重量 GPU 路线做肽段特异性验证（精确但昂贵）。我们的管线用 DeepTCR 做 repertoire 分析层，同时用三个 CPU 工具（DeepTCR/NetTCR/ERGO-II）做交叉验证。

---

## 实际应用场景

### 场景 1：肿瘤浸润淋巴细胞分析

对患者肿瘤组织的 TCR 测序数据做 VAE 编码 → 聚类 → 发现扩增的 TCR 群组 → KNN 标记哪些是结合型 → 这些可能是肿瘤特异性克隆。

### 场景 2：TCR-T 治疗的特异性评估

改造 TCR 前先编码 → 检查它在 latent 空间中与已知自身反应性 TCR 的距离 → 评估脱靶风险。

### 场景 3：疫苗免疫监测

接种新抗原疫苗后，编码患者 TCR 库的时序样本 → 追踪疫苗诱导的 TCR 克隆扩增。

---

## 复现

```python
# 环境：CPU 即可
# 依赖：DeepTCR 2.1.29（pip install DeepTCR）、scikit-learn

# 1. 加载 VAE checkpoint，对 TCR 序列编码
# 2. 用 VDJdb 标签训练 KNN
# 3. 对新 TCR 序列预测结合型概率
```

完整方法参考 DeepTCR 论文（DOI: 10.1038/s41467-021-21879-w）和 VDJdb（DOI: 10.1093/nar/gkx760）。

---

## 团队

DiVo Gen²AI 干计算研发团队。专注前沿计算生物学与核酸药物研发。

---

## 致谢

- **DeepTCR**（Sidhom JW et al., *Nature Communications* 2021, 12:1605）提供了 VAE 框架
- **VDJdb**（Shugay M et al., *Nucleic Acids Research* 2017）提供了训练数据
