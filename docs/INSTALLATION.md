# Installation Guide

## Python Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install local packages (editable mode)
pip install -e ./chai-1
pip install -e ./boltz  # Optional, for Boltz support
```

## System Dependencies

### kalign (Required for Chai-1 templates)

kalign은 Chai-1이 템플릿 서버를 사용할 때 필요합니다.

#### Option 1: Conda (권장)
```bash
conda install -c bioconda kalign
```

#### Option 2: From Source
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential

# Download and install kalign
wget https://github.com/TimoLassmann/kalign/archive/refs/tags/v3.3.5.tar.gz
tar -xzf v3.3.5.tar.gz
cd kalign-3.3.5
mkdir build && cd build
cmake ..
make
sudo make install

# Verify installation
kalign --version
```

#### Option 3: 템플릿 서버 비활성화 (kalign 불필요)

kalign 설치가 어려운 경우, config에서 템플릿 서버를 비활성화할 수 있습니다:

```python
# pipeline/config.py
"phase3_fast": {
    "chai": {
        "command_template": "chai-lab fold --use-msa-server {input_path} {output_dir}",
        # --use-templates-server 제거
    }
}
```

### DockQ (Required for Phase 3)

```bash
pip install DockQ
# 또는
pip install git+https://github.com/bjornwallner/DockQ.git
```

## Boltz 전용 가상환경 (Optional)

Boltz를 사용하려면 별도 가상환경을 만드는 것을 권장합니다 (의존성 충돌 방지):

```bash
# Boltz 전용 venv 생성
python -m venv /path/to/boltz_venv
source /path/to/boltz_venv/bin/activate

# Boltz 설치
pip install -e ./boltz

# Config에서 venv 경로 설정
# pipeline/config.py
"boltz": {
    "enabled": True,
    "venv_path": "/path/to/boltz_venv"
}
```

## Verification

```bash
# Chai-1 확인
chai-lab --help

# Boltz 확인 (별도 venv에서)
boltz --help

# kalign 확인
kalign --version

# DockQ 확인
DockQ --help
```

## Troubleshooting

### kalign not found
```bash
# PATH 확인
which kalign

# PATH에 추가 (필요시)
export PATH="/usr/local/bin:$PATH"
```

### Chai-1 torch version conflict
현재 설정은 torch>=2.3.1을 사용합니다. 충돌 시:
```bash
pip install --upgrade torch>=2.3.1,<2.7
```

### Boltz import error
Boltz는 별도 가상환경 사용을 권장합니다.
