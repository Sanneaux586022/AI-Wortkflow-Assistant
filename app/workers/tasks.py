import requests
import jinja2
from app.core.config import Config
from app.db.database import db
from app.services.processing_service import ProcessingService
from app.services.ai_service import AIService
from app.core.logger import get_logger

template_loader = jinja2.FileSystemLoader("app/templates")
template_env = jinja2.Environment(loader=template_loader)

def render_template(template_filename, **context):
    return template_env.get_template(template_filename).render(**context)

def process_mail_task(request_id):
    from main import app
    with app.app_context():
        logger = get_logger("worker_mail")
        ai_engine = AIService(logger=logger)
        processing_service = ProcessingService(
            db_session=db,
            ai_service=ai_engine,
            logger=logger
        )
        processing_service.process(request_id)


def process_foto_task(request_id):
    from main import app
    with app.app_context():
        logger = get_logger("worker_foto")
        ai_engine = AIService(logger=logger)
        processing_service = ProcessingService(
            db_session=db,
            ai_service=ai_engine,
            logger=logger
        )
        processing_service.predict(request_id)

def send_simple_message(to, subject, body, html):
    return requests.post(
  		f"https://api.mailgun.net/v3/{Config.MAILGUN_DOMAIN_NAME}/messages",
  		auth=("api", Config.MAILGUN_API_KEY),
  		data={"from": f"Sanneaux <postmaster@{Config.MAILGUN_DOMAIN_NAME}>",
			"to": [to],
  			"subject": [subject],
  			"text": body,
            "html": html
        }
    )


def send_user_registration_email(email, username):
    return send_simple_message(
        email,
        "Successfuly signed up.",
        f"Hi {username}! You have successfully signed up to the Stores Rest Api.",
        render_template("email/action.html", username=username)
    )