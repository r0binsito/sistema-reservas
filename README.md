# Reserfy — Sistema de Reservas SaaS Multitenant

## Requisitos
- Python 3.11.9
- pip

## Instalación
```bash
pip install -r requirements.txt
```

## Variables de entorno
Crea un archivo `.env` con estas variables:
```
SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///reservas.db
SENDGRID_API_KEY=SG.xxxxx
MAIL_DEFAULT_SENDER=tu@email.com
CLOUDINARY_CLOUD_NAME=xxxxx
CLOUDINARY_API_KEY=xxxxx
CLOUDINARY_API_SECRET=xxxxx
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
BASE_URL=http://localhost:5000
FLASK_ENV=development
```

## Correr en local
```bash
python app.py
```

## Stack
- Flask + SQLAlchemy + Flask-Login
- SendGrid (emails)
- Cloudinary (imágenes)
- Google OAuth (flask-dance)
- PostgreSQL (producción) / SQLite (local)
- Railway (deploy)