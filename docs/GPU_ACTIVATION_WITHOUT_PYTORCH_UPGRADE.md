# GPU 활성화 방법 (PyTorch 업그레이드 없이)

현재 SE3nv에는 PyTorch 1.9 + CUDA 11.1이 설치되어 있습니다.
GPU를 활성화하려면 **Windows에서 NVIDIA Driver만 설치**하면 됩니다.

## 🎯 GPU 활성화 단계

### 1단계: Windows에서 NVIDIA Driver 설치

**방법 1: 자동 다운로드 (가장 쉬움)**

1. 다음 링크를 브라우저에서 열기:
   ```
   https://www.nvidia.com/Download/index.aspx
   ```

2. GPU 정보 입력:
   - Product Type: `GeForce`
   - Product Series: `RTX 40 Series (Notebooks)`
   - Product: `GeForce RTX 4050 Laptop GPU`
   - Operating System: `Windows 11` (또는 Windows 10)
   - Download Type: `Game Ready Driver (GRD)`

3. "Search" 클릭 → "Download" 클릭

4. 다운로드한 파일 실행 (예: `535.xx-desktop-win11-64bit-international-whql.exe`)

5. 설치 옵션: `Express (권장)` 선택

6. 설치 완료 후 **컴퓨터 재시작** (필수!)

**방법 2: GeForce Experience (더 간편)**

1. GeForce Experience 다운로드:
   ```
   https://www.nvidia.com/geforce/geforce-experience/
   ```

2. 설치 후 실행 → "Drivers" 탭

3. "Check for updates" → 최신 드라이버 자동 설치

4. 설치 완료 후 **컴퓨터 재시작** (필수!)

### 2단계: 설치 확인 (Windows)

PowerShell 또는 CMD 열고:

```powershell
nvidia-smi
```

**예상 출력**:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx       Driver Version: 535.xx       CUDA Version: 12.2    |
|-------------------------------+----------------------+----------------------+
| GPU  Name                 TCC/WDDM | Bus-Id        Disp.A | Volatile Uncorr. ECC |
|===============================+======================+======================|
|   0  NVIDIA GeForce RTX 4050...  | 00000000:01:00.0 Off |                  N/A |
+-------------------------------+----------------------+----------------------+
```

중요:
- ✅ Driver Version: 470.76 이상이어야 함
- ✅ GPU 이름이 표시되어야 함

### 3단계: WSL2에서 확인

WSL2 터미널 열고:

```bash
nvidia-smi
```

Windows와 동일한 출력이 나와야 합니다.

### 4단계: Python에서 GPU 확인

```bash
conda activate SE3nv
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

**성공 출력**:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 4050 Laptop GPU
```

**실패 출력** (드라이버 없음):
```
CUDA available: False
GPU: N/A
```

## 🔧 문제 해결

### 문제 1: "CUDA available: False"

**원인 1: 컴퓨터를 재시작하지 않음**
```
해결: Windows 재시작
```

**원인 2: 드라이버가 너무 오래됨**
```
해결: 드라이버 470.76 이상으로 업데이트
```

**원인 3: WSL2가 GPU를 인식하지 못함**
```
해결:
# PowerShell (관리자)
wsl --update
wsl --shutdown

# 그 후 WSL 다시 열기
```

### 문제 2: "nvidia-smi: command not found" (Windows)

**원인**: NVIDIA Driver가 설치되지 않음

**해결**: 위의 1단계 다시 실행

### 문제 3: "GPU access blocked by the operating system" (WSL2)

**원인**: WSL2 버전이 오래됨

**해결**:
```powershell
# PowerShell (관리자)
wsl --update
wsl --version  # WSL 버전 확인 (2.0.0 이상 권장)
```

## 📋 완전한 설치 프로세스

```
1. Windows에서 NVIDIA Driver 설치 (470.76+)
   ↓
2. 컴퓨터 재시작 (필수!)
   ↓
3. PowerShell에서 확인: nvidia-smi
   ↓
4. WSL2 열고 확인: nvidia-smi
   ↓
5. Python 확인:
   conda activate SE3nv
   python -c "import torch; print(torch.cuda.is_available())"
   ↓
6. 성공! RFdiffusion 사용 가능
```

## ⚡ 빠른 체크리스트

- [ ] Windows NVIDIA Driver 설치 (https://www.nvidia.com/Download/index.aspx)
- [ ] 컴퓨터 재시작
- [ ] Windows에서 `nvidia-smi` 실행 → GPU 이름 보임
- [ ] WSL2에서 `nvidia-smi` 실행 → GPU 이름 보임
- [ ] SE3nv에서 `python -c "import torch; print(torch.cuda.is_available())"` → `True`
- [ ] 완료! 🎉

## 💡 중요 포인트

1. **PyTorch 업그레이드 불필요**
   - PyTorch 1.9 + CUDA 11.1로 충분함
   - NVIDIA Driver만 설치하면 GPU 작동

2. **컴퓨터 재시작 필수**
   - 드라이버 설치 후 반드시 재시작
   - 재시작하지 않으면 GPU 인식 안 됨

3. **WSL2 업데이트 권장**
   ```powershell
   wsl --update
   ```

4. **드라이버 버전**
   - 최소: 470.76
   - 권장: 535.xx 이상

## 🎯 예상 결과

### GPU 활성화 전
```bash
$ python -c "import torch; print(torch.cuda.is_available())"
False

$ python scripts/test_phase1_2_3.py
# RFdiffusion이 CPU에서 실행 (매우 느림, 크래시 가능)
```

### GPU 활성화 후
```bash
$ python -c "import torch; print(torch.cuda.is_available())"
True

$ python scripts/test_phase1_2_3.py
# RFdiffusion이 GPU에서 빠르게 실행! (30초-2분)
```

---

**다음 단계**: NVIDIA Driver를 설치하고 컴퓨터를 재시작한 후, WSL2에서 `nvidia-smi`를 실행하여 GPU가 보이는지 확인하세요!

**추가 도움**: Windows Driver 설치 상세 가이드는 `docs/WINDOWS_NVIDIA_DRIVER_INSTALL.md` 참조
