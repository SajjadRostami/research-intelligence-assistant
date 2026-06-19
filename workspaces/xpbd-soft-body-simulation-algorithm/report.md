# Research Intelligence Report: XPBD soft body simulation algorithm

**Generated:** 2026-06-19 16:25:24 UTC

---

## Executive Summary

This report presents a comprehensive analysis of **XPBD soft body simulation algorithm** based on 5 top-ranked patents. The analysis evaluates sources across 10 benchmark metrics to identify leading implementations, methodologies, and performance characteristics.

**Key Finding:** The highest-ranked patent "Methods for realistic and efficient simulation of moving objects" (relevance score: 0.85) demonstrates strong alignment with XPBD soft body simulation algorithm.

---

## Top Patents

The following 5 patents represent the most relevant prior art and implementations related to this research topic.

### 1. Methods for realistic and efficient simulation of moving objects

**Patent Number:** patent/US20220151701A1/en  
**Assignee:** Virtamed Ag  
**Publication Date:** 2022-05-19  
**Relevance Score:** 0.85/1.00  
**Confidence:** High  
**URL:** [https://patentimages.storage.googleapis.com/63/7a/da/1af33c7327cfd9/US20220151701A1.pdf](https://patentimages.storage.googleapis.com/63/7a/da/1af33c7327cfd9/US20220151701A1.pdf)

**Relevance Analysis:**

Highly relevant to XPBD soft body simulation. The source directly addresses Projective Dynamics (which is the foundation of XPBD - eXtended Position Based Dynamics), implements constraint-based simulation with local-global solving, and applies it to deformable object simulation. The specific application to rod bending/twisting with Cosserat constraints demonstrates advanced constraint formulations used in modern XPBD implementations. The only minor limitation is the focus on a specific application (surgical simulation) rather than general XPBD methodology, but the core algorithmic content is directly relevant.

### 2. A real-time snow simulation method based on position dynamics with integrated …

**Patent Number:** patent/CN118410742A/en  
**Assignee:** 北京航空航天大学  
**Publication Date:** 2024-07-30  
**Relevance Score:** 0.75/1.00  
**Confidence:** High  
**URL:** [https://patentimages.storage.googleapis.com/e8/53/f3/ec051934c10d97/CN118410742A.pdf](https://patentimages.storage.googleapis.com/e8/53/f3/ec051934c10d97/CN118410742A.pdf)

**Relevance Analysis:**

This patent is highly relevant to XPBD soft body simulation. It explicitly mentions 'position dynamics' which is the core principle of XPBD (Extended Position Based Dynamics). The patent addresses real-time simulation with constraint-based physics, which directly aligns with XPBD methodology. While the specific application is snow simulation rather than general soft body dynamics, the underlying algorithm and approach are fundamentally related to XPBD techniques. The focus on efficiency and constraint-based dynamics makes this a strong match, though it's application-specific rather than a general XPBD framework paper.

### 3. Simulator, simulation data generation method, and simulator system

**Patent Number:** patent/WO2023171413A1/en  
**Assignee:** ソニーグループ株式会社  
**Publication Date:** 2023-09-14  
**Relevance Score:** 0.70/1.00  
**Confidence:** High  
**URL:** [https://patentimages.storage.googleapis.com/b1/34/62/a0e4f62fae755b/WO2023171413A1.pdf](https://patentimages.storage.googleapis.com/b1/34/62/a0e4f62fae755b/WO2023171413A1.pdf)

**Relevance Analysis:**

The patent describes a soft body simulator that uses particle-based mesh modeling with constraint minimization, which aligns with XPBD (Extended Position Based Dynamics) principles. However, the abstract is incomplete and doesn't explicitly mention XPBD, position-based dynamics, or constraint-based methods by name. The core concepts of particle systems and constraint optimization are relevant to XPBD, but without confirmation of the specific algorithm used, the relevance is moderately high rather than definitive.

### 4. Methods of contact for simulation

**Patent Number:** patent/US20250131161A1/en  
**Assignee:** Nvidia Corporation  
**Publication Date:** 2025-04-24  
**Relevance Score:** 0.65/1.00  
**Confidence:** High  
**URL:** [https://patentimages.storage.googleapis.com/96/a0/50/5537df63fc0edf/US20250131161A1.pdf](https://patentimages.storage.googleapis.com/96/a0/50/5537df63fc0edf/US20250131161A1.pdf)

**Relevance Analysis:**

This patent addresses contact simulation and constraint solving for rigid body dynamics, which are related to soft body simulation. However, it focuses on force-based (primal) formulations for rigid bodies rather than XPBD (Extended Position Based Dynamics), which is a constraint-based (dual) approach specifically designed for soft bodies. The source is moderately relevant as contact handling and constraint solving are components of XPBD, but it does not directly address the XPBD algorithm itself or soft body-specific techniques.

### 5. A GPU parallel fitting simulation method based on constraint projection

**Patent Number:** patent/CN112862957A/en  
**Assignee:** 南京大学  
**Publication Date:** 2021-05-28  
**Relevance Score:** 0.65/1.00  
**Confidence:** High  
**URL:** [https://patentimages.storage.googleapis.com/01/7a/ee/93c9518595150d/CN112862957A.pdf](https://patentimages.storage.googleapis.com/01/7a/ee/93c9518595150d/CN112862957A.pdf)

**Relevance Analysis:**

The source is moderately relevant to XPBD soft body simulation. It addresses constraint-based simulation (constraint projection) and GPU parallel computing, which are core components of XPBD algorithms. However, the focus appears to be specifically on clothing/garment fitting simulation with BVH collision detection rather than general XPBD methodology. The constraint projection approach is related to XPBD's core technique, but the source seems narrowly scoped to a specific application domain rather than comprehensively covering the XPBD algorithm itself.

---

## Top Papers

*No scientific papers were ranked for this topic.*

---

## Benchmark Metrics

This analysis evaluates sources against 10 benchmark metrics across multiple categories:

### Accuracy Metrics

**Constraint Formulation Alignment Score**

Measures how closely the source implements constraint-based formulations core to XPBD, specifically evaluating support for position-based constraints, Lagrange multipliers, and constraint projection methods on a scale of 0-100. Higher scores indicate direct implementation of XPBD constraint solving mechanisms.

**Simulation Stability Metric**

Measures the robustness of constraint solving under extreme conditions (high velocities, large timesteps, complex collisions) using a normalized energy conservation score (0-100). Values above 85 indicate stable convergence without numerical artifacts or constraint violations.

**Collision Detection Integration Score**

Evaluates the comprehensiveness of contact and collision handling mechanisms on a scale of 0-100, including support for self-collisions, continuous collision detection, and contact constraint formulation. Essential for realistic soft body interaction.

**XPBD Algorithm Specificity Index**

Quantifies how explicitly the source addresses Extended Position Based Dynamics principles (0-100 scale), including: position-based constraint formulation, extended constraint types, damping mechanisms, and temporal coherence. Measures direct relevance to XPBD methodology.

### Efficiency Metrics

**Constraint Solver Iteration Efficiency**

Measures the average number of constraint projection iterations required to achieve convergence (typically 1-10 iterations for XPBD) and the convergence rate per iteration. Lower iteration counts with faster convergence indicate more efficient solver implementation.

**Memory Efficiency Ratio**

Measures memory consumption per simulated particle in kilobytes, accounting for constraint data, particle state, and solver structures. Lower ratios enable larger simulations on fixed hardware; benchmark target is <2KB per particle.

### Hardware Metrics

**GPU Parallelization Support Level**

Assesses the degree of GPU acceleration implementation on a 5-point scale: 0=no GPU support, 1=partial CPU-GPU hybrid, 2=GPU-optimized kernels, 3=full GPU pipeline, 4=advanced parallel algorithms. Directly relevant to XPBD scalability on modern hardware.

### Performance Metrics

**Real-time Performance Capability Index**

Quantifies the source's demonstrated ability to achieve interactive frame rates (≥30 FPS) for soft body simulations, measured as percentage of test cases meeting real-time requirements. Evaluates whether the implementation can handle practical interactive applications.

### Scalability Metrics

**Scalability Factor for Particle Count**

Quantifies computational complexity scaling as particle count increases, measured as the ratio of frame time increase per 10,000 particles added. Lower ratios (closer to linear O(n)) indicate better scalability for large-scale simulations.

### Usability Metrics

**Implementation Maturity Level**

Assesses the completeness of the XPBD implementation on a 5-point scale: 1=theoretical/proof-of-concept, 2=basic algorithm, 3=production-ready with optimization, 4=mature with multiple features, 5=industry-standard with extensive validation. Indicates practical usability.

---

## References

### Patents

1. Methods for realistic and efficient simulation of moving objects. Virtamed Ag. patent/US20220151701A1/en. Published 2022-05-19. Available at: https://patentimages.storage.googleapis.com/63/7a/da/1af33c7327cfd9/US20220151701A1.pdf

2. A real-time snow simulation method based on position dynamics with integrated …. 北京航空航天大学. patent/CN118410742A/en. Published 2024-07-30. Available at: https://patentimages.storage.googleapis.com/e8/53/f3/ec051934c10d97/CN118410742A.pdf

3. Simulator, simulation data generation method, and simulator system. ソニーグループ株式会社. patent/WO2023171413A1/en. Published 2023-09-14. Available at: https://patentimages.storage.googleapis.com/b1/34/62/a0e4f62fae755b/WO2023171413A1.pdf

4. Methods of contact for simulation. Nvidia Corporation. patent/US20250131161A1/en. Published 2025-04-24. Available at: https://patentimages.storage.googleapis.com/96/a0/50/5537df63fc0edf/US20250131161A1.pdf

5. A GPU parallel fitting simulation method based on constraint projection. 南京大学. patent/CN112862957A/en. Published 2021-05-28. Available at: https://patentimages.storage.googleapis.com/01/7a/ee/93c9518595150d/CN112862957A.pdf

