from sqlalchemy import select
from app.auth_service import register_user
from app.config import required
from app.database import SessionLocal, engine
from app.models import User
from app.schemas import UserRegister


def main():
    data = UserRegister(email=required('ADMIN_EMAIL'), password=required('ADMIN_PASSWORD'))
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == str(data.email))):
            raise RuntimeError('Account already exists; no changes made')
        register_user(db, str(data.email), data.password, 'ADMIN')
    print('Administrator created')


if __name__ == '__main__':
    try:
        main()
    finally:
        engine.dispose()
