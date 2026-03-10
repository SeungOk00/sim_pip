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

### 전제 조건

이 파이프라인은 다음 외부 도구들이 **사전 설치**되어 있다고 가정합니다:

- **RFdiffusion**: `/home01/hpc194a02/test/sim_pip/tools/rfdiffusion`
- **ProteinMPNN**: `/home01/hpc194a02/test/sim_pip/tools/proteinmpnn`
- **Chai-1**: `/home01/hpc194a02/test/sim_pip/tools/chai-1`
- **ColabFold**: `/home01/hpc194a02/test/sim_pip/tools/colabfold`
- **Boltz** (선택):
 `/home01/hpc194a02/test/sim_pip/tools/boltz`
- **DockQ**: `/home01/hpc194a02/test/sim_pip/tools/dockq`

### 1. 시스템 요구사항 확인

```bash
# GPU 확인 (권장: CUDA 지원 GPU)
nvidia-smi

# Conda 환경 확인
conda --version

# Python 버전 확인 (3.8 이상)
python --version
```

### 2. RFdiffusion 환경 설정

RFdiffusion은 별도의 Conda 환경 (SE3nv)이 필요합니다:

```bash
# SE3nv 환경 확인
conda env list | grep SE3nv

# SE3nv 환경이 없다면 생성
conda env create -f tools/rfdiffusion/env/SE3nv.yml

# 모델 가중치 다운로드 (처음 한 번만, 수 GB)
cd tools/rfdiffusion
bash scripts/download_models.sh

# 모델 파일 확인
ls -lh models/Complex_base_ckpt.pt
```

**RFdiffusion 설치 검증**:

```bash
# 자동 검증 스크립트 실행
bash scripts/test_rfdiffusion_setup.sh

# 수동 테스트 (선택사항)
conda activate SE3nv
cd tests/test_rfdiffusion
python ../../tools/rfdiffusion/scripts/run_inference.py \
  inference.input_pdb=target.pdb \
  inference.output_prefix=outputs/binder \
  inference.num_designs=1 \
  'contigmap.contigs=[A1-150/0 80-80]' \
  'ppi.hotspot_res=[A982,A990,A995]'
```

### 3. Python 환경 설정 (메인 파이프라인)

```bash
# Python 3.8 이상 필요
cd /home01/hpc194a02/test/sim_pip

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 기본 의존성 설치
pip install -r requirements.txt
```

### 4. Chai-1 설치

```bash
# Chai-1을 editable 모드로 설치
pip install -e ./tools/chai-1

# Chai-1 설치 확인
chai-lab --help
```

### 5. Boltz 설치 (선택사항)

Boltz는 의존성 충돌 방지를 위해 **별도 가상환경** 사용을 권장합니다:

```bash
# Boltz 전용 가상환경 생성
python -m venv .boltz_venv
source .boltz_venv/bin/activate

# Boltz 설치
pip install -e ./tools/boltz

# Boltz 설치 확인
boltz --help

# 원래 환경으로 복귀
deactivate
source .venv/bin/activate
```

설정 파일에서 Boltz venv 경로를 지정하세요:

```python
# pipeline/config.py
"boltz": {
    "enabled": True,
    "venv_path": "/home01/hpc194a02/test/sim_pip/.boltz_venv"
}
```

### 6. 시스템 의존성

#### kalign (Chai-1 템플릿 서버용)

```bash
# Conda를 사용하는 경우 (권장)
conda install -c bioconda kalign

# 또는 소스에서 빌드
wget https://github.com/TimoLassmann/kalign/archive/refs/tags/v3.3.5.tar.gz
tar -xzf v3.3.5.tar.gz
cd kalign-3.3.5
mkdir build && cd build
cmake .. && make && sudo make install

# 설치 확인
kalign --version
```

**참고**: kalign 없이 사용하려면 `--use-templates-server` 플래그를 제거하세요.

#### DockQ (구조 평가용)

```bash
pip install DockQ
# 또는
pip install git+https://github.com/bjornwallner/DockQ.git

# 설치 확인
DockQ --help
```

### 7. 설치 검증

전체 파이프라인 설치를 검증하세요:

```bash
# Phase 1-2-3 통합 테스트
python scripts/test_phase1_2_3.py

# 또는 dry-run 모드로 전체 파이프라인 테스트
python main.py \
  --target-pdb tests/test_rfdiffusion/target.pdb \
  --chain-id A \
  --hotspots "982,990,995" \
  --notes "Installation test run" \
  --dry-run
```

개별 도구 확인:

```bash
# RFdiffusion (SE3nv 환경에서)
conda activate SE3nv
python tools/rfdiffusion/scripts/run_inference.py --help

# ProteinMPNN (메인 환경에서)
source .venv/bin/activate
python tools/proteinmpnn/protein_mpnn_run.py --help

# Chai-1
chai-lab --help

# Boltz (.boltz_venv 환경에서)
source .boltz_venv/bin/activate
boltz --help

# DockQ
DockQ --help

# kalign
kalign --version
```

### 8. 경로 설정

프로젝트 루트 경로를 확인하고 필요시 수정하세요:

```python
# pipeline/config.py
DEFAULT_CONFIG = {
    "project_root": "/home01/hpc194a02/test/sim_pip",  # 실제 경로로 변경
    
    # Phase 2: RFdiffusion 경로
    "phase2": {
        "rfdiffusion": {
            "path": "/home01/hpc194a02/test/sim_pip/tools/rfdiffusion",
            ...
        },
        "proteinmpnn": {
            "path": "/home01/hpc194a02/test/sim_pip/tools/proteinmpnn",
            ...
        }
    },
    
    # Phase 3-B: ColabFold 경로
    "phase3_deep": {
        "colabfold": {
            "path": "/home01/hpc194a02/test/sim_pip/tools/colabfold"
        }
    }
}
```

