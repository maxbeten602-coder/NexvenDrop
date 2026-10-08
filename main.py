from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

from backend.database import get_db, init_db
from backend.models import User, InventoryItem, Transaction, CaseOpen, GameHistory
from backend.cases import CASES, get_case, roll_prize

app = FastAPI(title="Nexven Drops API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW_STARS", "100"))
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "8133917568,5198310704").split(",") if x.strip()]


def validate_telegram_init_data(init_data: str) -> dict:
    if not BOT_TOKEN:
        try:
            data = dict(parse_qsl(init_data))
            user = json.loads(data.get("user", "{}"))
            return user
        except:
            return {}
    try:
        data = dict(parse_qsl(init_data))
        received_hash = data.pop("hash", "")
        data_check_arr = [f"{k}={v}" for k, v in sorted(data.items())]
        data_check_string = "\n".join(data_check_arr)
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != received_hash:
            return {}
        user = json.loads(data.get("user", "{}"))
        return user
    except Exception:
        return {}


async def get_or_create_user(db: AsyncSession, tg_user: dict) -> User:
    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Invalid user data")
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            photo_url=tg_user.get("photo_url"),
            balance_ton=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.username = tg_user.get("username") or user.username
        user.first_name = tg_user.get("first_name") or user.first_name
        user.last_name = tg_user.get("last_name") or user.last_name
        user.photo_url = tg_user.get("photo_url") or user.photo_url
        user.last_active = datetime.utcnow()
        await db.commit()
    return user


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


class AuthRequest(BaseModel):
    initData: str

class OpenCaseRequest(BaseModel):
    initData: str
    case_id: str

class GameBetRequest(BaseModel):
    initData: str
    game_type: str
    bet_amount: int
    choice: Optional[str] = None
    target: Optional[float] = None

class DepositRequest(BaseModel):
    initData: str
    amount: int
    method: str

class WithdrawRequest(BaseModel):
    initData: str
    amount: int

class AdminAction(BaseModel):
    initData: str
    action: str
    target_telegram_id: Optional[int] = None
    amount: Optional[int] = None
    tx_id: Optional[int] = None


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {"app": "Nexven Drops", "version": "1.1.0", "status": "ok"}


@app.post("/api/auth")
async def auth(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(req.initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    can_free = True
    free_cooldown = None
    if user.last_free_case:
        next_free = user.last_free_case + timedelta(hours=24)
        if datetime.utcnow() < next_free:
            can_free = False
            free_cooldown = int((next_free - datetime.utcnow()).total_seconds())
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "photo_url": user.photo_url,
            "balance_ton": user.balance_ton,
            "balance_ton": user.balance_ton,
            "is_admin": is_admin(user.telegram_id),
            "can_free_case": can_free,
            "free_cooldown_sec": free_cooldown,
        }
    }


@app.get("/api/profile")
async def profile(initData: str, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "photo_url": user.photo_url,
            "balance_ton": user.balance_ton,
            "balance_ton": user.balance_ton,
            "total_deposited": user.total_deposited,
            "total_withdrawn": user.total_withdrawn,
            "is_admin": is_admin(user.telegram_id),
        }
    }


@app.get("/api/cases")
async def get_cases():
    return {
        "ok": True,
        "cases": [
            {
                "id": c["id"],
                "name": c["name"],
                "price_ton": c["price_ton"],
                "description": c["description"],
                "image": c["image"],
                "prizes_count": len(c["prizes"]),
            }
            for c in CASES.values()
        ]
    }


@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"ok": True, "case": case}


