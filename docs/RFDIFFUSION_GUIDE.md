# RFdiffusion 바인더 설계 가이드

## 📖 개요

RFdiffusion은 단백질 바인더를 생성하는 핵심 도구입니다. 이 문서는 파이프라인에서 RFdiffusion을 사용하는 방법을 설명합니다.

## 🎯 바인더 설계 워크플로우

### 1. 타겟 단백질 준비

#### 타겟 선택 기준
- **좋은 결합 사이트**: 3개 이상의 소수성 잔기 포함
- **피해야 할 사이트**: 
  - 완전히 극성/하전된 표면
  - 글리칸이 가까이 있는 부위
  - 비구조화된 루프 (가능하면)

#### 타겟 자르기 (Truncation)
RFdiffusion은 O(N²) 복잡도를 가지므로 타겟을 자르는 것이 중요합니다:

```python
# 권장 전략:
# 1. 결합 사이트 주변 ~10Å 영역 유지
# 2. 도메인 경계나 유연한 링커에서 자르기
# 3. 2차 구조 보존
# 4. 가능한 한 체인 브레이크 최소화
```

**예시**: SARS-CoV-2 RBD 바인더 설계
```bash
# 전체 스파이크 단백질 (1200+ aa) 대신
# RBD 도메인만 사용 (200 aa)
# 결합 사이트 주변 잔기 포함
```

### 2. 핫스팟 잔기 선택

#### 핫스팟이란?
- 바인더가 반드시 접촉해야 하는 타겟의 잔기
- 10Å Cbeta 거리 이내로 정의
- 모델은 제공된 것보다 **더 많은** 접촉을 만듭니다

#### 선택 가이드
- **권장 개수**: 3-6개
- **선택 기준**:
  - 소수성 잔기 우선
  - 결합 포켓 전체에 분산
  - 표면에 노출된 잔기
  
#### 예시
```yaml
# 인슐린 수용체 바인더
hotspot_residues: [59, 83, 91]  # A체인의 3개 잔기

# SARS-CoV-2 RBD 바인더
hotspot_residues: [417, 446, 453, 484, 501]  # 5개 잔기
```

## ⚙️ RFdiffusion 파라미터 설명

### 핵심 파라미터

#### 1. **contigmap.contigs** - 구조 정의

```bash
# 기본 형식
'contigmap.contigs=[<타겟>/0 <바인더>]'

# 예시 1: 고정 길이 바인더
'contigmap.contigs=[A1-150/0 80-80]'  # 정확히 80aa 바인더

# 예시 2: 가변 길이 바인더 (권장)
'contigmap.contigs=[A1-150/0 70-100]'  # 70-100aa 사이에서 랜덤 샘플링

# 예시 3: 여러 타겟 체인
'contigmap.contigs=[A1-100/0 70-100/0 B1-50]'  # A, B 두 체인
```

**문법 설명**:
- `A1-150`: A체인의 1-150번 잔기 (타겟)
- `/0 `: 체인 브레이크 (공백 필수!)
- `70-100`: 생성할 바인더 길이 범위

#### 2. **ppi.hotspot_res** - 핫스팟 지정

```bash
# 형식: [체인ID+잔기번호, ...]
'ppi.hotspot_res=[A59,A83,A91]'

# 여러 체인
'ppi.hotspot_res=[A30,A33,B45,B67]'

# 많은 핫스팟 (6개까지 권장)
'ppi.hotspot_res=[A30,A33,A34,A45,A67,A89]'
```

#### 3. **diffuser.T** - 디퓨전 스텝 수

| 작업 | T 값 | 설명 |
|------|------|------|
| De novo 생성 | 50 | 기본값, 처음부터 백본 생성 |
| 빠른 생성 | 20 | 속도 10x, 품질 유사 |
| Refinement | 10-20 | Partial diffusion |

```bash
diffuser.T=50  # 기본값
```

#### 4. **denoiser.noise_scale** - 노이즈 제어

```bash
# 노이즈 스케일 (0-1)
denoiser.noise_scale_ca=0.0      # 좌표 이동
denoiser.noise_scale_frame=0.0   # 회전
```

| 값 | 품질 | 다양성 | 권장 용도 |
|----|------|--------|----------|
| 0.0 | ⭐⭐⭐ | ⭐ | 바인더 설계 (권장) |
| 0.5 | ⭐⭐ | ⭐⭐ | 균형잡힌 생성 |
| 1.0 | ⭐ | ⭐⭐⭐ | 최대 다양성 |

#### 5. **inference.num_designs** - 생성 개수

```bash
inference.num_designs=10  # 테스트용
inference.num_designs=1000  # 실제 캠페인용
inference.num_designs=10000  # 논문 스케일
```

**권장 스케일**:
- 테스트: 10-100 designs
- 소규모: 1,000 designs → ~100 backbones
- 대규모: 10,000 designs → ~1000 backbones (논문 수준)

## 📋 실행 예시

### 예시 1: 기본 바인더 설계

