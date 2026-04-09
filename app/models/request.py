from app.db.database import db
from datetime import datetime, timezone



class CustomerRequest(db.Model):
    __tablename__= "customer_requests"

    id = db.Column(db.Integer, primary_key=True)
    
    # Testo della richiesta (obbligatorio)
    text = db.Column(db.Text, nullable=False)

    # Campi popolati dall'AI
    category = db.Column(db.String(50), nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    suggested_reply = db.Column(db.Text, nullable=True)

    extracted_data = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.Text, nullable= True)

    # Metadati
    status = db.Column(db.String(20), default="pending") #pending processed, error
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


    def to_dict(self):
        """ 
        Utility per convertire l'oggetto SQLAlchemy  in un dizionario Python.
        Fondamentale per restiruire JSON puliti tramite API.
        """
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "priority": self.priority,
            "suggested_reply": self.suggested_reply,
            "status": self.status,
            "create_at": self.created_at.isoformat() if self.created_at else None
        }
    
class CustomerRequestFoto(db.Model):
    __tablename__= "customer_requests_foto"

    id = db.Column(db.Integer, primary_key=True)

    # percorso della foto
    foto_path = db.Column(db.Text, nullable=False)

    razza = db.Column(db.String(50), nullable=True)
    famiglia = db.Column(db.String(50), nullable=True)
    descrizione = db.Column(db.String(50), nullable=True)
    pericolosità = db.Column(db.String(50), nullable=True)
    classificazione = db.Column(db.String(50), nullable=True)

    status = db.Column(db.String(20), default="pending") #pending processed, error
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        """ 
        Utility per convertire l'oggetto SQLAlchemy  in un dizionario Python.
        Fondamentale per restiruire JSON puliti tramite API.
        """
        return {
            "id": self.id,
            "foto_path": self.foto_path,
            "razza": self.razza,
            "famiglia": self.famiglia,
            "descrizione": self.descrizione,
            "pericolosità": self.pericolosità,
            "classificazione": self.classificazione,
            "status": self.status,
            "create_at": self.created_at.isoformat() if self.created_at else None
        }