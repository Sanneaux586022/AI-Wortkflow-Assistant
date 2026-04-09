from flask.views import MethodView
from flask_smorest import Blueprint, abort
from app.api.schemas import UserLoginSchema, UserRegisterSchema
from app.services.user_service import UserService
from app.db.database import db
from app.core.logger import get_logger
from flask_jwt_extended import jwt_required


blp = Blueprint("Users", "users", url_prefix="/users", description="Operazioni sugli utenti.")
logger = get_logger("user_route_logger")
user_service = UserService(db_session=db,logger=logger)

@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(UserRegisterSchema)
    def post(self, user_data):
        """
        Registra un nuovo utente.
        """

        try:
            user = user_service.user_create(user_data)

            return {"message": "Utente creato corretamente.", "id": user.id}, 201
        except ValueError as e:
            abort(409, message=f"{str(e)}")
        

@blp.route("/login")
class UserLogin(MethodView):

    @blp.arguments(UserLoginSchema)
    def post(self, userdata):
        """
        Funzione per il login
        """
        token_data = user_service.user_login(userdata)
        if not token_data:
            abort(401, message="credenziali non valide.") 
        
        return token_data, 200
    
@blp.route("/refresh")
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        new_token = user_service.refresh_token()
        return new_token, 200
    
@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required(fresh=True)
    def post(self):
        try:
            message = user_service.logout()
            return {"message":message}
        except Exception as e:
            abort(500, message=f"{str(e)}")