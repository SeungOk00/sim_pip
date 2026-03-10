# Protein Binder Design Pipeline

자동화된 단백질 바인더 설계 파이프라인입니다.

## 개요

이 파이프라인은 5단계로 구성된 자동화 시스템으로, 타겟 단백질에 대한 바인더를 설계하고 검증합니다:

1. **Phase 1**: 타겟 발견 (사용자 승인 필요)
2. **Phase 2**: 생성 설계 (RFdiffusion + ProteinMPNN)
3. **Phase 3**: 스크리닝 및 검증 (Chai-1, ColabFold)
4. **Phase 4**: 다목적 최적화 (NSGA-II)
5. **Phase 5**: 실험실 자동화 (SOP 생성)

## 설치

### 1. Python 환경 설정

```bash
# Python 3.8 이상 필요
pip install -r requirements.txt
```

### 2. 필요한 도구들

이 파이프라인은 다음 도구들이 이미 설치되어 있다고 가정합니다:

- RFdiffusion (`/home01/hpc194a02/test/sim_pip/RFdiffusion`)
- ProteinMPNN (`/home01/hpc194a02/test/sim_pip/ProteinMPNN`)
- Chai-1 (`/home01/hpc194a02/test/sim_pip/chai-lab`)
- ColabFold (`/home01/hpc194a02/test/sim_pip/ColabFold`)
- CAPRI-Q (`/home01/hpc194a02/test/sim_pip/capri-q`)

## 사용법

### 기본 사용 (대화형 모드)

```bash
python main.py --target-pdb target.pdb --interactive
```

대화형 모드에서는 파이프라인이 다음 정보를 요청합니다:
- 타겟 체인 ID
- 핫스팟 잔기 번호
- 추가 노트

### 비대화형 모드

```bash
python main.py \
  --target-pdb target.pdb \
  --chain-id A \
  --hotspots "23,45,67,89" \
  --notes "My target protein"
```

### 설정 파일 사용

```bash
python main.py --target-pdb target.pdb --interactive --config configs/my_config.yaml
```

### Dry Run (명령어만 확인)

```bash
python main.py --target-pdb target.pdb --chain-id A --hotspots "23,45,67" --dry-run
```

### 중단된 파이프라인 재개

```bash
python main.py --resume data/runs/run_20260310_182325/pipeline_state.json --start-phase 3
```

## 디렉토리 구조

```
sim_pip/
├── README.md              # 프로젝트 설명
├── INSTALLATION.md        # 설치 가이드
├── requirements.txt       # Python 의존성
├── main.py               # 메인 실행 스크립트
│
├── pipeline/              # 파이프라인 핵심 코드
│   ├── models.py         # 데이터 모델
│   ├── config.py         # 설정 관리
│   ├── phases/           # Phase별 구현
│   │   ├── phase1_target.py
│   │   ├── phase2_generate.py
│   │   ├── phase3_screen.py
│   │   ├── phase4_optimize.py
│   │   └── phase5_lab.py
│   └── utils/            # 유틸리티
│       ├── file_ops.py
│       ├── tool_wrapper.py
│       └── validation.py
│
├── configs/              # 설정 파일
│   └── run.yaml
│
├── targets/              # 타겟 정보 (메타데이터)
│   └── Trun2026031/
│       └── hotspot.json
│
├── tools/                # 외부 도구 래퍼 및 소스코드
│   ├── boltz/
│   ├── chai-1/
│   ├── colabfold/
│   ├── dockq/
│   ├── proteinmpnn/
│   └── rfdiffusion/
│
├── data/                 # 데이터 디렉토리 (gitignore)
│   ├── inputs/           # 입력 데이터
│   │   ├── pdb/          # 타겟 PDB 파일
│   │   └── fasta/        # FASTA 파일
│   ├── outputs/          # 각 도구의 출력
│   │   ├── rfdiffusion/
│   │   ├── proteinmpnn/
│   │   ├── chai1/
│   │   ├── colabfold/
│   │   └── phase3_fast/
│   ├── candidates/       # 후보 바인더
│   │   └── C000001/
│   │       ├── metadata.json
│   │       └── seq.fasta
│   └── runs/             # 실행 히스토리 및 로그
│       └── run_20260310_182325/
│           ├── pipeline_state.json
│           ├── pipeline.log
│           └── phase5_lab/
│               ├── final_sequences.fasta
│               ├── SOP.md
│               └── pipeline_summary.md
│
├── logs/                 # 파이프라인 로그 파일 (gitignore)
│   └── *.log
│
├── scripts/              # 유틸리티 스크립트
│   ├── prepare_rfdiffusion_test.sh
│   ├── test_phase1_2.py
│   └── test_phase1_2_3.py
│
└── tests/                # 테스트 코드
    └── test_rfdiffusion/
```

