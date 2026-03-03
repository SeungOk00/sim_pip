# 단백질 바인더 설계 자동화 파이프라인 – LLM 친화 설계 전략(정리본)

## 0) 전체 파이프라인 정의

### 파이프라인 타입
- 상태기반(State Machine) + 큐 기반(Job Queue) 구조 권장
- 각 Phase는 `state`를 읽고 결과를 `state`에 쓰는 “노드(순수 함수형)”로 설계

### 공통 원칙
- **재현성**: config/seed/tool version/입력 파일 hash 저장
- **설명 가능성**: 점수뿐 아니라 `why/evidence`(DockQ 리포트, pAE, RMSD 등) 저장

---

## 1) 공통 데이터 스키마(Contract)

### 핵심 엔티티 3개
1) **TargetSpec**: 타겟 정보(구조/포켓/핫스팟)
2) **DesignCandidate**: 설계 후보(구조+서열+점수)
3) **RunRecord**: 실행 로그/입출력/버전

### (A) TargetSpec (Phase 1 Output)
- `target_id`
- `target_pdb_path`
- `chain_id`
- `pocket_definition`
  - 옵션1: residue list (핫스팟 잔기 번호)
  - 옵션2: 좌표 박스(center xyz + size)
- `hotspot_residues`: [int]  ← **연구자 승인 후 확정본**
- `notes`: 근거/코멘트/링크

### (B) DesignCandidate (모든 Phase 공통)
- `candidate_id`
- `parent_id` (refinement로 생긴 경우)
- `binder_sequence`
- `binder_pdb_path`
- `complex_pdb_path`
- `stage`: `generated / refined / fast_screened / deep_validated / optimized / selected / failed`
- `metrics`: dict
  - fast: `dockq`, `capriq`, `rmsd_pred`, `chai_conf`, `boltz_conf`
  - deep: `rmsd_chai_vs_cf`, `pae_interaction`
  - developability: `interface_ddg`, `sap`, `total_score_per_res`, `packstat`, `rg`, `mhc2_best_ic50`, `mhc2_strong_binders_count`
- `decision`: dict
  - `gate`: `PASS/REFINE/FAIL`
  - `reason`: string

### (C) RunRecord (재현/디버깅)
- `tool_name`, `tool_version`, `command`
- `inputs`, `outputs`
- `start_time`, `end_time`, `exit_code`, `stderr_tail`

---

## 2) 폴더/파일 규칙(LLM 코드 안정성)

### 추천 구조
```
project/
  configs/
    run.yaml
  targets/
    T001/
      target.pdb
      hotspot.json
  runs/
    2026-03-03_001/
      phase2_generate/
      phase3_fast/
      phase3_deep/
      phase4_opt/
  candidates/
    C000001/
      seq.fasta
      complex.pdb
      metrics.json
      lineage.json
```

- `candidates/` 폴더를 **single source of truth**로 유지
- `runs/`는 실행 로그/중간 파일 저장소로만 사용

---

## 3) Phase-by-Phase 설계 전략

## Phase 1: Human-in-the-Loop Target Discovery
### 목적
- RAG 제안 + 연구자 직관 결합 → **핫스팟 잔기 최종 확정**

### 입력
- `target_pdb_path`
- (옵션) RAG가 제안한 hotspot 후보 + 근거

### 출력
- `TargetSpec.hotspot_residues` 확정본
- `hotspot.json` 저장

### 구현 포인트
- 이 Phase는 UI/CLI form step(사람 승인)으로 두고 이후 Phase는 자동화

---

## Phase 2: Evolutionary Generative Design
### 목적
- RFdiffusion 생성/리파인 + (Protein/Ligand)MPNN 서열 생성

### 입력
- `TargetSpec`(핫스팟/포켓 정의)
- Settings
  - RFdiffusion De novo: `diffuser.T = 50`
  - RFdiffusion Refinement: `diffuser.T = 15`
  - ProteinMPNN: `num_seq_per_target=10`, `sampling_temp=[0.1,0.2,0.3]`

### 출력
- N개의 `DesignCandidate(stage="generated")`
- lineage 기록(de novo → refine → mpnn)

