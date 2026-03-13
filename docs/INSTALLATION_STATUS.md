# 설치 상태 요약

**날짜**: 2026-03-13  
**시스템**: Linux (WSL2)  
**Python 버전**: 3.10.12 (시스템), 3.12.12 (Boltz), 3.13.12 (메인 venv)

## ✅ 성공적으로 설치된 구성 요소

### 1. Miniconda
- **위치**: `/home/so/miniconda3`
- **버전**: conda 26.1.1
- **상태**: ✓ 설치 완료

### 2. Conda 환경들

#### SE3nv (RFdiffusion 환경)
- **위치**: `/home/so/miniconda3/envs/SE3nv`
- **용도**: RFdiffusion 실행
- **상태**: ✓ 생성 완료

#### boltz_env (Boltz 환경)
- **위치**: `/home/so/miniconda3/envs/boltz_env`
- **Python**: 3.12.12
- **주요 패키지**:
  - torch 2.10.0
  - boltz 2.2.1
  - pytorch-lightning 2.5.0
- **상태**: ✓ 완전히 설치됨

### 3. 메인 가상환경 (.venv)
- **Python**: 3.13.12
- **상태**: ✓ 완전히 설치됨
- **주요 패키지**:
  - torch 2.6.0 (CUDA 12.4)
  - numpy 1.26.4
  - pandas 3.0.1
  - scipy 1.17.1
  - biopython 1.86
  - pyyaml 6.0.3
  - hydra-core 1.3.2
  - e3nn 0.6.0
  - 모든 NVIDIA CUDA 라이브러리

### 4. PyRosetta
- **설치 위치**: Conda base 환경
- **버전**: 2026.06+release
- **상태**: ✓ 설치 완료

### 5. 시스템 도구
- **kalign**: 3.4.0 ✓
- **DockQ**: 2.1.3 ✓
- **GPU**: NVIDIA GeForce RTX 4050 Laptop GPU ✓

### 6. 도구 디렉토리
설치된 도구들:
- ✓ RFdiffusion (`/home/so/sim_pip/tools/rfdiffusion`) + 모델 파일
- ✓ Boltz (`/home/so/sim_pip/tools/boltz`)
- ✓ Chai-1 (`/home/so/sim_pip/tools/chai-1`)
- ✓ ProteinMPNN (`/home/so/sim_pip/tools/proteinmpnn`)
- ✓ ColabFold (`/home/so/sim_pip/tools/colabfold`)
- ✓ DockQ (`/home/so/sim_pip/tools/dockq`)

## ✅ 모든 구성 요소 설치 완료!

**설치 검증 상태**: 모든 체크 통과 ✓

## 🚀 다음 단계

### 설치 검증 완료! ✅

모든 구성 요소가 성공적으로 설치되었습니다.

### 파이프라인 사용 시작

#### 1. 메인 환경 활성화
```bash
cd ~/sim_pip
source .venv/bin/activate
```

#### 2. 설치 확인
```bash
bash scripts/verify_installation.sh
```

#### 3. 파이프라인 실행
```bash
python main.py --help
```

### 환경별 사용 방법

### 메인 파이프라인 실행
```bash
cd ~/sim_pip
source .venv/bin/activate
python main.py --target-pdb target.pdb
```

### RFdiffusion 사용
```bash
conda activate SE3nv
# RFdiffusion 명령어 실행
```

### Boltz 사용
```bash
conda activate boltz_env
boltz predict --help
```

### PyRosetta 사용
```bash
conda activate base
python -c "import pyrosetta; pyrosetta.init()"
```

## 💡 참고사항

1. **GPU**: NVIDIA GeForce RTX 4050 Laptop GPU 감지됨
2. **sudo 없이 설치**: 대부분의 구성 요소는 sudo 없이 conda를 통해 설치되었습니다
3. **Python 버전**: 
   - 시스템: 3.10.12
   - 메인 venv: 3.13.12
   - Boltz: 3.12.12 (Boltz는 Python <3.13 필요)
4. **Conda 설정**: Terms of Service 자동 수락 설정 완료

## 🔧 문제 해결

### 문제: "gcc not found" 에러
**해결**: `sudo apt install build-essential`

### 문제: PyRosetta import 실패
**해결**: 
```bash
conda activate base
conda install -c https://conda.rosettacommons.org -c conda-forge pyrosetta
```

### 문제: GPU 인식 안 됨
**확인**: 
```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

## 📝 추가 정보

- 설치 로그: `/home/so/sim_pip/setup_log.txt`
- 프로젝트 문서: `/home/so/sim_pip/README.md`
- 설치 가이드: `/home/so/sim_pip/INSTALLATION.md`
