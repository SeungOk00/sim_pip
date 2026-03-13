# RFdiffusion Python 환경 충돌 해결

## 🐛 문제

```
ImportError: cannot import name 'Mapping' from 'collections'
File "/home/so/sim_pip/.venv/lib/python3.13/site-packages/dgl/__init__.py"
```

**원인**: RFdiffusion이 **SE3nv conda 환경 (Python 3.9)** 대신 **`.venv` (Python 3.13)**의 패키지를 사용하고 있습니다.

## 🔍 근본 원인

1. `test_phase1_2_3.py`는 `.venv`에서 실행됨
2. `tool_wrapper.py`가 RFdiffusion을 실행할 때:
   - SE3nv conda 환경의 Python을 찾으려고 시도
   - 실패 시 `conda run`으로 폴백
   - **하지만**: `.venv`의 환경 변수(`VIRTUAL_ENV`, `PYTHONPATH`)가 간섭

3. 결과:
   - RFdiffusion이 `.venv`의 `dgl` 패키지 사용
   - `dgl`이 Python 3.13과 호환되지 않음 → `ImportError`

## ✅ 해결 방법

### 수정 사항 1: `_get_conda_python()` 개선

**파일**: `/home/so/sim_pip/pipeline/utils/tool_wrapper.py`

**변경**:
- 여러 가능한 conda 위치 검색
- conda Python 버전 확인 및 로그
- 명확한 에러 메시지

```python
def _get_conda_python(self) -> str:
    """Get Python executable from conda environment"""
    import os
    import platform
    
    # Try multiple possible conda locations
    possible_conda_bases = [
        os.path.expanduser('~/miniconda3'),
        os.path.expanduser('~/anaconda3'),
        '/opt/conda',
        os.environ.get('CONDA_PREFIX', '').replace(f'/envs/{self.conda_env}', '') if os.environ.get('CONDA_PREFIX') else None
    ]
    
    # Filter out None values
    possible_conda_bases = [p for p in possible_conda_bases if p]
    
    for conda_base in possible_conda_bases:
        if platform.system() == 'Windows':
            python_path = os.path.join(conda_base, 'envs', self.conda_env, 'python.exe')
        else:
            python_path = os.path.join(conda_base, 'envs', self.conda_env, 'bin', 'python')
        
        # Check if conda python exists
        if os.path.exists(python_path):
            logger.info(f"Found conda Python at: {python_path}")
            # Verify it's the correct Python version
            import subprocess
            try:
                result = subprocess.run([python_path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                logger.info(f"Conda Python version: {result.stdout.strip()}")
            except:
                pass
            return python_path
    
    # Fallback: try to use conda run
    logger.warning(f"Conda Python not found in any location, will try 'conda run'")
    logger.warning(f"Searched locations: {possible_conda_bases}")
    return None
```

### 수정 사항 2: 환경 변수 격리

**파일**: `/home/so/sim_pip/pipeline/utils/tool_wrapper.py`

**변경**:
- 기존 환경 변수 복사 (덮어쓰지 않음)
- `.venv` 관련 변수 제거 (`VIRTUAL_ENV`, `PYTHONHOME`)
- `conda run`에 `--no-capture-output` 추가

```python
# Copy existing environment and add PYTHONPATH
env = os.environ.copy()
env['PYTHONPATH'] = f"{self.tool_path}:{se3_path}:{env.get('PYTHONPATH', '')}"

# If using conda Python directly, unset VIRTUAL_ENV to prevent conflicts
if conda_python:
    logger.info("Unsetting VIRTUAL_ENV to prevent conflicts with conda environment")
    env.pop('VIRTUAL_ENV', None)
    env.pop('PYTHONHOME', None)

exit_code, stdout, stderr = self.run(command, cwd=self.tool_path, env=env)
```

### 수정 사항 3: conda run 개선

```python
# Fallback: use conda run
logger.info(f"Using 'conda run -n {self.conda_env}'")
command = [
    "conda", "run", "-n", self.conda_env, "--no-capture-output", "python",
    tool_script_posix,
    # ... rest of arguments
]
```

## 🧪 테스트

### 1. 환경 확인 테스트

```bash
bash scripts/test_rfdiffusion_env.sh
```

**예상 출력**:
```
1. Current Python (should be .venv Python 3.13):
/home/so/sim_pip/.venv/bin/python
Python 3.13.12

2. SE3nv conda Python (what RFdiffusion should use):
Python 3.9.x
  Path: /home/so/miniconda3/envs/SE3nv/bin/python

3. Checking dgl availability:
   In .venv (should FAIL):
ImportError: cannot import name 'Mapping' from 'collections'

   In SE3nv (should SUCCEED):
  ✓ dgl imported successfully

4. Testing conda run method:
  ✓ PyTorch: 1.9.x
  ✓ dgl imported
  ✓ CUDA: True/False
```

### 2. 전체 파이프라인 테스트

```bash
source .venv/bin/activate
python scripts/test_phase1_2_3.py
```

**로그에서 확인할 것**:
```
Found conda Python at: /home/so/miniconda3/envs/SE3nv/bin/python
Conda Python version: Python 3.9.x
Using conda Python directly: /home/so/miniconda3/envs/SE3nv/bin/python
Unsetting VIRTUAL_ENV to prevent conflicts with conda environment
```

## 📋 요약

| 구성 요소 | 사용해야 할 Python | 실제 사용된 Python (수정 전) | 수정 후 |
|---------|-----------------|------------------------|--------|
| test_phase1_2_3.py | .venv (Python 3.13) | ✅ .venv | ✅ .venv |
| RFdiffusion | SE3nv (Python 3.9) | ❌ .venv | ✅ SE3nv |
| dgl 패키지 | SE3nv | ❌ .venv | ✅ SE3nv |

## 🎯 결과

- ✅ RFdiffusion이 올바른 SE3nv conda 환경 사용
- ✅ `dgl` 패키지가 Python 3.9에서 정상 작동
- ✅ `.venv`와 conda 환경 간 격리
- ✅ 명확한 디버깅 로그

## 🔍 디버깅

로그에서 다음을 확인:

```bash
# 성공적인 실행
grep "Found conda Python" setup_log.txt
grep "Using conda Python directly" setup_log.txt
grep "Unsetting VIRTUAL_ENV" setup_log.txt

# 실패 시 (conda run 폴백)
grep "Using 'conda run" setup_log.txt
```

## 📚 관련 파일

- `/home/so/sim_pip/pipeline/utils/tool_wrapper.py` - 핵심 수정
- `/home/so/sim_pip/scripts/test_rfdiffusion_env.sh` - 테스트 스크립트
- `/home/so/sim_pip/tools/rfdiffusion/env/SE3nv.yml` - SE3nv 환경 정의
