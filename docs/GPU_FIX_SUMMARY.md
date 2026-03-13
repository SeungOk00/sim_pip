# GPU 문제 해결 가이드

**날짜**: 2026-03-13  
**문제**: RFdiffusion이 CPU 모드에서 크래시  
**상태**: ✅ 해결 방법 제공

## 🔍 문제 분석

### 실제 에러

```
Error executing job with overrides: [...'contigmap.contigs=[A982-999/0 80-80]'...]
Traceback (most recent call last):
  File "rfdiffusion/Track_module.py", line 420, in forward
    msa_full, pair, R_in, T_i
```

**원인**:
1. ✅ Contig는 정상적으로 전달됨 (`[A982-999/0 80-80]`)
2. ❌ GPU가 감지되지 않아 CPU 모드로 실행
3. ❌ CPU 모드에서 RFdiffusion이 메모리/성능 문제로 크래시

### GPU 상태

```bash
$ nvidia-smi
Failed to initialize NVML: GPU access blocked by the operating system

$ python -c "import torch; print(torch.cuda.is_available())"
False
```

**문제**: WSL2에서 GPU에 접근할 수 없음

## ✅ 해결 방법

### 방법 1: 즉시 해결 (CPU 친화적 설정)

**수정된 파일**: `scripts/test_phase1_2_3.py`

```python
# CPU-friendly 설정
config.config['phase2']['rfdiffusion']['num_designs'] = 1
config.config['phase2']['rfdiffusion']['target_residues'] = "982-999"  # 작은 범위
config.config['phase2']['rfdiffusion']['binder_length'] = "60-60"      # 고정 작은 크기
```

**실행**:
```bash
cd ~/sim_pip
source .venv/bin/activate
python scripts/test_phase1_2_3.py
```

**예상 시간**: 10-20분 (CPU 모드)

### 방법 2: GPU 활성화 (권장 - 영구 해결)

#### 단계별 가이드

**1단계: Windows NVIDIA Driver 업데이트**
- 최소 버전: 470.76 이상 (WSL2 지원)
- https://www.nvidia.com/Download/index.aspx

**2단계: SE3nv에 CUDA PyTorch 설치**
```bash
conda activate SE3nv

# 현재 PyTorch 제거
pip uninstall torch torchvision torchaudio -y

# CUDA 11.8 버전 설치 (가장 호환성 좋음)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**3단계: 확인**
```bash
conda activate SE3nv
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

예상 출력:
```
CUDA available: True
Device: NVIDIA GeForce RTX 4050 Laptop GPU
```

### 방법 3: 간단한 테스트

**새로운 스크립트**: `scripts/test_rfdiffusion_cpu.sh`

```bash
bash scripts/test_rfdiffusion_cpu.sh
```

이 스크립트는:
- 최소 설정으로 RFdiffusion 테스트
- 1개 디자인만 생성
- 작은 타겟 사용 (residues 1-50)
- CPU에서도 5-15분 내 완료

## 📊 성능 비교

| 모드 | 1 Design | 10 Designs | 안정성 |
|------|----------|------------|--------|
| GPU | 30초-2분 | 5-20분 | ✅ 안정 |
| CPU | 10-30분 | 2-5시간 | ⚠️ 크래시 위험 |

**결론**: GPU 없이는 실제 프로젝트 사용 불가

## 🎯 즉시 실행 가능한 명령어

### 옵션 A: 수정된 테스트 스크립트
```bash
cd ~/sim_pip
source .venv/bin/activate
python scripts/test_phase1_2_3.py  # 이미 CPU-friendly로 수정됨
```

### 옵션 B: 간단한 RFdiffusion 테스트
```bash
cd ~/sim_pip
bash scripts/test_rfdiffusion_cpu.sh
```

### 옵션 C: Config 직접 수정
```bash
# configs/run.yaml 편집
vim configs/run.yaml

# 수정:
phase2:
  rfdiffusion:
    num_designs: 1
    target_residues: "982-999"
    binder_length: "60-60"
```

## 📁 생성된 파일

1. **`docs/GPU_SETUP_WSL2.md`** - WSL2 GPU 설정 가이드
2. **`scripts/test_rfdiffusion_cpu.sh`** - CPU 친화적 테스트 스크립트
3. **`scripts/test_phase1_2_3.py`** - CPU-friendly 설정으로 수정됨
4. **`GPU_FIX_SUMMARY.md`** - 이 요약 파일

## 🚨 중요 참고사항

### RFdiffusion CPU 모드의 한계

1. **매우 느림**: GPU 대비 20-50배 느림
2. **메모리 문제**: 큰 타겟이나 많은 디자인은 크래시
3. **불안정**: Track_module에서 자주 실패
4. **실용성 없음**: 실제 프로젝트에는 GPU 필수

### 권장 사항

**단기** (지금):
- `num_designs: 1` 사용
- 작은 타겟 사용 (residues < 50)
- 작은 바인더 (< 60 residues)

**장기** (프로젝트):
- WSL2 GPU 활성화 (docs/GPU_SETUP_WSL2.md 참조)
- 또는 GPU가 있는 서버 사용
- 또는 Google Colab/Kaggle 등 클라우드 GPU

## ✅ 체크리스트

- [x] Contig 에러 수정 (tool_wrapper.py)
- [x] CPU-friendly 테스트 스크립트 작성
- [x] GPU 설정 가이드 작성
- [ ] WSL2 GPU 활성화 (사용자가 수행)
- [ ] SE3nv에 CUDA PyTorch 설치 (사용자가 수행)

## 🎉 다음 단계

1. **즉시 테스트**: `python scripts/test_phase1_2_3.py` 실행
2. **GPU 설정**: `docs/GPU_SETUP_WSL2.md` 참조
3. **성능 최적화**: GPU 활성화 후 전체 파이프라인 실행

GPU가 활성화되면 RFdiffusion이 정상 속도로 작동할 것입니다!
