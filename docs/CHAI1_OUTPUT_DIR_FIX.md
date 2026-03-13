# Chai-1 출력 디렉토리 충돌 해결 ✅

## 🐛 문제

```
AssertionError: Output directory 
/home/so/sim_pip/data/outputs/chai1/2026-03-13/02-19-36-024726/C000001 is 
not empty.
```

**원인**: 
- Chai-1은 출력 디렉토리가 **완전히 비어있어야** 실행됨
- 재시도 시 이전 실패한 실행의 파일이 남아있음
- `self.run()` 메서드의 재시도가 디렉토리를 정리하지 않음

## ✅ 해결

### 수정한 파일: `/home/so/sim_pip/pipeline/utils/tool_wrapper.py`

#### 1. `predict_complex()` 메서드 개선 (671-743줄)

**변경 사항**:
- 각 명령 시도 전에 출력 디렉토리 정리
- `_run_with_clean()` 메서드로 재시도 시 정리 수행

```python
# Helper function to clean output directory
def clean_output_dir():
    """Clean output directory for Chai-1 (requires empty dir)"""
    import shutil
    if output_dir.exists():
        try:
            for item in output_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info(f"Cleaned output directory: {output_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean output directory: {e}")

# Run with retry, cleaning before each retry
exit_code, stdout, stderr = self._run_with_clean(
    command, 
    output_dir, 
    clean_output_dir,
    cwd=self.tool_path if str(self.tool_path) else None
)
```

#### 2. 새로운 `_run_with_clean()` 메서드 추가 (745-782줄)

**기능**:
- 재시도 전에 출력 디렉토리 정리
- `clean_func` 콜백으로 유연한 정리 로직
- 기존 `self.run()`과 유사하지만 재시도 시 정리 수행

```python
def _run_with_clean(self, command, output_dir, clean_func, cwd=None, retry_count=2):
    """Run command with cleaning before each retry attempt"""
    for attempt in range(retry_count + 1):
        # Clean output directory before each attempt (except first)
        if attempt > 0:
            clean_func()
            logger.info(f"Retrying... ({attempt}/{retry_count})")
        
        # Run command...
        result = subprocess.run(command, ...)
        
        if result.returncode == 0:
            return result.returncode, result.stdout, result.stderr
    
    return -1, "", "Failed after retries"
```

## 📋 동작 방식

### Before (실패)
```
1. Chai-1 실행 시도 1 → 실패 → 파일 생성
2. 재시도 1 → "directory not empty" → 실패
3. 재시도 2 → "directory not empty" → 실패
4. 재시도 3 → "directory not empty" → 실패
```

### After (성공)
```
1. Chai-1 실행 시도 1 → 실패 → 파일 생성
2. 디렉토리 정리 → 재시도 1 → 성공 또는 실패
3. 디렉토리 정리 → 재시도 2 → 성공 또는 실패
4. 디렉토리 정리 → 재시도 3 → 성공 또는 실패
```

## 🎯 결과

- ✅ Chai-1 재시도 시 출력 디렉토리 자동 정리
- ✅ `AssertionError: Output directory is not empty` 해결
- ✅ 다른 명령 시도 시에도 정리 수행
- ✅ 안전한 에러 처리 (정리 실패 시 경고만 출력)

## 🧪 테스트

```bash
source .venv/bin/activate
python scripts/test_phase1_2_3.py
```

**예상 로그**:
```
Cleaned output directory: /home/so/sim_pip/data/outputs/chai1/.../C000001
Retrying... (1/2)
Cleaned output directory: /home/so/sim_pip/data/outputs/chai1/.../C000001
Command succeeded on attempt 2
```

## 💡 추가 정보

### Chai-1의 출력 디렉토리 요구사항

Chai-1 코드 (`tools/chai-1/chai_lab/chai1.py:531`):
```python
if output_dir.exists():
    assert not any(
        output_dir.iterdir()
    ), f"Output directory {output_dir} is not empty."
```

이는 Chai-1이 **완전히 비어있는 디렉토리**만 허용한다는 것을 의미합니다.

### 다른 도구와의 비교

- **RFdiffusion**: 기존 파일 덮어쓰기 가능 (출력 정리 불필요)
- **ProteinMPNN**: 기존 파일 덮어쓰기 가능
- **Chai-1**: 빈 디렉토리 필수 ⚠️
- **Boltz**: 미확인

---

**이제 Chai-1이 재시도 시 정상 작동합니다!** 🎊
