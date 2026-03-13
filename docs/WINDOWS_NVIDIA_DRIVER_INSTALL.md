# Windows NVIDIA Driver 설치 가이드

WSL2에서 GPU를 사용하려면 **Windows에 NVIDIA Driver**를 설치해야 합니다.

## 🎯 필수 요구사항

- **최소 Driver 버전**: 470.76 이상
- **GPU**: NVIDIA GeForce, RTX, Quadro 등
- **OS**: Windows 10/11 (64-bit)
- **WSL**: WSL2 (WSL1은 GPU 지원 안 함)

## 📥 설치 방법

### 방법 1: 자동 감지 및 다운로드 (권장)

1. **NVIDIA 공식 다운로드 페이지 접속**
   
   https://www.nvidia.com/Download/index.aspx

2. **GPU 자동 감지**
   
   웹페이지에서 "Option 2: Automatically find drivers for my NVIDIA products" 클릭
   
   또는 수동으로 선택:
   - **Product Type**: GeForce
   - **Product Series**: RTX 40 Series (Notebooks)
   - **Product**: GeForce RTX 4050 Laptop GPU
   - **Operating System**: Windows 11 (또는 10)
   - **Download Type**: Game Ready Driver (GRD)

3. **다운로드 및 설치**
   
   "Search" → "Download" 클릭 → 설치 파일 실행

### 방법 2: GeForce Experience 사용 (간편)

1. **GeForce Experience 다운로드**
   
   https://www.nvidia.com/en-us/geforce/geforce-experience/

2. **설치 및 실행**
   
   GeForce Experience 설치 → "Drivers" 탭 → "Check for updates"

3. **최신 드라이버 설치**
   
   자동으로 최신 드라이버 다운로드 및 설치

### 방법 3: Windows Update (기본)

1. **Windows 설정 열기**
   
   `Windows + I` → "Windows Update"

2. **고급 옵션**
   
   "Advanced options" → "Optional updates"

3. **NVIDIA 드라이버 확인**
   
   목록에서 NVIDIA Driver 선택 → 설치

   ⚠️ 주의: Windows Update의 드라이버는 최신이 아닐 수 있음

## ✅ 설치 확인

### 1. PowerShell에서 확인

PowerShell 또는 CMD를 열고:

```powershell
nvidia-smi
```

**예상 출력**:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx       Driver Version: 535.xx       CUDA Version: 12.2    |
|-------------------------------+----------------------+----------------------+
| GPU  Name            TCC/WDDM | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ... WDDM  | 00000000:01:00.0 Off |                  N/A |
| N/A   45C    P8     3W /  N/A |    123MiB /  6144MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

중요한 정보:
- **Driver Version**: 535.xx (470.76 이상이어야 함)
- **GPU Name**: 본인의 GPU 모델
- **Memory**: 총 GPU 메모리

### 2. WSL2에서 확인

WSL2 터미널에서:

```bash
nvidia-smi
```

동일한 GPU 정보가 표시되어야 합니다.

### 3. Python에서 확인

WSL2의 SE3nv 환경에서:

```bash
conda activate SE3nv
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**예상 출력**:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 4050 Laptop GPU
```

## 🔧 문제 해결

### 문제 1: "nvidia-smi: command not found" (Windows)

**원인**: NVIDIA Driver가 설치되지 않음

**해결**:
1. 위의 설치 방법 중 하나로 드라이버 설치
2. 컴퓨터 재시작
3. 다시 확인

### 문제 2: "GPU access blocked by the operating system" (WSL2)

**원인**: WSL2가 GPU에 접근할 수 없음

**해결**:

1. **Windows 버전 확인**
   ```powershell
   # PowerShell에서
   winver
   ```
   - Windows 10: Build 21H2 (19044) 이상
   - Windows 11: 모든 버전

2. **WSL2 업데이트**
   ```powershell
   # PowerShell (관리자 권한)
   wsl --update
   wsl --shutdown
   ```

