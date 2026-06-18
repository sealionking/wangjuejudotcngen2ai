# DiVo Gen²AI

AI-driven bio-computing models & pipeline — desensitized public release.

## About

DiVo Gen²AI develops AI-driven tools for protein design and mRNA engineering, with a focus on binding affinity prediction, multi-dimensional scoring pipelines, and translation efficiency optimization.

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

## License

Proprietary — All rights reserved by DiVo Gen²AI.