@app.post("/api/open-case")
async def open_case(req: OpenCaseRequest, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(req.initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Кейс не найден")
    price = case["price_ton"]
    if req.case_id == "free":
        if user.last_free_case:
            next_free = user.last_free_case + timedelta(hours=24)
            if datetime.utcnow() < next_free:
                remaining = int((next_free - datetime.utcnow()).total_seconds())
                hours = remaining // 3600
                mins = (remaining % 3600) // 60
                raise HTTPException(status_code=400, detail=f"Фри кейс доступен через {hours}ч {mins}м")
        user.last_free_case = datetime.utcnow()
    else:
        if user.balance_ton < price:
            raise HTTPException(status_code=400, detail="Недостаточно звёзд")
        user.balance_ton -= price
    prize = roll_prize(req.case_id)
    item = InventoryItem(
        user_id=user.id,
        gift_id=prize["id"],
        gift_name=prize["name"],
        gift_type=prize["type"],
        gift_image=prize.get("image"),
        gift_value_ton=prize["value"],
        is_nft=prize.get("is_nft", False),
        obtained_from=f"case_{req.case_id}",
    )
    db.add(item)
    open_log = CaseOpen(
        user_id=user.id,
        case_type=req.case_id,
        cost_ton=price,
        prize_gift_id=prize["id"],
        prize_name=prize["name"],
        prize_value=prize["value"],
    )
    db.add(open_log)
    tx = Transaction(
        user_id=user.id,
        type="open_case",
        amount_ton=-price if price > 0 else 0,
        description=f"Открытие кейса {case['name']} → {prize['name']}",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    can_free = True
    free_cooldown = None
    if user.last_free_case:
        next_free = user.last_free_case + timedelta(hours=24)
        if datetime.utcnow() < next_free:
            can_free = False
            free_cooldown = int((next_free - datetime.utcnow()).total_seconds())
    return {
        "ok": True,
        "prize": prize,
        "new_balance": user.balance_ton,
        "item_id": item.id,
        "can_free_case": can_free,
        "free_cooldown_sec": free_cooldown,
    }


@app.get("/api/inventory")
async def get_inventory(initData: str = Query(...), db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.id, InventoryItem.is_withdrawn == False)
        .order_by(InventoryItem.obtained_at.desc())
    )
    items = result.scalars().all()
    return {
        "ok": True,
        "items": [
            {
                "id": i.id,
                "gift_id": i.gift_id,
                "name": i.gift_name,
                "type": i.gift_type,
                "image": i.gift_image,
                "value": i.gift_value_ton,
                "is_nft": i.is_nft,
                "from": i.obtained_from,
                "date": i.obtained_at.isoformat() if i.obtained_at else None,
            }
            for i in items
        ]
    }


@app.post("/api/game/bet")
async def place_bet(req: GameBetRequest, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(req.initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    if req.bet_amount <= 0:
        raise HTTPException(status_code=400, detail="Ставка должна быть > 0")
    if user.balance_ton < req.bet_amount:
        raise HTTPException(status_code=400, detail="Недостаточно звёзд")
    import random
    win_amount = 0
    multiplier = 0.0
    result_str = ""
    if req.game_type == "roulette":
        number = random.randint(0, 14)
        color = "green" if number == 0 else ("red" if 1 <= number <= 7 else "black")
        choice = (req.choice or "").lower()
        if choice == color:
            multiplier = 14.0 if color == "green" else 2.0
            win_amount = int(req.bet_amount * multiplier)
            result_str = f"Выпало {number} ({color}) — WIN x{multiplier}"
        else:
            result_str = f"Выпало {number} ({color}) — LOSE"
    elif req.game_type == "upgrade":
        target = req.target or (req.bet_amount * 2)
        chance = min(95.0, (req.bet_amount / target) * 100)
        roll = random.uniform(0, 100)
        if roll <= chance:
            multiplier = target / req.bet_amount
            win_amount = int(target)
            result_str = f"Апгрейд успешен! x{multiplier:.2f}"
        else:
            result_str = f"Апгрейд провален (шанс был {chance:.1f}%)"
    elif req.game_type == "crash":
        r = random.random()
        if r < 0.04:
            crash_point = 1.00
        else:
            crash_point = round(max(1.01, 0.99 / (1 - r)), 2)
            crash_point = min(crash_point, 50.0)
        cashout = req.target or 1.5
        if cashout <= crash_point:
            multiplier = cashout
            win_amount = int(req.bet_amount * multiplier)
            result_str = f"Crash @ {crash_point}x | Вышел @ {cashout}x — WIN"
        else:
            result_str = f"Crash @ {crash_point}x | Не успел (цель {cashout}x) — LOSE"
    else:
        raise HTTPException(status_code=400, detail="Unknown game type")
    user.balance_ton -= req.bet_amount
    if win_amount > 0:
        user.balance_ton += win_amount
    history = GameHistory(
        user_id=user.id,
        game_type=req.game_type,
        bet_amount=req.bet_amount,
        result=result_str,
        win_amount=win_amount,
        multiplier=multiplier,
    )
    db.add(history)
    tx = Transaction(
        user_id=user.id,
        type="game_win" if win_amount > 0 else "game_bet",
        amount_ton=win_amount - req.bet_amount,
        description=f"{req.game_type}: {result_str}",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    return {
        "ok": True,
        "result": result_str,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "new_balance": user.balance_ton,
        "net": win_amount - req.bet_amount,
    }


@app.post("/api/deposit")
async def deposit(req: DepositRequest, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(req.initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    if req.amount < 10:
        raise HTTPException(status_code=400, detail="Минимум 10")
    if req.method not in ("ton", "ton"):
        raise HTTPException(status_code=400, detail="method: ton или ton")
    tx = Transaction(
        user_id=user.id,
        type="deposit",
        amount_ton=req.amount if req.method == "ton" else 0,
        amount_ton=round(req.amount / 100, 2) if req.method == "ton" else 0.0,
        description=f"Пополнение {req.method.upper()}: {req.amount}",
        status="pending",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    if req.method == "ton":
        user.balance_ton += req.amount
        user.total_deposited += req.amount
        tx.status = "completed"
        await db.commit()
        await db.refresh(user)
        return {
            "ok": True,
            "message": f"Баланс пополнен на {req.amount} ⭐",
            "new_balance": user.balance_ton,
            "tx_id": tx.id,
            "demo": True,
        }
    return {
        "ok": True,
        "message": "Отправьте TON на адрес. После подтверждения баланс обновится.",
        "ton_address": "UQBdemo_replace_with_real_wallet",
        "amount_ton": round(req.amount / 100, 2),
        "tx_id": tx.id,
        "status": "pending",
    }


@app.post("/api/withdraw")
async def request_withdraw(req: WithdrawRequest, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(req.initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    user = await get_or_create_user(db, tg_user)
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    if req.amount < MIN_WITHDRAW:
        raise HTTPException(status_code=400, detail=f"Минимум для вывода: {MIN_WITHDRAW} ⭐")
    if user.balance_ton < req.amount:
        raise HTTPException(status_code=400, detail="Недостаточно звёзд")
    user.balance_ton -= req.amount
    tx = Transaction(
        user_id=user.id,
        type="withdraw",
        amount_ton=-req.amount,
        description=f"Заявка на вывод {req.amount} ⭐",
        status="pending",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    return {
        "ok": True,
        "message": f"Заявка на вывод {req.amount} ⭐ создана. Ожидайте обработки.",
        "new_balance": user.balance_ton,
        "tx_id": tx.id,
    }


@app.post("/api/admin")
async def admin_action(req: AdminAction, db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(req.initData)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    if not is_admin(tg_user.get("id", 0)):
        raise HTTPException(status_code=403, detail="Нет доступа")
    if req.action == "give_ton":
        if not req.target_telegram_id or not req.amount:
            raise HTTPException(status_code=400, detail="Нужны target_telegram_id и amount")
        result = await db.execute(select(User).where(User.telegram_id == req.target_telegram_id))
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        target.balance_ton += req.amount
        target.total_deposited += req.amount
        tx = Transaction(
            user_id=target.id,
            type="deposit",
            amount_ton=req.amount,
            description=f"Админ начислил {req.amount} ⭐",
            status="completed",
        )
        db.add(tx)
        await db.commit()
        return {"ok": True, "message": f"Начислено {req.amount} ⭐ пользователю {req.target_telegram_id}"}
    elif req.action == "ban":
        result = await db.execute(select(User).where(User.telegram_id == req.target_telegram_id))
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        target.is_banned = True
        await db.commit()
        return {"ok": True, "message": f"Пользователь {req.target_telegram_id} забанен"}
    elif req.action == "unban":
        result = await db.execute(select(User).where(User.telegram_id == req.target_telegram_id))
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        target.is_banned = False
        await db.commit()
        return {"ok": True, "message": f"Пользователь {req.target_telegram_id} разбанен"}
    elif req.action == "approve_withdraw":
        if not req.tx_id:
            raise HTTPException(status_code=400, detail="Нужен tx_id")
        result = await db.execute(select(Transaction).where(Transaction.id == req.tx_id))
        tx = result.scalar_one_or_none()
        if not tx or tx.type != "withdraw":
            raise HTTPException(status_code=404, detail="Транзакция не найдена")
        tx.status = "completed"
        result2 = await db.execute(select(User).where(User.id == tx.user_id))
        u = result2.scalar_one_or_none()
        if u:
            u.total_withdrawn += abs(tx.amount_ton)
        await db.commit()
        return {"ok": True, "message": f"Вывод #{req.tx_id} подтверждён"}
    elif req.action == "stats":
        users_count = (await db.execute(select(func.count(User.id)))).scalar()
        total_ton = (await db.execute(select(func.sum(User.balance_ton)))).scalar() or 0
        opens = (await db.execute(select(func.count(CaseOpen.id)))).scalar()
        pending_wd = (await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.type == "withdraw", Transaction.status == "pending"
            )
        )).scalar()
        return {
            "ok": True,
            "stats": {
                "users": users_count,
                "total_balance_ton": total_ton,
                "case_opens": opens,
                "pending_withdraws": pending_wd,
            }
        }
    else:
        raise HTTPException(status_code=400, detail="Unknown action")


@app.get("/api/admin/pending-withdraws")
async def admin_pending(initData: str = Query(...), db: AsyncSession = Depends(get_db)):
    tg_user = validate_telegram_init_data(initData)
    if not tg_user or not is_admin(tg_user.get("id", 0)):
        raise HTTPException(status_code=403, detail="Нет доступа")
    result = await db.execute(
        select(Transaction)
        .where(Transaction.type == "withdraw", Transaction.status == "pending")
        .order_by(desc(Transaction.created_at))
        .limit(50)
    )
    txs = result.scalars().all()
    items = []
    for tx in txs:
        u = (await db.execute(select(User).where(User.id == tx.user_id))).scalar_one_or_none()
        items.append({
            "tx_id": tx.id,
            "telegram_id": u.telegram_id if u else None,
            "username": u.username if u else None,
            "amount": abs(tx.amount_ton),
            "date": tx.created_at.isoformat() if tx.created_at else None,
        })
    return {"ok": True, "pending": items}
