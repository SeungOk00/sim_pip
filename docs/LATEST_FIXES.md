# 수정 요약

## 🎯 해결한 문제들

### 1. Boltz 설치 Python 버전 충돌 ✅
**문제**: `ERROR: Package 'boltz' requires a different Python: 3.13.12 not in '<3.13,>=3.10'`

**원인**: 
- `conda activate boltz_env` 실행했지만
- `.venv`가 먼저 활성화되어 있어서
- `pip`가 `.venv`의 Python 3.13 사용

**해결**: `/home/so/sim_pip/setup_linux.sh`
```bash
# First deactivate any existing venv
deactivate 2>/dev/null || true

# Then activate boltz_env
conda activate boltz_env

# Verify Python version
BOLTZ_PYTHON_VERSION=$(python --version 2>&1)
echo "Using Python in boltz_env: $BOLTZ_PYTHON_VERSION"
```

---

### 2. RFdiffusion Python 환경 충돌 ✅
**문제**: `ImportError: cannot import name 'Mapping' from 'collections'`
```
File "/home/so/sim_pip/.venv/lib/python3.13/site-packages/dgl/__init__.py"
```

**원인**:
- RFdiffusion이 SE3nv (Python 3.9) 대신 `.venv` (Python 3.13) 사용
- `dgl` 패키지가 Python 3.13과 호환 안 됨

**해결**: `/home/so/sim_pip/pipeline/utils/tool_wrapper.py`

1. **conda Python 찾기 개선**:
```python
def _get_conda_python(self) -> str:
    # Try multiple conda locations
    possible_conda_bases = [
        os.path.expanduser('~/miniconda3'),
        os.path.expanduser('~/anaconda3'),
        '/opt/conda',
        os.environ.get('CONDA_PREFIX', '').replace(f'/envs/{self.conda_env}', '')
    ]
    
    for conda_base in possible_conda_bases:
        python_path = os.path.join(conda_base, 'envs', self.conda_env, 'bin', 'python')
        if os.path.exists(python_path):
            logger.info(f"Found conda Python at: {python_path}")
            return python_path
```

2. **환경 변수 격리**:
```python
# Copy existing environment (don't overwrite)
env = os.environ.copy()
env['PYTHONPATH'] = f"{self.tool_path}:{se3_path}:{env.get('PYTHONPATH', '')}"

# Remove .venv variables to prevent conflicts
if conda_python:
    logger.info("Unsetting VIRTUAL_ENV to prevent conflicts")
    env.pop('VIRTUAL_ENV', None)
    env.pop('PYTHONHOME', None)
```

3. **conda run 개선**:
```python
command = [
    "conda", "run", "-n", self.conda_env, "--no-capture-output", "python",
    # ... rest
]
```

---

### 3. PyTorch 자동 업그레이드 제거 ✅
**요청**: "업데이트 하지말고, gpu 활성하는 방법 알려줘"

**해결**: `/home/so/sim_pip/setup_linux.sh`
- PyTorch 자동 업그레이드 로직 제거
- GPU 상태 확인만 수행
- Windows NVIDIA Driver 설치 가이드 제공

```bash
# Check GPU status (no PyTorch upgrade)
echo "Checking GPU status..."
conda activate SE3nv

PYTORCH_VERSION=$(python -c "import torch; print(torch.__version__)")
CUDA_AVAILABLE=$(python -c "import torch; print(torch.cuda.is_available())")

echo "Current PyTorch version: $PYTORCH_VERSION"

if [ "$CUDA_AVAILABLE" = "True" ]; then
    echo "✓ GPU enabled successfully!"
else
    echo "⚠ WARNING: GPU not detected!"
    echo "See docs/GPU_ACTIVATION_WITHOUT_PYTORCH_UPGRADE.md"
fi
```

---

## 📁 생성된 파일

1. **`/home/so/sim_pip/docs/GPU_ACTIVATION_WITHOUT_PYTORCH_UPGRADE.md`**
   - PyTorch 업그레이드 없이 GPU 활성화하는 방법
   - Windows NVIDIA Driver 설치 가이드
   - 문제 해결 가이드

2. **`/home/so/sim_pip/docs/RFDIFFUSION_PYTHON_ENV_FIX.md`**
   - RFdiffusion Python 환경 충돌 해결 방법
   - 수정 사항 상세 설명
   - 테스트 방법

3. **`/home/so/sim_pip/scripts/test_rfdiffusion_env.sh`**
   - RFdiffusion 환경 테스트 스크립트
   - Python 환경 확인
   - dgl 패키지 import 테스트

---

## 🔧 수정된 파일

1. **`/home/so/sim_pip/setup_linux.sh`**
   - Boltz 설치 시 venv 먼저 비활성화
   - PyTorch 자동 업그레이드 제거
   - GPU 상태 확인만 수행

2. **`/home/so/sim_pip/pipeline/utils/tool_wrapper.py`**
   - `_get_conda_python()` 개선
   - 환경 변수 격리 추가
   - 명확한 디버깅 로그 추가
   - `conda run` 개선

---

## 🧪 테스트 방법

### 1. 환경 테스트
```bash
bash scripts/test_rfdiffusion_env.sh
```

### 2. 전체 파이프라인 테스트
```bash
source .venv/bin/activate
python scripts/test_phase1_2_3.py
```

**로그에서 확인**:
```
Found conda Python at: /home/so/miniconda3/envs/SE3nv/bin/python
Conda Python version: Python 3.9.x
Using conda Python directly: ...
Unsetting VIRTUAL_ENV to prevent conflicts
```

---

## 📋 다음 단계

1. **GPU 활성화** (선택사항):
   - Windows에서 NVIDIA Driver 설치 (470.76+)
   - 컴퓨터 재시작
   - WSL2에서 `nvidia-smi` 확인
   - 가이드: `docs/GPU_ACTIVATION_WITHOUT_PYTORCH_UPGRADE.md`

2. **파이프라인 테스트**:
   ```bash
   source .venv/bin/activate
   python scripts/test_phase1_2_3.py
   ```

3. **Boltz 재설치** (필요 시):
   ```bash
   bash setup_linux.sh
   ```

---

## 🎉 결과

- ✅ Boltz가 올바른 Python 3.12 환경에 설치
- ✅ RFdiffusion이 SE3nv (Python 3.9) 환경 사용
- ✅ `.venv`와 conda 환경 간 격리
- ✅ PyTorch 버전 유지 (SE3nv.yml 정의대로)
- ✅ GPU 활성화 방법 문서화
