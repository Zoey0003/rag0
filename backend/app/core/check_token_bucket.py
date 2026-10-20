import time
from uuid import uuid4

from fastapi import HTTPException

from app.core.rate_limit import check_token_bucket


identity = f"test-{uuid4().hex}"


def request_once(label: str):
    try:
        check_token_bucket(
            scope="bucket_test",
            identity=identity,
            capacity=2,
            refill_seconds=3,
        )
        print(label, "通过")
    except HTTPException as exc:
        print(label, exc.status_code, exc.headers)


request_once("第1次")
request_once("第2次")
request_once("第3次")

print("等待3.2秒，补充一个令牌……")
time.sleep(3.2)

request_once("第4次")
request_once("第5次")