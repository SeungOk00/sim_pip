# RFdiffusion 사용 가이드

## 문제 해결: "Must either specify a contig string" 에러

### 원인
RFdiffusion을 실행할 때 `target_residues`와 `binder_length`가 지정되지 않으면 contig 정보가 전달되지 않아 에러가 발생합니다.

### 해결 방법

#### 1. 설정 파일에서 지정 (권장)

`configs/run.yaml` 파일에서 다음 항목을 설정하세요:

```yaml
phase2:
  rfdiffusion:
    target_residues: "27-147"     # PDB 파일의 실제 residue 범위
    binder_length: "70-100"       # 원하는 바인더 길이
```

**중요**: `target_residues`는 PDB 파일에 실제로 존재하는 residue 번호를 사용해야 합니다!

#### 2. PDB 파일의 residue 번호 확인 방법

```bash
# Chain A의 residue 번호 확인
grep "^ATOM" your_target.pdb | awk '{print $6}' | sort -un | head -20

# 또는 첫 번째와 마지막 residue 확인
grep "^ATOM" your_target.pdb | awk '{print $6}' | sort -un | tail -1
```

#### 3. 일반적인 PDB 파일 패턴

- **항체**: residue가 보통 1부터 시작하지만, 불연속적일 수 있음
- **단백질 도메인**: residue 번호가 전체 단백질 기준으로 매겨져서 100+부터 시작할 수 있음
- **구조 생물학 PDB**: 결정 구조는 일부 residue가 missing될 수 있음

### 기본값

tool_wrapper.py에서 자동으로 사용하는 기본값:
- `target_residues`: "1-150"
- `binder_length`: "70-100"

하지만 **실제 PDB 파일에 맞게 수정하는 것을 강력히 권장**합니다!

## 예제

### 예제 1: 4IBM (Insulin Receptor)
```yaml
phase2:
  rfdiffusion:
    target_residues: "982-1150"   # Kinase domain
    binder_length: "70-100"
```

### 예제 2: 5TPN (불연속 residues)
```yaml
phase2:
  rfdiffusion:
    target_residues: "27-147"     # 실제 범위
    binder_length: "70-100"
```

### 예제 3: 전체 단백질
```yaml
phase2:
  rfdiffusion:
    target_residues: "1-300"      # 전체 단백질
    binder_length: "50-80"        # 작은 바인더
```

## GPU 관련 메시지

```
NO GPU DETECTED! Falling back to CPU
```

이 메시지가 나타나면:

1. **WSL2 사용자**: CUDA 설정 확인
   ```bash
   nvidia-smi
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Conda 환경 확인**:
   ```bash
   conda activate SE3nv
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. CPU 모드로도 작동하지만 매우 느립니다 (수십 배 차이)

## 추가 팁

### Contig 문자열 형식
```
contigmap.contigs=[A27-147/0 70-100]
```

의미:
- `A27-147`: Chain A의 residue 27-147 사용
- `/0`: Gap (링커)
- `70-100`: 70-100개 residue의 바인더 생성

### Hotspot 지정
```python
hotspot_residues = [982, 990, 995]  # 중요한 residue 번호
```

이 번호들도 PDB 파일에 실제로 존재해야 합니다!

## 문제 해결 체크리스트

- [ ] PDB 파일의 실제 residue 번호 확인
- [ ] `configs/run.yaml`에 올바른 `target_residues` 설정
- [ ] `binder_length` 설정 (기본값: 70-100)
- [ ] Hotspot residues가 target_residues 범위 내에 있는지 확인
- [ ] GPU가 감지되는지 확인
- [ ] SE3nv conda 환경이 활성화되는지 확인