3. **NVIDIA Driver 재설치**
   - 기존 드라이버 완전히 제거 (설정 → 앱)
   - 최신 드라이버 다운로드 및 설치
   - 컴퓨터 재시작

### 문제 3: "CUDA available: False" (WSL2 Python)

**원인**: PyTorch가 CPU 버전이거나 CUDA 버전 불일치

**해결**:
```bash
cd ~/sim_pip
bash setup_linux.sh
```

스크립트가 자동으로 CUDA PyTorch를 설치합니다.

### 문제 4: 드라이버 설치 후에도 GPU 인식 안 됨

**체크리스트**:

1. **컴퓨터 재시작** (필수!)
   
   드라이버 설치 후 반드시 재시작해야 함

2. **WSL 재시작**
   ```powershell
   # PowerShell
   wsl --shutdown
   ```
   
   그 후 다시 WSL 열기

3. **NVIDIA Control Panel 확인**
   
   Windows 작업 표시줄에서 NVIDIA 아이콘 우클릭 → "NVIDIA Control Panel"

4. **BIOS에서 GPU 활성화 확인**
   
   일부 노트북은 BIOS에서 dGPU(discrete GPU) 활성화 필요

## 📋 단계별 전체 프로세스

### 1단계: Windows에서 NVIDIA Driver 설치

```
1. https://www.nvidia.com/Download/index.aspx 접속
2. GPU 모델 선택 (RTX 4050 Laptop GPU)
3. 최신 드라이버 다운로드 (예: 535.xx 이상)
4. 설치 파일 실행
5. 설치 유형: "Express" 선택
6. 설치 완료
```

### 2단계: 컴퓨터 재시작

```
⚠️ 중요: 재시작하지 않으면 GPU가 작동하지 않습니다!
```

### 3단계: Windows에서 확인

```powershell
# PowerShell 열기
nvidia-smi

# 출력에 GPU 이름과 드라이버 버전이 보여야 함
```

### 4단계: WSL2에서 확인

```bash
# WSL2 터미널 열기
nvidia-smi

# Windows와 동일한 GPU 정보가 보여야 함
```

### 5단계: setup_linux.sh 실행 (WSL2)

```bash
cd ~/sim_pip
bash setup_linux.sh
```

스크립트가 자동으로:
- CUDA PyTorch 설치
- GPU 감지 및 확인
- 성공 메시지 표시

### 6단계: 최종 검증

```bash
conda activate SE3nv
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

**성공**: `CUDA: True`

## 🎉 성공 확인

모든 것이 올바르게 설치되면:

```bash
$ nvidia-smi
# GPU 정보 표시

$ conda activate SE3nv
$ python -c "import torch; print(torch.cuda.is_available())"
# True

$ cd ~/sim_pip
$ python scripts/test_phase1_2_3.py
# RFdiffusion이 GPU에서 빠르게 실행됨 (30초-2분)
```

## 📞 추가 도움

### NVIDIA 공식 WSL2 가이드

https://docs.nvidia.com/cuda/wsl-user-guide/index.html

### 권장 드라이버 버전

- **최소**: 470.76
- **권장**: 535.xx 이상
- **최신**: 545.xx+ (2024년 기준)

### 지원되는 GPU

- GeForce RTX 20/30/40 시리즈
- GeForce GTX 16 시리즈
- Quadro/Tesla (데이터센터)
- GeForce GTX 10 시리즈 (일부)

## ⚡ 빠른 요약

```
1. Windows에서 NVIDIA Driver 설치 (470.76+)
   → https://www.nvidia.com/Download/index.aspx

2. 컴퓨터 재시작 (필수!)

3. PowerShell에서 확인: nvidia-smi

4. WSL2에서 setup 실행: bash setup_linux.sh

5. GPU 확인: conda activate SE3nv && python -c "import torch; print(torch.cuda.is_available())"

6. 성공! 🎉
```

---

**다음 단계**: GPU가 활성화되면 `python scripts/test_phase1_2_3.py`를 실행하여 RFdiffusion을 테스트하세요!
