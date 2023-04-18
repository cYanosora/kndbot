from fastapi import HTTPException, status


auth_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="非法验证",
)

request_error = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="参数非法",
)