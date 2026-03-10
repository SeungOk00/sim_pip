#!/bin/bash
# RFdiffusion 단독 실행 테스트 (최종 버전)

echo "=========================================="
echo "RFdiffusion 실행 테스트"
echo "=========================================="
echo ""

# 테스트 디렉토리
TEST_DIR="/home01/hpc194a02/test/sim_pip/test_rfdiffusion"
mkdir -p $TEST_DIR/outputs
cd $TEST_DIR

# 1. 타겟 다운로드
if [ ! -f "target.pdb" ]; then
    echo "[1/4] 테스트 타겟 다운로드 중..."
    wget -q https://files.rcsb.org/download/4IBM.pdb -O target.pdb
    echo "      ✓ target.pdb 다운로드 완료"
else
    echo "[1/4] ✓ target.pdb 이미 존재"
fi
echo ""

# 2. RFdiffusion 경로 확인
RFDIFFUSION="/home01/hpc194a02/test/sim_pip/RFdiffusion"
if [ ! -d "$RFDIFFUSION" ]; then
    echo "✗ RFdiffusion 디렉토리 없음: $RFDIFFUSION"
    exit 1
fi
echo "[2/4] ✓ RFdiffusion 경로 확인"
echo ""

# 3. 모델 다운로드 확인
echo "[3/4] 모델 가중치 확인..."
if [ ! -d "$RFDIFFUSION/models" ]; then
    echo "      모델 디렉토리 생성..."
    mkdir -p $RFDIFFUSION/models
fi

if [ ! -f "$RFDIFFUSION/models/Complex_base_ckpt.pt" ]; then
    echo "      ⚠ 모델 없음. 다운로드가 필요합니다."
    echo ""
    echo "      다음 명령어를 실행하세요:"
    echo "      cd $RFDIFFUSION"
    echo "      mkdir -p models && cd models"
    echo "      wget http://files.ipd.uw.edu/pub/RFdiffusion/e29311f6f1bf1af907f9ef9f44b8328b/Complex_base_ckpt.pt"
    echo ""
    echo "      또는 전체 모델:"
    echo "      bash $RFDIFFUSION/scripts/download_models.sh $RFDIFFUSION/models"
    echo ""
    exit 1
else
    echo "      ✓ Complex_base_ckpt.pt 존재"
fi
echo ""

# 4. 실행 스크립트 생성
echo "[4/4] 실행 스크립트 생성..."

cat > run_test.sh << 'SCRIPT_EOF'
#!/bin/bash
# RFdiffusion 실행

# Conda 초기화 (환경에 맞게 수정)
# 일반적인 conda 경로들을 시도
for CONDA_SH in \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "/opt/anaconda3/etc/profile.d/conda.sh" \
    "/opt/miniconda3/etc/profile.d/conda.sh"
do
    if [ -f "$CONDA_SH" ]; then
        source "$CONDA_SH"
        break
    fi
done

# SE3nv 환경 활성화
if conda env list 2>/dev/null | grep -q "SE3nv"; then
    conda activate SE3nv
    echo "✓ SE3nv 환경 활성화됨"
else
    echo "⚠ SE3nv 환경 없음. 기본 Python 사용"
fi

cd /home01/hpc194a02/test/sim_pip/test_rfdiffusion

echo ""
echo "=========================================="
echo "RFdiffusion 실행 시작"
echo "=========================================="
echo ""
echo "설정:"
echo "  타겟: target.pdb (인슐린 수용체)"
echo "  타겟 체인: A (잔기 1-150)"
echo "  바인더 길이: 80 aa"
echo "  핫스팟: A59, A83, A91"
echo "  디자인 수: 2개"
echo "  디퓨전 스텝: 50"
echo ""

python /home01/hpc194a02/test/sim_pip/RFdiffusion/scripts/run_inference.py \
  inference.input_pdb=target.pdb \
  inference.output_prefix=outputs/binder \
  inference.num_designs=2 \
  'contigmap.contigs=[A1-150/0 80-80]' \
  'ppi.hotspot_res=[A59,A83,A91]' \
  diffuser.T=50 \
  denoiser.noise_scale_ca=0 \
  denoiser.noise_scale_frame=0

EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ 실행 완료!"
    echo "=========================================="
    echo ""
    echo "생성된 파일:"
    ls -lh outputs/ 2>/dev/null || echo "파일 없음"
else
    echo "✗ 실행 실패 (exit code: $EXIT_CODE)"
    echo "=========================================="
fi
SCRIPT_EOF

chmod +x run_test.sh

echo "      ✓ run_test.sh 생성 완료"
echo ""

echo "=========================================="
echo "준비 완료!"
echo "=========================================="
echo ""
echo "다음 명령어로 실행하세요:"
echo ""
echo "  cd $TEST_DIR"
echo "  ./run_test.sh"
echo ""
echo "또는:"
echo ""
echo "  cd $TEST_DIR"
echo "  bash run_test.sh"
echo ""
