from app.db.database import db
from datetime import datetime, timezone


class BaseRequest(db.Model):
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(20), nullable=False)  # "mail" o "foto"
    status = db.Column(db.String(20), default="pending")  # pending, processed, error
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __mapper_args__ = {
        "polymorphic_on": request_type,
        "polymorphic_identity": "base"
    }

    def to_dict(self):
        return {
            "id": self.id,
            "request_type": self.request_type,
            "status": self.status,
            "created_at": self.created_at if self.created_at else None
        }


class MailRequest(BaseRequest):
    __tablename__ = "mail_requests"

    id = db.Column(db.Integer, db.ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True)
    mail_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    suggested_reply = db.Column(db.Text, nullable=True)
    extracted_data = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    __mapper_args__ = {"polymorphic_identity": "mail"}

    def to_dict(self):
        base = super().to_dict()
        base.update({
            "mail_text": self.mail_text,
            "category": self.category,
            "priority": self.priority,
            "suggested_reply": self.suggested_reply,
            "extracted_data": self.extracted_data,
            "feedback": self.feedback,
        })
        return base


class FotoRequest(BaseRequest):
    __tablename__ = "foto_requests"

    id = db.Column(db.Integer, db.ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True)
    foto_path = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), nullable=True)
    classe = db.Column(db.String(50), nullable=True)
    ordine = db.Column(db.String(50), nullable=True)
    famiglia = db.Column(db.String(50), nullable=True)
    genere = db.Column(db.String(50), nullable=True)
    specie = db.Column(db.String(50), nullable=True)
    pericolosita = db.Column(db.Text, nullable=True)
    habitat = db.Column(db.Text, nullable=True)
    in_pericolo = db.Column(db.Text, nullable=True)

    __mapper_args__ = {"polymorphic_identity": "foto"}

    def to_dict(self):
        base = super().to_dict()
        base.update({
            "foto_path": self.foto_path,
            "tipo": self.tipo,
            "classe": self.classe,
            "ordine": self.ordine,
            "famiglia": self.famiglia,
            "genere": self.genere,
            "specie": self.specie,
            "pericolosita": self.pericolosita,
            "habitat": self.habitat,
            "in_pericolo": self.in_pericolo
        })
        return base