### 노드 설계
1) `GenerateBatchNode`: de novo backbone N개 생성
2) `RefineLoopNode`: 각 backbone refinement(반복 횟수 상한)
3) `SequenceDesignNode`: backbone당 MPNN 10개 서열 생성(temp 균등 분배)

### 필수 정책
- 후보 폭발 방지: `max_candidates_per_target` 상한
- 재현 옵션: seed 고정

---

## Phase 3-A: Fast Screening (고속 선별)
### 목적
- 후보를 Fail/Refine/Pass로 빠르게 분류

### 도구
- Chai-1, Boltz-1 (구조 예측)
- DockQ, CAPRI-Q, OpenStructure (평가)

### Gate
- 🔴 Fail: `DockQ < 0.23`
- 🟡 Refine: `0.23 ≤ DockQ < 0.49` → Phase 2 refinement 큐로 환송
- 🟢 Pass: `DockQ ≥ 0.49` → Phase 3-B 진출

### 출력
- `metrics.dockq` 저장
- `decision.gate` 저장

---

## Phase 3-B: Deep Validation (정밀 검증)
### 목적
- ColabFold(AF2-multimer)로 최종 확증

### 입력
- Phase 3-A PASS 후보

### Gate
- Consensus: `RMSD(chai vs colabfold) < 2.0 Å`
- Confidence: `pAE_interaction < 5`

### 출력
- `stage="deep_validated"` 승격 → Phase 4로 전달
- 실패 사유 분류: `FAIL_consensus` vs `FAIL_pae`

### 구현 포인트
- ColabFold는 느리므로 배치 실행 + 캐시 필수

---

## Phase 4: Multi-Objective Optimization (Developability)
### 목적
- 결합력/용해도/안정성을 동시에 고려해 개발가능 후보 선발
- NSGA-II 파레토 최적 + mmseq2 clustering으로 대표 96개

### 전처리
- Rosetta FastRelax(필수)

### Objectives (Minimize)
- Affinity f1: `interface_ddg < -30`
- Solubility f2: `sap < 40`
- Stability f3: `total_score_per_res < -3.0`

### Hard Constraints (모두 만족해야 feasible)
- Packing: `packstat > 0.60`
- Structure: `overall_rmsd < 2.0`
- Hotspot: `epitope_rmsd < 1.0`
- Compactness: `rg < 16`
- Safety: IEDB MHC-II에서 `IC50 < 50 nM` 강결합 에피토프 **개수 0**

### 구현 구조(LLM이 코드로 옮기기 쉬움)
- `evaluate_developability(candidate) -> metrics`
- `is_feasible(metrics) -> bool`
- `nsga2_optimize(feasible_candidates) -> pareto_candidates`
- `cluster_and_select(pareto_candidates, k=96) -> final_candidates`

> 권장: Phase 4에서 새 변이를 만들기 전에 “선별형 NSGA-II(랭킹/선정)”로 먼저 시작

---

## Phase 5: Lab Automation
### 목적
- SOP 자동 생성 + 결과 저장 + 피드백 루프

### 입력
- 최종 후보(96개): 서열/구조/리스트

### 출력
- SOP 문서(LLM 생성)
- Neo4j 결과 저장(스키마 기반)
- 결과 기반 Phase 2/4 피드백(옵션)

### 구현 포인트
- SOP는 템플릿 기반 섹션 고정(클로닝/발현/정제/결합측정/안정성/응집 등)

---

## 4) LLM에게 주는 “코드 작성 지시문” 템플릿

- Phase별 함수/클래스로 분리
- 모든 Phase는 `state(JSON)` 입력 → `state` 업데이트 출력
- canonical 산출물은 `candidates/`에 저장
- 실패 처리
  - tool 실패: `RETRY 2회` 후 `FAIL_TOOL`
  - 점수 실패: gate 규칙대로 fail/refine/pass
- `dry-run` 모드 지원(커맨드만 출력)

---

## 5) 도구별 사용방법 문서화 템플릿(예: Chai-1)

- 목적: complex 구조 예측
- 입력: target pdb, binder fasta(or pdb)
- 출력: predicted complex pdb, confidence metrics
- 실행: CLI 커맨드 예시
- 산출물 저장 규칙: `runs/phase3_fast/...`
- 실패 처리: exit code !=0 → retry/log
