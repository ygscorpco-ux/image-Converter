# LOGOPLANET PNG Generator

원본 PNG 로고 1개를 넣으면, 용도별 폴더 구조까지 포함한 PNG 파생본을 한 번에 생성하는 Windows용 프로그램입니다.

## 주요 기능

- 원본 PNG 1개 선택
- 창 어디든 드래그 앤 드롭으로 PNG 첨부
- 출력 폴더 선택
- 저장 기준 이름 직접 입력
- 사용자 지정 HEX 색상 입력
- 투명 배경 / 흑백 / 반전 / 색상변형 자동 생성
- 인쇄 / 배달앱 / 네이버 / 인스타그램 / 웹사이트 / 목업용 폴더 구조 자동 생성
- 필요한 용도만 골라서 선택 생성
- 생성 결과 요약 및 실행 로그 표시

## 배포용 실행 파일

배포용 독립 실행 파일은 아래 경로에 포함됩니다.

- `release/LOGOPLANET PNG 생성기.exe`

이 파일은 다른 PC로 옮겨도 바로 실행할 수 있는 standalone exe입니다.

## 실행 방법

### 1. exe로 바로 실행

1. `release/LOGOPLANET PNG 생성기.exe`를 실행합니다.
2. 원본 PNG를 선택하거나 창 아무 곳에 드래그해서 놓습니다.
3. 출력 폴더를 선택합니다.
4. 저장 기준 이름과 사용자 색상을 입력합니다.
5. 필요한 생성 범위를 선택합니다.
6. `PNG 자동 생성` 버튼을 누릅니다.

### 2. Python으로 실행

필요 패키지:

- Python 3.11 이상 권장
- Pillow
- tkinterdnd2

설치:

```bash
pip install pillow tkinterdnd2
```

실행:

```bash
python main.py
```

## 생성되는 대표 결과

- 원본 복사 PNG
- 투명 배경 PNG
- 검정 / 흰색 / 회색조 PNG
- 반전 PNG
- 고정 색상 변형 PNG
- 사용자 지정 색상 PNG
- 플랫폼/용도별 리사이즈 PNG

## 폴더 구조 예시

```text
브랜드명/
├─ 00_원본/
├─ 01_인쇄/
├─ 02_배달앱/
├─ 03_네이버/
├─ 04_인스타그램/
├─ 05_웹사이트/
└─ 06_목업/
```

실사용 폴더 안에는 아래 하위 폴더가 자동 생성됩니다.

- 투명배경
- 흑백
- 반전
- 색상변형

## 프로젝트 구성

- `main.py` : 메인 GUI 및 이미지 생성 로직
- `assets/` : 프로그램 아이콘 및 브랜드 에셋
- `build_exe.bat` : 배포용 exe 빌드 스크립트
- `latest_launcher.py` : 개발 환경에서 최신 `main.py`를 직접 실행하는 런처
- `개발계획서.md` : 개발 계획 및 폴더/사이즈 기준 문서
- `기획서.md` : 기술 기획 문서

## 배포용 exe 다시 만들기

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "LOGOPLANET PNG 생성기" --distpath "release" --workpath "build_release" --specpath "." --icon "assets/app_icon.ico" --add-data "assets/app_icon.png;assets" --add-data "assets/app_icon.ico;assets" --add-data "assets/logoplanet_mark.png;assets" --add-data "assets/logoplanet_mark_soft.png;assets" main.py
```

## 참고

- `latest_launcher.py`로 만든 exe는 개발자 로컬 경로를 참조하므로 배포용으로 사용하지 않습니다.
- 다른 사용자에게 전달할 때는 반드시 `release/LOGOPLANET PNG 생성기.exe`를 사용하세요.
