import json
import logging
from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import UserResponse
from app.dependencies import get_validated_sub

MAX_DEVICES_PER_USER = 3  # или как у тебя задано

logger = logging.getLogger("hwid")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def hwid_check(
    hwid: str | None = Header(default=None, alias="x-hwid"),
    os: str | None = Header(default=None, alias="x-ver-os"),
    model: str | None = Header(default=None, alias="x-device-model"),
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_sub)
):
    """
    Проверяет HWID и обновляет hwid_device_list в БД.
    Если HWID отсутствует — логирует и возвращает None.
    """
    client_ip = "unknown"  # можно взять request.client.host через Request, если нужно
    if not hwid:
        logger.info(f"No HWID provided for user {dbuser.username}")
        return None

    logger.info(f"Received HWID {hwid} for user {dbuser.username}")

    hwid_list = json.loads(dbuser.hwid_device_list) if dbuser.hwid_device_list else []

    # Обновляем существующее устройство
    for d in hwid_list:
        if d["hwid"] == hwid:
            d["os"] = os
            d["model"] = model
            dbuser.hwid_device_list = json.dumps(hwid_list)
            db.commit()
            return hwid

    # Добавляем новое устройство
    if len(hwid_list) >= MAX_DEVICES_PER_USER:
        logger.warning(f"User {dbuser.username} exceeded device limit")
        raise HTTPException(status_code=403, detail="Device limit exceeded")

    hwid_list.append({"hwid": hwid, "os": os, "model": model})
    logger.info(hwid_list)
    dbuser.hwid_device_list = json.dumps(hwid_list)
    db.commit()
    return hwid
