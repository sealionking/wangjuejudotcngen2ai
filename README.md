# DiVo Gen²AI

AI-driven bio-computing models, pipelines & agent infrastructure — desensitized public release.

## About

DiVo Gen²AI develops AI-driven tools for protein design, mRNA engineering, and agent infrastructure, with a focus on binding affinity prediction, multi-dimensional scoring pipelines, translation efficiency optimization, and strategic memory systems.

## Abstract

DiVo Gen²AI is an AI-driven bio-computing platform that spans the full pipeline from **structure prediction → affinity scoring → sequence optimization → model deployment**. This repository documents our core technical innovations:

- **PPI Head**: A dedicated binding affinity prediction head that extracts Kd signals from structure prediction intermediates — filling the gap where pLDDT/pDockQ only measure confidence, not actual binding strength.
- **RNALens**: Three-round progressive fine-tuning of RNA language models for mRNA translation efficiency prediction, achieving Spearman = 0.92 on MRL across HEK/Muscle/PC3 cell lines.
- **Enzyme Mutation Algorithm**: Four-generation evolution (v1→v4) of anti-hydrolysis scoring, discovering that single-chain kcat negatively correlates with tetramer stability (ρ = -0.604), shifting the paradigm from "catalysis-first" to "anti-hydrolysis-first".
- **DiVo-Anamnesis**: 5D strategic memory engine (semantic + temporal + relational + strategic + knowledge) with OpenSearch knowledge federation for AI agent hybrid retrieval.
- **Bio-Distillation**: Multi-teacher knowledge distillation pipeline (GLM-5.2 + GLM-5.1 + DeepSeek-V4-Pro → ~60B MoE student) with bioinformatics-specific GRPO tool-calling rewards. End-to-end verified on consumer-grade GPU — from teacher inference through LoRA fine-tuning to evaluation, the full pipeline runs on accessible hardware.

All innovations are validated with real experimental data and reproducible pipelines.

## Key Innovations

### PPI Head — Protein-Protein Interaction Affinity Prediction

A dedicated affinity prediction head that extracts binding affinity signals from structure prediction intermediate representations. Unlike structure confidence metrics (pLDDT, pDockQ), PPI Head directly predicts binding strength (Kd), providing the missing "judgment" capability that structure prediction models lack.

- Distance binning encoding + Pairformer layers
- Multi-task output: Kd regression, affinity score, binary classification
- Integrated into a unified scoring pipeline with physical docking validation

### RNALens Fine-tuning — mRNA Translation Efficiency Prediction

Multi-round deep fine-tuning of RNA language models for mRNA translation efficiency prediction, achieving **Spearman = 0.92** on ribosome loading (MRL) prediction and adapting to HEK, Muscle, PC3 cell lines.

- Three-round progressive training: MRL pretraining → BioFeatures enhancement → Tissue-specific adaptation
- Dual-channel architecture: sequence embedding + 26-dim biological features
- Tissue-specific models for precision medicine applications

### Enzyme Mutation Algorithm — Anti-Hydrolysis Scoring with 3D Structural Constraints

A four-generation evolution (v1→v4) of mutation scoring algorithms for enzyme activity enhancement. Key discovery: **single-chain kcat negatively correlates with tetramer configuration stability (ρ = -0.604)**, leading to a paradigm shift from "catalysis-first" to "anti-hydrolysis-first".

- v4 algorithm: 3D Gaussian distance penalty + inter-subunit charge repulsion + industrial post-processing correction
- Validated on 102 tetramer samples with 100% configuration PASS rate (conservative threshold)
- Reduced structure prediction candidates by 72% (130→36)

### DiVo-Anamnesis — 5D Strategic Memory Engine for AI Agents

A 5-dimensional memory engine extending open-source Anamnesis with an OpenSearch knowledge federation layer. Enables AI agents to perform hybrid retrieval across local episodic memories and external knowledge bases through unified RRF scoring.

- 5D recall: semantic + temporal + relational + strategic + knowledge
- Hybrid BM25+neural search via OpenSearch with automatic fallback
- IDE session bridge: decrypt and index encrypted agent conversation databases
- Hook architecture for extensible lifecycle customization

### Bio-Distillation — Multi-Teacher Knowledge Distillation for Bioinformatics

A complete distillation pipeline that compresses multi-teacher knowledge (GLM-5.2 + GLM-5.1 + DeepSeek-V4-Pro) into a deployable ~60B MoE student model, with bioinformatics-specific SFT data construction and GRPO tool-calling reward functions. Verified end-to-end on a consumer-grade GPU.

- Black-box + white-box distillation: Forward KL from teacher logits + SFT from teacher outputs
- GRPO reward: 4-dimensional weighted scoring (tool correctness 0.4 + param accuracy 0.3 + pipeline validity 0.2 + efficiency 0.1)
- 16-question must-pass evaluation + tool-calling accuracy assessment
- Based on EasyDistill (ModelScope), supports QLoRA 4bit for consumer GPUs

### Multi-Dimensional Scoring Pipeline

| Dimension | Metric | What it measures |
|-----------|--------|-----------------|
| Structure confidence | pLDDT, pDockQ | Prediction reliability |
| Interface quality | ipTM | Interface prediction confidence |
| Binding affinity | PPI Head score | Actual binding strength |
| Physical validation | Docking score / Redocking RMSD | Physical plausibility |

The docking validation dimension can identify "confident but wrong" designs — where structure prediction scores are high but physical docking reveals incorrect binding modes.

## Documentation

- [PPI Head Innovation](docs/divo-ppi-head-innovation.md) — Technical deep-dive into our PPI affinity prediction model
- [RNALens Fine-tuning](docs/rnalens-finetuning-innovation.md) — mRNA translation efficiency prediction via progressive fine-tuning
- [Asparaginase Mutation Algorithm](docs/asparaginase-mutation-algorithm.md) — Anti-hydrolysis mutation scoring algorithm v1→v4 evolution
- [DiVo-Anamnesis 5D Memory](docs/divo-anamnesis-5d-memory.md) — 5D strategic memory engine with knowledge federation
- [Bio-Distillation Demo](docs/bio-distillation-demo.md) — Multi-teacher knowledge distillation for bioinformatics, verified on consumer-grade GPU

## License

Proprietary — All rights reserved by DiVo Gen²AI.
