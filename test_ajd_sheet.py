"""아정당 크롤링 + 구글 시트 기록 검증"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

import app

# 브라우저 창 없이 빠르게 테스트
app.HEADLESS = True

print("=" * 50)
print("1) 크롤링 실행")
print("=" * 50)
app.run()

print("\n" + "=" * 50)
print("2) 구글 시트 최근 5행 확인")
print("=" * 50)

ws = app.get_worksheet()
rows = ws.get_all_values()
print(f"시트 탭: {ws.title}")
print(f"총 행 수: {len(rows)}")

headers = app.SHEET_HEADERS
print(f"\n헤더(기대): {headers}")
if rows:
    print(f"헤더(실제 1행): {rows[0]}")

print("\n--- 최근 5행 ---")
for row in rows[-5:]:
    print(row)

# 마지막 행 검증
if len(rows) < 2:
    print("\n[실패] 데이터 행이 없습니다.")
    sys.exit(1)

last = rows[-1]
expected_cols = 7
ok = True

if len(last) < expected_cols:
    print(f"\n[실패] 열 개수 부족: {len(last)} / {expected_cols}")
    ok = False

checks = [
    ("수집 일시", 0, lambda v: bool(v) and "-" in v and ":" in v),
    ("타겟사이트명", 1, lambda v: "아정당" in v),
    ("통신사명", 2, lambda v: v == "SK"),
    ("인터넷 상품명", 3, lambda v: "500" in v),
    ("TV상품명", 4, lambda v: "Btv" in v and "스탠다드" in v),
    ("기본 요금", 5, lambda v: bool(v) and ("원" in v or "," in v)),
    ("사은품 액수", 6, lambda v: bool(v) and ("만원" in v or "원" in v)),
]

print("\n--- 마지막 행 항목별 검증 ---")
for name, idx, fn in checks:
    value = last[idx] if idx < len(last) else ""
    passed = fn(value)
    status = "OK" if passed else "FAIL"
    print(f"  [{status}] {name}: {value!r}")
    if not passed:
        ok = False

print("\n" + ("[전체 통과] 아정당 데이터가 시트에 정상 기록되었습니다." if ok else "[일부 실패] 위 FAIL 항목을 확인하세요."))
sys.exit(0 if ok else 1)
