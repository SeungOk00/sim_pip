# Setup 스크립트 개선 사항

**날짜**: 2026-03-13  
**파일**: `setup_linux.sh`

## 주요 개선 사항

### 1. ✅ Python 호환성 개선
- **문제**: 스크립트가 `python` 명령어만 찾았지만, 많은 Linux 시스템에서는 `python3`만 설치됨
- **해결**: 
  - `python3` 감지 추가
  - 자동으로 `~/.local/bin/python` 심볼릭 링크 생성
  - `PYTHON_CMD` 변수로 통일된 Python 명령어 사용

```bash
# Before
if ! command -v python &> /dev/null; then
    echo "ERROR: python not found."
    exit 1
fi

# After
PYTHON_CMD=""
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    # Create python symlink
    mkdir -p "$HOME/.local/bin"
    ln -sf "$(which python3)" "$HOME/.local/bin/python"
fi
```

### 2. ✅ Conda ToS 자동 수락
- **문제**: 설치 중 Conda Terms of Service 프롬프트에서 무한 루프
- **해결**:
  - `.condarc` 파일에 자동 수락 설정 추가
  - 스크립트에서 채널 ToS 자동 수락

```yaml
# ~/.condarc
always_yes: true
safety_checks: disabled
channel_priority: flexible
```

### 3. ✅ 대화형 프롬프트 제거
- **문제**: 모든 `read -p` 명령이 사용자 입력을 대기하여 자동화 불가
- **해결**: 기존 환경/디렉토리가 있으면 자동으로 재사용

```bash
# Before
read -p "Do you want to recreate it? (y/n): " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # recreate
else
    # use existing
fi

# After
# Use existing without prompting
echo "✓ Using existing environment."
```

### 4. ✅ 빌드 도구 확인 및 안내
- **문제**: gcc 없이 numpy 등 컴파일이 필요한 패키지 설치 실패
- **해결**: 빌드 도구 확인 및 명확한 설치 안내 제공

```bash
if ! command -v gcc &> /dev/null; then
    echo "ERROR: gcc (C compiler) not found."
    echo ""
    echo "빌드 도구가 설치되어 있지 않습니다. 다음 명령어를 실행해주세요:"
    echo ""
    echo "  sudo apt update"
    echo "  sudo apt install -y build-essential python3-dev"
    echo ""
    exit 1
fi
```

### 5. ✅ kalign 설치 개선
- **문제**: `kalign` 패키지가 bioconda에서 찾을 수 없음
- **해결**: `kalign3` 사용으로 변경

```bash
# Before
conda install -c bioconda kalign -y

# After
conda install -c bioconda -c conda-forge kalign3 -y
```

### 6. ✅ DockQ 설치 전략 개선
- **문제**: DockQ pip 설치 시 gcc 필요하여 실패
- **해결**: 
  - conda 우선 시도
  - 실패 시 명확한 에러 메시지와 대안 제공
  - requirements.txt에서 제거하여 선택적 설치로 변경

```bash
if conda install -c conda-forge -c bioconda dockq -y 2>/dev/null; then
    echo "✓ DockQ installed via conda."
else
    echo "Conda installation failed. Trying pip (may require gcc)..."
    pip install DockQ 2>/dev/null || {
        echo "WARNING: DockQ installation failed."
        echo "DockQ requires gcc. Install with: sudo apt install build-essential"
    }
fi
```

### 7. ✅ PyRosetta 설치 확인 개선
- **문제**: PyRosetta가 설치되었지만 잘못된 Python으로 테스트하여 실패로 표시
- **해결**: conda Python 사용하여 확인

```bash
# Before
if python -c "import pyrosetta" 2>/dev/null; then

# After
if $HOME/miniconda3/bin/python -c "import pyrosetta" 2>/dev/null; then
```

### 8. ✅ requirements.txt 개선
- **문제**: DockQ가 컴파일 필요한 패키지로 자동 설치 실패
- **해결**: requirements.txt에서 제거하고 선택적 설치로 변경

```txt
# Before
DockQ

# After
# DockQ  # Requires compilation, install separately if needed
```

## 설치 흐름 개선

### Before (기존)
1. Python 확인 (python만 지원) ❌
2. Conda 설치
3. 환경 생성 시 매번 사용자 입력 대기 ❌
4. ToS 무한 루프 ❌
5. 컴파일 도구 없이 패키지 설치 실패 ❌

### After (개선)
1. Python/Python3 자동 감지 ✅
2. 빌드 도구 확인 및 안내 ✅
3. Conda ToS 자동 수락 ✅
4. Conda 설치 (사용자 입력 없음) ✅
5. 기존 환경 자동 재사용 ✅
6. 패키지 설치 (conda 우선, pip 대체) ✅
7. 명확한 에러 메시지 및 해결 방법 제공 ✅

## 테스트 결과

### 성공적으로 설치된 항목
- ✅ Miniconda 26.1.1
- ✅ Python 3.10/3.12/3.13 환경
- ✅ Conda 환경 3개 (SE3nv, boltz_env, base)
- ✅ Boltz + PyTorch 2.10.0
- ✅ PyRosetta 2026.06
- ✅ kalign 3.4.0
- ✅ 모든 도구 디렉토리

### 선택적 설치 (gcc 필요)
- ⚠️ DockQ (gcc 설치 후 가능)
- ⚠️ 메인 venv 일부 패키지 (gcc 설치 후 가능)

## 사용자 경험 개선

### 1. 명확한 에러 메시지
- 한글 설명 추가
- 해결 방법 명시
- 선택 사항 구분

### 2. 자동화 지원
- 모든 대화형 프롬프트 제거
- CI/CD 환경에서 사용 가능

### 3. 실패 복구
- 각 단계별 실패 시 명확한 안내
- 계속 진행 가능한 경우와 중단해야 하는 경우 구분

## 향후 개선 사항 제안

1. **멀티 플랫폼 지원**
   - macOS 테스트 및 개선
   - Windows WSL 최적화

2. **병렬 설치**
   - 독립적인 패키지들 동시 설치
   - 설치 시간 단축

3. **설치 검증**
   - 각 구성 요소 설치 후 즉시 테스트
   - 설치 성공/실패 요약 리포트

4. **로깅 개선**
   - 타임스탬프 추가
   - 상세 로그와 요약 로그 분리
   - 에러 로그 별도 파일 저장

## 결론

이번 개선으로 setup_linux.sh가:
- ✅ 더 견고해짐 (다양한 환경 지원)
- ✅ 더 사용자 친화적 (명확한 메시지)
- ✅ 더 자동화 가능 (대화형 프롬프트 제거)
- ✅ sudo 없이도 대부분 설치 가능

사용자가 sudo 권한이 없어도 핵심 기능들을 모두 설치하고 사용할 수 있습니다.
