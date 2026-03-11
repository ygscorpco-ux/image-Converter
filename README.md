# LOGOPLANET PNG Generator

원본 PNG 로고 1개를 넣으면 투명 배경, 흑백, 반전, 색상 변형, 용도별 리사이즈 PNG를 폴더 구조까지 포함해 자동으로 생성하는 프로그램입니다.

현재 메인 버전은 `PySide6` 기반 `V2`입니다.  
기존 `Tkinter` 기반 `V1` 코드는 fallback과 비교용으로 함께 남겨두었습니다.

## 실행 방법

### V2 실행

```bash
python main_v2.py
```

### V1 실행

```bash
python main.py
```

## 필요 패키지

```bash
pip install pillow pyside6
```

## 주요 기능

- 원본 PNG 1개 선택
- 프로그램 창 전체 드래그앤드롭으로 PNG 첨부
- 출력 폴더 선택
- 저장 기준 이름 입력
- 사용자 지정 HEX 색상 입력
- 투명 배경 / 흑백 / 반전 / 색상 변형 자동 생성
- 인쇄 / 배달앱 / 네이버 / 인스타그램 / 웹사이트 / 목업 폴더 구조 자동 생성
- 용도별 사이즈 자동 저장
- 원하는 범위만 선택 생성
- 비동기 생성과 실행 로그 표시
- 최근 입력값과 선택 범위 저장

## 프로젝트 구조

- `main_v2.py`: PySide6 기반 V2 실행 진입점
- `v2_app/`: V2 UI, 테마, 워커, 설정 저장 로직
- `logo_engine.py`: 공용 이미지 처리 및 파일 생성 엔진
- `main.py`: 기존 Tkinter 기반 V1 실행 진입점
- `app_ui.py`: V1 UI 코드
- `assets/`: 아이콘과 브랜드 자산

## 빌드

### V2 onedir 빌드

```bash
build_v2.bat
```

또는

```bash
python -m PyInstaller --noconfirm .\PNG_Logo_Auto_Generator_V2.spec
```

## 참고

- 현재 기준 추천 실행 버전은 `V2`입니다.
- 큰 PNG에서도 배경 제거 속도를 개선했고, 실사용 기준 품질과 속도를 함께 다듬은 상태입니다.
- 저장소에는 개발 산출물과 임시 검증 폴더를 포함하지 않습니다.
