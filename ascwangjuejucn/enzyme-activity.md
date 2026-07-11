---
title: 酶活性评估 Agent
slug: enzyme-activity
icon: Zap
color: "#00ff96"
status: dev
category: 酶工程
demoUrl: ""
githubUrl: https://github.com/sealionking/wangjuejudotcngen2ai
date: 2026-07-11
tags: [酶活性, DLKcat, FoldX, 突变评估]
order: 2
en:
  title: Enzyme Activity Assessment Agent
  excerpt: Input protein sequence and mutation sites, Agent calls DLKcat + FoldX + triple-model cross-validation, outputs enzyme activity change prediction and stability assessment.
ja:
  title: 酵素活性評価 Agent
  excerpt: タンパク質配列と変異部位を入力、Agent が DLKcat + FoldX + 3モデル交叉検証を呼び出し、酵素活性変化予測と安定性評価を出力。
fr:
  title: Agent d'Évaluation d'Activité Enzymatique
  excerpt: Entrez séquence protéique et sites de mutation, l'Agent appelle DLKcat + FoldX + validation croisée triple-modèle, produit prédiction de changement d'activité enzymatique et évaluation de stabilité.
kr:
  title: 효소 활성 평가 Agent
  excerpt: 단백질 서열과 변이 부위 입력, Agent가 DLKcat + FoldX + 3모델 교차 검증 호출, 효소 활성 변화 예측과 안정성 평가 출력.
---

# 酶活性评估 Agent

输入蛋白质序列与突变位点，Agent 调用 DLKcat + FoldX + 三模型交叉验证，输出酶活性变化预测与稳定性评估。

## 功能特性

- **kcat/KM 预测**：DLKcat 深度学习模型预测催化效率
- **稳定性评估**：FoldX 计算 ΔΔG 判断突变稳定性影响
- **三模型交叉验证**：DLKcat + FoldX + 知识图谱三重交叉
- **突变位点扫描**：支持单点、多点、饱和突变扫描

## 使用方式

1. 输入野生型蛋白质序列
2. 指定突变位点（如 K172M, A235T）
3. Agent 自动调用多模型并行计算
4. 输出活性变化比、稳定性 ΔΔG、综合评估报告