### 주요 변경사항 (v0.2.0)

- **data/**: 모든 입출력 데이터를 통합 관리
  - `inputs/`, `outputs/`, `candidates/`, `runs/`를 `data/` 하위로 이동
- **logs/**: 로그 파일 전용 디렉토리
- **scripts/**: 테스트 및 유틸리티 스크립트 통합
- **tests/**: 테스트 코드 통합
- **.gitignore**: `data/`와 `logs/` 전체를 무시하여 Git 저장소 크기 최소화

## 설정 파일 (`configs/run.yaml`)

주요 설정 옵션:

```yaml
# Phase 2: 생성
phase2:
  rfdiffusion:
    num_designs: 10        # 생성할 디자인 수
    de_novo_T: 50         # De novo 생성 온도
    refinement_T: 15      # 리파인먼트 온도
  proteinmpnn:
    num_seq_per_target: 10 # 백본당 서열 수
    sampling_temps: [0.1, 0.2, 0.3]

# Phase 3: 스크리닝
phase3_fast:
  gates:
    fail_threshold: 0.23   # DockQ < 0.23 → FAIL
    pass_threshold: 0.49   # DockQ >= 0.49 → PASS

# Phase 4: 최적화
phase4:
  final_selection: 96      # 최종 선택 후보 수
  constraints:
    packstat_min: 0.60
    overall_rmsd_max: 2.0
    rg_max: 16.0
```

## 출력 파일

### Phase 5 최종 산출물

1. **final_sequences.fasta**: 선택된 모든 바인더 서열
2. **structures_list.txt**: 구조 파일 목록
3. **SOP.md**: 실험실 표준 작업 절차서
4. **pipeline_summary.md**: 파이프라인 실행 요약

## 트러블슈팅

### 도구가 실행되지 않을 때

```bash
# 도구 경로 확인
ls -la RFdiffusion/
ls -la ProteinMPNN/
ls -la chai-lab/
ls -la ColabFold/

# 설정 파일에서 경로 수정
vim configs/run.yaml
```

### 로그 확인

```bash
# 가장 최근 실행 로그
ls -lt data/runs/
tail -f data/runs/run_20260310_182325/pipeline.log

# 파이프라인 로그 (phase별)
tail -f logs/phase3_test.log
```

### 중간 상태 확인

```bash
# 파이프라인 상태 확인
cat data/runs/run_20260310_182325/pipeline_state.json

# 후보 확인
ls data/candidates/
cat data/candidates/C000001/metadata.json
```

## 예제

### 예제 1: 간단한 실행

```bash
python main.py \
  --target-pdb examples/target.pdb \
  --chain-id A \
  --hotspots "23,45,67,89,102" \
  --notes "SARS-CoV-2 RBD binder"
```

### 예제 2: 테스트 실행 (적은 후보)

```bash
# 설정을 임시로 변경
python main.py \
  --target-pdb target.pdb \
  --interactive \
  --config configs/test_config.yaml
```

`configs/test_config.yaml`:
```yaml
phase2:
  rfdiffusion:
    num_designs: 3
  proteinmpnn:
    num_seq_per_target: 3
  max_candidates_per_target: 10

phase4:
  final_selection: 5
```

## 고급 사용

### 특정 Phase만 실행

```bash
# Phase 4부터 시작
python main.py --resume data/runs/run_20260310_182325/pipeline_state.json --start-phase 4
```

### 병렬 실행 설정

```yaml
execution:
  parallel_jobs: 8  # 동시 실행 작업 수
```

## 참고 문서

- [설계 전략 문서](binder_pipeline_llm_blueprint.md)
- 각 도구별 문서:
  - RFdiffusion: `RFdiffusion/README.md`
  - ProteinMPNN: `ProteinMPNN/README.md`
  - Chai-1: `chai-lab/README.md`

## 라이선스

이 파이프라인은 연구 목적으로 제공됩니다.

## 버전

- **v0.2.0** (2026-03-10): 폴더 구조 재구성
  - `data/` 디렉토리로 입출력 데이터 통합
  - `logs/`, `scripts/`, `tests/` 디렉토리 추가
  - .gitignore 업데이트로 Git 저장소 크기 최적화
- **v0.1.0** (2026-03-03): 초기 릴리스
