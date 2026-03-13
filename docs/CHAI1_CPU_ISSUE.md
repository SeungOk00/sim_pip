# Chai-1 실행 문제 해결 가이드

## 🐛 현재 문제

```
Trunk recycles:   0%|          | 0/3 [00:00<?, ?it/s]
```

Chai-1이 CPU에서 실행되고 있어 매우 느림 (2분 이상 소요, GPU 없이는 완료 불가능)

---

## 🛑 즉시 해결 방법

### 1. 현재 실행 중단

**터미널에서**:
```bash
# Ctrl+C를 눌러 실행 중단
Ctrl+C
```

---

## ✅ 해결책 옵션

### 옵션 1: Chai-1 비활성화 (권장)

Chai-1 없이 파이프라인을 계속 진행하려면:

**`pipeline/config.py` 수정**:

```python
# Phase 3-A: Fast Screening
"phase3_fast": {
    "chai": {
        "enabled": False,  # ← 이 줄 추가
        "path": str(Path(__file__).resolve().parent.parent / "tools/chai-1"),
        "venv_path": "",
        "command_template": "",
        "output_file": ""
    },
    # ...
}
```

그런 다음 `phase3_screen.py`에서 enabled 확인:

```python
# Fast screen에서 Chai-1 건너뛰기
if self.fast_config.get("chai", {}).get("enabled", True):
    # Chai-1 실행
    chai_pdb, chai_conf = self.chai.predict_complex(...)
else:
    logger.info("Chai-1 disabled, skipping...")
    candidate.complex_pdb_path = None
```

---

### 옵션 2: GPU 활성화 (근본 해결)

#### 2-1. Windows NVIDIA Driver 설치

1. **GeForce Experience 설치** (가장 쉬움):
   ```
   https://www.nvidia.com/geforce/geforce-experience/
   ```

2. **또는 수동 다운로드**:
   ```
   https://www.nvidia.com/Download/index.aspx
   
   선택:
   - Product Type: GeForce
   - Product Series: RTX 40 Series (Notebooks)
   - Product: GeForce RTX 4050 Laptop GPU
   - OS: Windows 11
   ```

3. **설치 후 컴퓨터 재시작** (필수!)

4. **확인**:
   ```powershell
   # Windows PowerShell
   nvidia-smi
   
   # WSL2에서도 확인
   nvidia-smi
   ```

#### 2-2. Chai-1에서 GPU 확인

```bash
source .venv/bin/activate
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

**예상 결과**:
- CPU: `CUDA: False` ← 현재 상태
- GPU: `CUDA: True` ← 목표

---

### 옵션 3: Chai-1 타임아웃 설정

Chai-1이 너무 오래 걸리면 자동 건너뛰기:

**`pipeline/utils/tool_wrapper.py`의 `ChaiRunner` 수정**:

```python
def predict_complex(...):
    # 타임아웃 추가
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Chai-1 execution timeout")
    
    # 5분 타임아웃
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)  # 5 minutes
    
    try:
        # 기존 실행 코드
        exit_code, stdout, stderr = self._run_with_clean(...)
    except TimeoutError:
        logger.warning("Chai-1 timed out, skipping...")
        return None, {}
    finally:
        signal.alarm(0)  # 타임아웃 취소
```

---

## 🎯 권장 순서

### 단기 해결 (지금 당장)

1. **Ctrl+C로 중단**
2. **Chai-1 비활성화**:
   ```python
   # config.py
   "phase3_fast": {
       "chai": {"enabled": False, ...}
   }
   ```
3. **테스트 재실행**:
   ```bash
   python scripts/test_phase1_2_3.py
   ```

### 장기 해결 (근본적)

1. **Windows NVIDIA Driver 설치**
2. **컴퓨터 재시작**
3. **GPU 확인**: `nvidia-smi`
4. **Chai-1 다시 활성화**:
   ```python
   "phase3_fast": {
       "chai": {"enabled": True, ...}
   }
   ```

---

## 📊 Chai-1 성능 비교

| 환경 | 소요 시간 | 성공률 |
|-----|---------|-------|
| CPU (현재) | 수 시간 ~ 무한 | 0% (메모리 부족) |
| GPU (목표) | 1-5분 | 95%+ |

---

## 🔍 현재 상태 확인

```bash
# GPU 상태
nvidia-smi

# PyTorch CUDA
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 실행 중인 프로세스
ps aux | grep python
```

---

## 💡 추가 정보

- **Chai-1은 선택사항**: Phase 3에서 필수가 아님
- **대안**: Boltz를 사용하거나 둘 다 건너뛰고 ColabFold로 진행 가능
- **GPU 없으면**: Chai-1, Boltz는 실용적이지 않음
- **상세 가이드**: `docs/GPU_ACTIVATION_WITHOUT_PYTORCH_UPGRADE.md`

---

**당장 해야 할 일**:
1. Ctrl+C로 중단
2. Chai-1 비활성화
3. 테스트 재실행

**나중에 할 일**:
1. GPU 활성화
2. Chai-1 다시 사용