```bash
python /home01/hpc194a02/test/sim_pip/RFdiffusion/scripts/run_inference.py \
  inference.input_pdb=target.pdb \
  inference.output_prefix=outputs/binder \
  inference.num_designs=10 \
  'contigmap.contigs=[A1-150/0 70-100]' \
  'ppi.hotspot_res=[A30,A33,A34]' \
  diffuser.T=50 \
  denoiser.noise_scale_ca=0 \
  denoiser.noise_scale_frame=0
```

### 예시 2: 베타 모델 (다양한 토폴로지)

```bash
# 기본 모델은 주로 헬릭스 바인더 생성
# 베타 시트나 다른 토폴로지 원하면:
python scripts/run_inference.py \
  inference.ckpt_override_path=models/Complex_beta_ckpt.pt \
  inference.input_pdb=target.pdb \
  'contigmap.contigs=[A1-150/0 70-100]' \
  'ppi.hotspot_res=[A30,A33,A34]' \
  inference.num_designs=10
```

### 예시 3: Deterministic (재현 가능)

```bash
python scripts/run_inference.py \
  inference.deterministic=True \
  inference.input_pdb=target.pdb \
  'contigmap.contigs=[A1-150/0 70-100]' \
  'ppi.hotspot_res=[A30,A33,A34]' \
  inference.num_designs=10
```

## 🔧 파이프라인 설정 (`configs/run.yaml`)

```yaml
phase2:
  rfdiffusion:
    path: /home01/hpc194a02/test/sim_pip/RFdiffusion
    
    # De novo 생성 파라미터
    de_novo_T: 50                # 디퓨전 스텝 (기본값)
    binder_length: "70-100"      # 바인더 길이 범위
    noise_scale: 0.0             # 노이즈 스케일 (0=고품질)
    num_designs: 10              # 생성할 디자인 수
    
    # Refinement 파라미터
    refinement_T: 15             # Partial diffusion 스텝
    max_refinement_iterations: 3 # 최대 반복 횟수
    
    # 타겟 설정
    target_residues: "1-150"     # 포함할 타겟 잔기
```

## 📊 출력 파일

### 생성되는 파일

```
output_prefix_0.pdb        # 생성된 구조 (폴리글리신)
output_prefix_0.trb        # 메타데이터 (pickle)
output_prefix_0_pX0.pdb    # 예측 궤적
output_prefix_0_Xt-1.pdb   # 디퓨전 궤적
```

### .trb 파일 내용

```python
import pickle
with open('design_0.trb', 'rb') as f:
    trb = pickle.load(f)

# 유용한 정보:
trb['config']  # 사용된 전체 설정
trb['con_ref_pdb_idx']  # 입력 PDB 인덱스
trb['con_hal_pdb_idx']  # 출력 PDB 인덱스
trb['contig']  # 사용된 실제 contig
```

## ⚠️ 주의사항

### 1. 환경 설정
```bash
# RFdiffusion 실행 전 반드시 conda 환경 활성화
conda activate SE3nv
```

### 2. GPU 필요
- RFdiffusion은 GPU가 필수입니다
- CPU로 실행 가능하지만 매우 느립니다

### 3. 첫 실행 시간
- 첫 실행 시 "Calculating IGSO3" 과정 필요 (시간 소요)
- 이후 캐시되어 빠르게 실행됨

### 4. 메모리 요구사항
- 타겟 크기에 따라 다름
- 큰 타겟(500+ aa): 24GB+ GPU 메모리 권장
- 작은 타겟(<200 aa): 8GB GPU로 가능

## 🎓 모범 사례

### 1. Pilot 실행
```bash
# 대규모 실행 전 항상 소규모 테스트
inference.num_designs=5  # 파라미터 테스트
```

### 2. 반복적 개선
```bash
# 1단계: 넓은 범위
binder_length: "50-120"
noise_scale: 0.5

# 2단계: 좋은 결과 범위로 좁히기
binder_length: "70-90"
noise_scale: 0.0
```

### 3. 배치 실행
```bash
# SLURM 등에서 병렬 실행
for i in {1..100}; do
  sbatch run_rfdiffusion.sh --design_num=$i
done
```

## 📚 참고 자료

- [RFdiffusion 공식 문서](https://github.com/RosettaCommons/RFdiffusion)
- [RFdiffusion 논문](https://www.biorxiv.org/content/10.1101/2022.12.09.519842v1)
- [Google Colab Notebook](https://colab.research.google.com/github/sokrypton/ColabDesign/blob/v1.1.1/rf/examples/diffusion.ipynb)

## ❓ 트러블슈팅

### 문제: "No GPU detected"
```bash
# GPU 확인
nvidia-smi

# CUDA 버전 확인
nvcc --version

# conda 환경 재설치
conda env create -f env/SE3nv.yml
```

### 문제: "Hydra config error"
```bash
# Contig 문자열을 반드시 작은따옴표로 감싸기
'contigmap.contigs=[A1-150/0 70-100]'  # 올바름
contigmap.contigs=[A1-150/0 70-100]    # 오류!
```

### 문제: 바인더가 의도한 부위에 결합하지 않음
```bash
# 해결책:
# 1. 핫스팟 개수 늘리기 (3→6개)
# 2. 노이즈 줄이기 (0.5→0.0)
# 3. 타겟을 더 작게 자르기
```
