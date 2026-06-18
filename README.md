# DiVo Gen²AI

Protein design models & pipeline — desensitized public release.

## About

DiVo Gen²AI develops AI-driven protein design tools with a focus on protein-protein interaction (PPI) affinity prediction and multi-dimensional scoring pipelines.

## Key Innovations

### PPI Head

A dedicated affinity prediction head that extracts binding affinity signals from structure prediction intermediate representations. Unlike structure confidence metrics (pLDDT, pDockQ), PPI Head directly predicts binding strength (Kd), providing the missing "judgment" capability that structure prediction models lack.

- Distance binning encoding + Pairformer layers
- Multi-task output: Kd regression, affinity score, binary classification
- Integrated into a unified scoring pipeline with physical docking validation

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

## License

Proprietary — All rights reserved by DiVo Gen²AI.