### 트러블슈팅

#### RFdiffusion 모델 가중치 없음

```bash
cd tools/rfdiffusion
bash scripts/download_models.sh
ls models/  # Complex_base_ckpt.pt 확인
```

#### GPU 메모리 부족

```bash
# RFdiffusion num_designs 줄이기
# pipeline/config.py
"phase2": {
    "rfdiffusion": {
        "num_designs": 1,  # 기본값: 10
        ...
    }
}
```

#### Conda 환경 활성화 오류

```bash
# conda init 실행
conda init bash
source ~/.bashrc

# SE3nv 환경 재생성
conda env remove -n SE3nv
conda env create -f tools/rfdiffusion/env/SE3nv.yml
```

자세한 설치 가이드는 [INSTALLATION.md](INSTALLATION.md)를 참조하세요.

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

## Pipeline 모듈 구조

### 핵심 모듈

#### `pipeline/models.py`
데이터 모델 정의:
- **`TargetSpec`**: Phase 1 타겟 명세 (타겟 ID, PDB 경로, 체인, 핫스팟 등)
- **`DesignCandidate`**: 후보 바인더 정보 (ID, 서열, PDB, 메트릭, 결정사항 등)
- **`PipelineState`**: 전체 파이프라인 상태 (진행 단계, 타겟, 후보 목록, 실행 기록)
- **`RunRecord`**: 각 단계별 실행 기록

#### `pipeline/config.py`
설정 관리:
- **`DEFAULT_CONFIG`**: 기본 설정값 (경로, Phase별 파라미터)
- **`Config`** 클래스: 
  - YAML 설정 파일 로드 및 저장
  - 설정값 조회 및 수정 (`get`, `set`)
  - 계층적 설정 병합

### Phase 구현 (`pipeline/phases/`)

#### `phase1_target.py` - 타겟 발견
- 사용자가 지정한 타겟 PDB, 체인, 핫스팟 검증
- 타겟 ID 생성 및 메타데이터 저장
- 대화형/비대화형 모드 지원

**주요 메서드**:
- `run()`: 타겟 스펙 생성 및 검증
- `interactive_approval()`: 대화형 승인 프로세스

#### `phase2_generate.py` - 생성 설계
- RFdiffusion de novo 백본 생성
- (선택적) RFdiffusion 리파인먼트
- ProteinMPNN 서열 설계

**주요 메서드**:
- `run()`: 전체 생성 파이프라인 실행
- `_generate_denovo_backbones()`: RFdiffusion de novo
- `_refine_backbones()`: RFdiffusion 리파인먼트
- `_design_sequences()`: ProteinMPNN 서열 생성

#### `phase3_screen.py` - 스크리닝 및 검증
**3-A: Fast Screening**
- Chai-1 또는 Boltz를 사용한 빠른 구조 예측
- DockQ 기반 품질 게이트
- PASS/REFINE/FAIL 분류

**3-B: Deep Validation**
- ColabFold를 사용한 정밀 검증
- 백본 RMSD, Interface PAE, pLDDT, ipTM 계산
- 최종 통과/실패 결정

**주요 메서드**:
- `run()`: 전체 스크리닝 파이프라인
- `_fast_screen_candidate()`: 빠른 스크리닝
- `_deep_validate_candidate()`: 정밀 검증

#### `phase4_optimize.py` - 다목적 최적화
- Rosetta FastRelax 전처리
- 개발가능성 메트릭 평가 (interface_ddg, SAP, PackStat 등)
- NSGA-II 파레토 최적화
- 클러스터링 및 최종 선택

**주요 메서드**:
- `run()`: 최적화 파이프라인
- `_evaluate_developability()`: 개발가능성 평가
- `_nsga2_optimize()`: NSGA-II 알고리즘
- `_cluster_and_select()`: 다양성 기반 선택

#### `phase5_lab.py` - 실험실 자동화
- 최종 후보 서열 및 구조 내보내기
- SOP (표준작업절차서) 문서 생성
- 파이프라인 요약 보고서 작성
- (선택적) Neo4j 데이터베이스 저장

**주요 메서드**:
- `run()`: 실험실 준비 파이프라인
- `_export_sequences()`: FASTA 파일 생성
- `_generate_sop()`: SOP 문서 생성
- `_generate_summary()`: 요약 보고서

### 유틸리티 (`pipeline/utils/`)

#### `tool_wrapper.py`
외부 도구 실행 래퍼:
- **`ToolRunner`**: 기본 도구 실행 클래스 (재시도 로직, 타임아웃)
- **`RFdiffusionRunner`**: RFdiffusion 실행
- **`ProteinMPNNRunner`**: ProteinMPNN 실행
- **`ChaiRunner`**: Chai-1 실행
- **`BoltzRunner`**: Boltz 실행 (전용 venv 지원)
- **`ColabFoldRunner`**: ColabFold 실행

각 러너는 명령어 생성, 실행, 결과 파싱 로직 포함

#### `file_ops.py`
파일 작업 유틸리티:
- `ensure_dir()`: 디렉토리 생성
- `copy_file()`: 파일 복사
- `compute_file_hash()`: 파일 해시 계산
- `get_next_candidate_id()`: 후보 ID 생성
- `get_run_id()`: 실행 ID 생성 (timestamp 기반)

#### `validation.py`
입력 검증:
- `validate_pdb_file()`: PDB 파일 형식 검증
- `validate_fasta_file()`: FASTA 파일 형식 검증
- `validate_hotspot_residues()`: 핫스팟 잔기 검증
- `validate_config()`: 설정 파일 검증

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
