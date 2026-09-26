@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== 요리왕 실행 =====

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] 가상환경 만드는 중...
  where py >nul 2>nul && (py -m venv .venv) || (python -m venv .venv)
  if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [오류] Python을 찾을 수 없어요. https://www.python.org 에서 설치하고
    echo        설치 화면의 "Add python.exe to PATH"를 꼭 체크하세요.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat"

echo [2/4] 필요한 패키지 설치 확인 중... (처음엔 1~2분 걸려요)
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [오류] 패키지 설치에 실패했어요. 인터넷 연결을 확인해 주세요.
  pause
  exit /b 1
)

if not exist ".env" copy ".env.example" ".env" >nul

echo [3/4] 기본 데이터 준비 중...
python -m app.seed

echo [4/4] 서버 시작! 잠시 후 브라우저가 열려요. (끄려면 이 창에서 Ctrl+C)
start "" cmd /c "timeout /t 3 >nul & start http://localhost:8000"
python -m uvicorn app.main:app --port 8000
pause
