import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import hash_password

logger = logging.getLogger(__name__)

USERS = [
    {
        "name": "Administrador",
        "email": "admin@gcfinder.com",
        "password": "admin123",
        "role": "admin",
    },
    {
        "name": "Editor Padrão",
        "email": "editor@gcfinder.com",
        "password": "editor123",
        "role": "editor",
    },
]


async def seed_users(db: AsyncSession) -> None:
    """Cria usuários iniciais de forma idempotente."""
    for user_data in USERS:
        result = await db.execute(
            select(User).where(User.email == user_data["email"])
        )
        if result.scalar_one_or_none() is not None:
            logger.info(f"Usuário '{user_data['email']}' já existe, pulando.")
            continue

        user = User(
            name=user_data["name"],
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            role=user_data["role"],
        )
        db.add(user)
        logger.info(f"Usuário '{user_data['email']}' criado com sucesso.")

    await db.commit()
