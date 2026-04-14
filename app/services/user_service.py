from datetime import timezone, datetime
from app.models.user import User
from passlib.hash import pbkdf2_sha256
from sqlalchemy.exc import IntegrityError
from app.core.redis_client import get_redis
from flask_jwt_extended import create_access_token, get_jwt, create_refresh_token, get_jwt_identity


class UserService:
    """
    Servizio responsabile della registrazione.
    """
    def __init__(self, db_session, logger):
        self.db = db_session
        self.logger = logger

    def user_create(self, user_data):
        new_user = User(
            username = user_data['username'],
            email = user_data['email'],
            hash_password = pbkdf2_sha256.hash(user_data['password']),
        )
        if 'is_admin' in user_data:
            new_user.is_admin = user_data['is_admin']
        else:
            new_user.is_admin = False
        try:
            self.db.session.add(new_user)
            self.db.session.commit()
            self.logger.info(f"🧔 Nuovo utente registrato: {new_user.username}")
            return new_user
        except IntegrityError:
            self.db.session.rollback()
            raise
    
    def user_login(self, user_data):
        
        user = self.db.session.query(User).filter(User.username == user_data["username"]).first()

        if user and pbkdf2_sha256.verify(user_data["password"], user.hash_password):
            self.logger.info(f"🔑 Login effetuato per : {user_data['username']}")
            return {"access_token": create_access_token(identity=(str(user.id)), fresh=True),
                    "refresh_token": create_refresh_token(identity=str(user.id))}
        return None
    
    def refresh_token(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        jti = get_jwt()["jti"]
        get_redis.set(jti, "revoked", ex=9000)

        return {"access_token": new_token}
    
    def logout(self):
        try:
            jwt_data = get_jwt()
            jti = jwt_data['jti']
            exp = jwt_data['exp']
            now = datetime.now(timezone.utc).timestamp()

            remaining = int(exp - now)
            get_redis().set(jti, "revoked", ex=remaining)
            return "utente correttamente scollegato!"
        except Exception as e:
            raise ValueError(f"Errore durante il logout: {str(e)}")

