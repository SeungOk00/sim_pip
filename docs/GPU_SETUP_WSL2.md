# WSL2에서 GPU (CUDA) 활성화 가이드

## 현재 상태

```
nvidia-smi: Failed to initialize NVML: GPU access blocked by the operating system
PyTorch CUDA: Available = False
```

**문제**: WSL2에서 GPU에 접근할 수 없어 RFdiffusion이 CPU 모드로 실행되고 크래시 발생

## GPU 활성화 방법

### 방법 1: WSL2 CUDA 지원 활성화 (권장)

#### 1단계: Windows에서 NVIDIA Driver 업데이트

Windows에서 (WSL 내부가 아님):

1. **NVIDIA Driver 다운로드**
   - https://www.nvidia.com/Download/index.aspx
   - 또는 GeForce Experience 사용
   - **최소 버전**: 470.76 이상 (WSL2 지원)

2. **설치 후 확인**
   ```powershell
   # PowerShell에서 실행
   nvidia-smi
   ```

#### 2단계: WSL2에서 CUDA Toolkit 확인

WSL2 내부에서:

```bash
# CUDA 런타임 확인
ls -la /usr/local/cuda*/

# 없으면 설치
# CUDA Toolkit을 WSL2에 직접 설치할 필요는 없습니다
# Windows의 NVIDIA Driver가 WSL2로 자동 전달됨
```

#### 3단계: PyTorch CUDA 버전 확인

```bash
conda activate SE3nv
python -c "import torch; print(torch.__version__); print(torch.version.cuda)"
```

**문제 발견**: SE3nv 환경의 PyTorch가 CUDA를 지원하지 않을 수 있음

#### 4단계: CUDA 버전 PyTorch 재설치

```bash
conda activate SE3nv

# 현재 PyTorch 제거
pip uninstall torch torchvision torchaudio -y

# CUDA 버전 PyTorch 설치
# CUDA 11.8 버전 (가장 호환성 좋음)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 또는 CUDA 12.1
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 5단계: 확인

```bash
conda activate SE3nv
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

예상 출력:
```
CUDA available: True
Device: NVIDIA GeForce RTX 4050 Laptop GPU
```

### 방법 2: CPU 모드로 실행 (임시)

GPU가 작동하지 않으면 CPU 모드에서 더 안정적으로 실행:

#### Option A: 디자인 수 줄이기

`configs/run.yaml`:
```yaml
phase2:
  rfdiffusion:
    num_designs: 1  # 10에서 1로 줄임
```

#### Option B: 더 작은 타겟 사용

```yaml
phase2:
  rfdiffusion:
    target_residues: "982-999"  # 범위 축소 (982-1150 → 982-999)
    binder_length: "50-60"      # 작은 바인더 (70-100 → 50-60)
```

#### Option C: RFdiffusion 스킵 (테스트용)

Phase 2를 건너뛰고 Phase 3부터 테스트:
```python
# test_phase1_2_3.py에서
# Phase 2 주석 처리
# phase2 = Phase2GenerativeDesign(config.to_dict())
# state = phase2.run(state)
```

## 추천 순서

### 1. 빠른 테스트 (지금 바로)
```bash
# configs/run.yaml 수정
phase2:
  rfdiffusion:
    num_designs: 1
    target_residues: "982-999"
    binder_length: "60-60"
```

### 2. GPU 활성화 (영구 해결책)
1. Windows에서 NVIDIA Driver 업데이트 (470.76+)
2. SE3nv에 CUDA PyTorch 설치
3. 테스트 재실행

## 확인 스크립트

```bash
#!/bin/bash
# check_gpu.sh

echo "=== GPU 상태 확인 ==="
echo ""

echo "1. NVIDIA Driver (Windows)"
nvidia-smi 2>&1 | head -5

echo ""
echo "2. SE3nv PyTorch CUDA"
~/miniconda3/envs/SE3nv/bin/python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'Device: {torch.cuda.get_device_name(0)}')
else:
    print('CUDA not available - check driver and PyTorch installation')
"

echo ""
echo "3. Main venv PyTorch CUDA"
source ~/sim_pip/.venv/bin/activate
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
"
```

## 예상 결과

### GPU 작동 시
- RFdiffusion: 약 30초-2분 per design
- 10 designs: 5-20분

### CPU 모드 시  
- RFdiffusion: 약 10-30분 per design
- 10 designs: 2-5시간 (비현실적)
- **크래시 가능성 높음**

## 결론

**즉시 해결**: `num_designs: 1`로 설정하고 작은 타겟 사용

**영구 해결**: Windows에서 NVIDIA Driver 업데이트 + SE3nv에 CUDA PyTorch 설치

GPU 없이는 RFdiffusion을 실제 프로젝트에 사용하기 어렵습니다.
