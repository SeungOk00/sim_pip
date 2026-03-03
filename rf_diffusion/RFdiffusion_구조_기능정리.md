# RFdiffusion 폴더 구조/기능 정리

기준 경로: `C:\project\sim_pip\RFdiffusion`

## 1) 루트(최상위) 폴더 개요

- `.git/`: Git 메타데이터(버전 이력, 브랜치, 객체 저장소)
- `.github/`: GitHub 협업/CI 설정
- `.rosetta-ci/`: Rosetta CI 벤치마크/테스트 실행 파이프라인
- `config/`: Hydra 기반 추론 설정 파일
- `docker/`: 컨테이너 빌드 설정
- `env/`: Conda 및 SE3Transformer 의존성/소스
- `examples/`: 태스크별 실행 예시 스크립트와 입력 데이터
- `helper_scripts/`: 보조 전처리 스크립트/샘플 구조
- `img/`: README 문서용 이미지
- `rfdiffusion/`: 핵심 Python 패키지(모델/디퓨전/유틸)
- `scripts/`: 사용자 실행 스크립트
- `tests/`: 통합 테스트

## 2) 루트 파일 기능

- `.gitignore`: Git 추적 제외 규칙
- `LICENSE`: 라이선스(저작권/사용 조건)
- `README.md`: 설치, 모델 다운로드, 실행법, 주요 옵션, 출력 설명 문서
- `setup.py`: `rfdiffusion` 패키지 설치 정의(엔트리 스크립트/의존성 포함)

## 3) 하위 폴더 상세

### .github/

- `CODEOWNERS`: 코드 소유자 지정(리뷰 라우팅)
- `workflows/main.yml`: GitHub Actions CI
  - Python/의존성 설치
  - 모델 weight 다운로드
  - 예제 기반 테스트(`tests/test_diffusion.py`) 분할 실행

### .rosetta-ci/

역할: Rosetta 쪽 CI/벤치마크 자동화 설정.

- `.gitignore`: CI 산출물 제외 규칙
- `benchmark.py`: 벤치마크 실행 엔트리
- `benchmark.template.ini`: 벤치마크 설정 템플릿
- `test-sets.yaml`: 테스트 세트 정의
- `hpc_drivers/`
  - `base.py`: HPC 실행 드라이버 공통 베이스
  - `multicore.py`: 멀티코어 실행 드라이버
  - `slurm.py`: SLURM 스케줄러 드라이버
  - `__init__.py`: 패키지 초기화
- `tests/`
  - `rfd.py`: RFdiffusion 관련 CI 테스트 로직
  - `self.py`: self test 로직
  - `self.md`: self test 설명 문서
  - `__init__.py`: 테스트 유틸/공통 로직

### config/

역할: Hydra 추론 설정.

- `inference/base.yaml`: 기본 추론 설정
  - `inference`(입출력/샘플 수/체크포인트 등)
  - `contigmap`(컨티그/마스킹)
  - `model`(아키텍처 하이퍼파라미터)
  - `diffuser`, `denoiser`, `potentials`, `scaffoldguided` 등
- `inference/symmetry.yaml`: 대칭체 생성용 설정 프리셋(`cN`, `dN`, tetra/octa/icosa)

### docker/

- `Dockerfile`: RFdiffusion 실행용 도커 이미지 빌드 정의

### env/

역할: 실행 환경 및 SE3Transformer 소스 포함.

- `SE3nv.yml`: Conda 환경 정의(CUDA/PyTorch 관련)
- `SE3Transformer/`: NVIDIA SE(3)-Transformer 코드(벤더 포함)
  - 루트 파일
    - `.dockerignore`, `.gitignore`: 제외 규칙
    - `Dockerfile`: SE3Transformer 전용 이미지
    - `LICENSE`, `NOTICE`: 라이선스/고지
    - `README.md`: 모델 설명 및 사용법
    - `requirements.txt`: 의존성 목록
    - `setup.py`: 패키지 설치 정의
  - `images/se3-transformer.png`: 문서용 이미지
  - `scripts/`
    - `train.sh`, `train_multi_gpu.sh`: 학습 실행
    - `predict.sh`: 추론 실행
    - `benchmark_train*.sh`, `benchmark_inference.sh`: 벤치마크 실행
  - `se3_transformer/`
    - `data_loading/data_module.py`: 데이터 모듈
    - `data_loading/qm9.py`: QM9 데이터셋 로딩
    - `model/transformer.py`: SE3 Transformer 본체
    - `model/basis.py`: 기저함수 계산
    - `model/fiber.py`: Fiber 표현 정의
    - `model/layers/attention.py`: 어텐션 레이어
    - `model/layers/convolution.py`: equivariant convolution
    - `model/layers/linear.py`: 선형 레이어
    - `model/layers/norm.py`: 정규화 레이어
    - `model/layers/pooling.py`: 풀링 레이어
    - `runtime/arguments.py`: CLI 인자 파싱
    - `runtime/training.py`: 학습 루프
    - `runtime/inference.py`: 추론 루프
    - `runtime/callbacks.py`: 콜백
    - `runtime/loggers.py`: 로깅
    - `runtime/metrics.py`: 지표 계산
    - `runtime/gpu_affinity.py`: GPU affinity 설정
    - `runtime/utils.py`: 공통 유틸
    - 각 `__init__.py`: 패키지 초기화
  - `tests/test_equivariance.py`: 등변성 테스트
  - `tests/utils.py`, `tests/__init__.py`: 테스트 유틸

