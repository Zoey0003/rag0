from uuid import uuid4

from fastapi import HTTPException

from app.core.rate_limit import check_rate_limit


# 每次测试使用不同身份，不影响真实登录计数。
identity = f"test-{uuid4()}"

for number in range(1, 5):
    try:
        check_rate_limit(
            scope="test",
            identity=identity,
            limit=3,
            window_seconds=10,
        )
        print(number, "通过")
    except HTTPException as exc:
        print(number, exc.status_code, exc.headers)

from uuid import uuid4

test_id = uuid4().hex

for user in ("user_a", "user_b"):
    for number in range(1, 4):
        try:
            check_rate_limit(
                scope="ask_test",
                identity=f"{test_id}:{user}",
                limit=2,
                window_seconds=10,
            )
            print(user, number, "通过")
        except HTTPException as exc:
            print(user, number, exc.status_code)