### examples/

역할: 태스크별 실행 예제와 입력 데이터.

- 예제 스크립트(`design_*.sh`): `scripts/run_inference.py` 호출 예시
  - `design_unconditional.sh`: 무조건 단량체 생성
  - `design_motifscaffolding*.sh`: motif scaffolding 계열
  - `design_partialdiffusion*.sh`: partial diffusion 계열
  - `design_ppi*.sh`: binder/PPI 계열
  - `design_*oligos.sh`: 대칭 올리고머 생성
  - `design_timbarrel.sh`, `design_enzyme.sh`, `design_nickel.sh` 등: 특정 사례
  - `design_unconditional_w_contact_potential.sh`, `design_unconditional_w_monomer_ROG.sh`: 보조 potential 사용 예
- `ppi_scaffolds_subset.tar.gz`: PPI scaffolded design 예제용 데이터 묶음
- `input_pdbs/*.pdb`: 예제 입력 구조 파일
- `target_folds/*.pt`: fold conditioning용 타깃 특징 텐서(SS/adj)
- `tim_barrel_scaffold/*.pt`: TIM barrel scaffold 특징 텐서

### helper_scripts/

- `make_secstruc_adj.py`: PDB에서 2차구조/인접행렬 특징 생성 보조 스크립트
- `2KL8.pdb`: 스크립트 예제 입력 PDB

### img/

README 설명용 이미지 모음.

- `main.png`, `uncond.png`, `motif.png`, `binder.png`, `fold_cond.png`, `sym_motif.png`, `partial.png`, `olig.png`, `olig2.png`, `rfpeptides_*.png`, `diffusion_protein_gradient_2.jpg`, `cropped_uncond.png`

### rfdiffusion/

역할: RFdiffusion 핵심 구현.

- `RoseTTAFoldModel.py`: RFdiffusion 본체 네트워크 조립/정의
- `Embeddings.py`: 입력 임베딩(MSA/템플릿/위치 정보)
- `Track_module.py`: 3-track 업데이트 블록(MSA/Pair/Structure)
- `Attention_module.py`: 어텐션/FFN 모듈
- `SE3_network.py`: SE(3) equivariant 네트워크 래퍼
- `diffusion.py`: forward/reverse diffusion 스케줄/샘플링 로직
- `igso3.py`: SO(3) 관련 디퓨전 수학 유틸
- `contigs.py`: contig 문자열 파싱 및 인덱스 매핑
- `kinematics.py`: 기하/각도/좌표 변환 유틸
- `coords6d.py`: 좌표를 6D 특성으로 변환
- `chemical.py`: 아미노산/원자 상수 및 매핑 테이블
- `scoring.py`: 원자/에너지 관련 스코어링 상수/로직
- `util.py`: PDB 출력, 기하 계산 등 공통 유틸
- `util_module.py`: 모델 유틸(초기화, 그래프/좌표 보조)
- `AuxiliaryPredictor.py`: 보조 예측 헤드(distance/token/LDDT 등)
- `model_input_logger.py`: 함수 입력 피클 로깅 디버그 도구
- `__init__.py`: 패키지 초기화

하위:

- `inference/`
  - `model_runners.py`: Sampler 초기화/모델 로딩/추론 실행 클래스
  - `utils.py`: 추론 보조 함수(프레임 업데이트, PDB 파싱 등)
  - `symmetry.py`: 대칭 어셈블리 보조 로직
  - `sym_rots.npz`: 대칭 회전행렬 사전 계산 데이터
  - `__init__.py`: 패키지 초기화
- `potentials/`
  - `potentials.py`: 가이드 potential 클래스 정의(예: ROG/contact 등)
  - `manager.py`: potential 파싱/관리 및 contact matrix 처리
  - `__init__.py`: 패키지 초기화

### scripts/

- `run_inference.py`: 메인 추론 엔트리(Hydra 설정 기반, 샘플 루프, PDB/TRB 출력)
- `download_models.sh`: 모델 weight 다운로드 스크립트

### tests/

- `test_diffusion.py`: examples 스크립트를 변형 실행해 재현성/정상동작 검증하는 통합 테스트

## 4) 실행 관점에서 핵심 파일(빠른 참조)

- 시작점: `scripts/run_inference.py`
- 기본 설정: `config/inference/base.yaml`
- 핵심 모델: `rfdiffusion/RoseTTAFoldModel.py`
- 샘플러/추론 제어: `rfdiffusion/inference/model_runners.py`
- 디퓨전 핵심: `rfdiffusion/diffusion.py`, `rfdiffusion/igso3.py`
- 예제 명령: `examples/design_*.sh`
- 검증: `tests/test_diffusion.py`
